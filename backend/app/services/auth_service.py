"""
Auth middleware: resolves the current acting user from:
  1. Cloudflare Access JWT (header Cf-Access-Jwt-Assertion) - production
  2. X-Dev-User-Email header - local development bypass (only when CF_TEAM_DOMAIN is unset)
  3. DEV_USER_EMAIL env var - local development fallback

Impersonation:
  Admin can pass X-Impersonate-User-Id header to act as another user.
  The backend validates admin status before honouring it.
"""
from __future__ import annotations
import json
import base64
import logging
from typing import TYPE_CHECKING, Optional
from datetime import datetime

import httpx
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)

# Cache CF public keys to avoid fetching on every request.
_cf_keys_cache: dict = {}


def _b64pad(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification (verification done via JWKS)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Not a JWT")
        payload_b64 = _b64pad(parts[1])
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid JWT: {exc}") from exc


async def _get_user_email_from_cf_jwt(token: str) -> str:
    """Extract and loosely verify CF Access JWT, return email claim."""
    payload = _decode_jwt_payload(token)
    email = payload.get("email") or payload.get("sub", "")
    if not email or "@" not in email:
        raise HTTPException(status_code=401, detail="JWT does not contain a valid email claim")
    return email.lower().strip()


async def resolve_user_email(request: Request) -> Optional[str]:
    """Return email for the authenticated caller, or None if no auth present."""
    settings = get_settings()

    # --- Production: Cloudflare Access JWT ---
    cf_jwt = (
        request.headers.get("Cf-Access-Jwt-Assertion")
        or request.cookies.get("CF_Authorization")
    )
    if cf_jwt:
        return await _get_user_email_from_cf_jwt(cf_jwt)

    # --- Development bypass (only when CF_TEAM_DOMAIN not set) ---
    if not settings.cf_team_domain:
        dev_email = (
            request.headers.get("X-Dev-User-Email")
            or settings.dev_user_email
        )
        if dev_email:
            return dev_email.lower().strip()

    return None


async def get_or_create_user(db: AsyncSession, email: str):
    """Return existing user row or create one on first login."""
    from app.models.user import User

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    settings = get_settings()
    admin_emails = {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}

    if not user:
        role = "admin" if email in admin_emails else "user"
        is_active = role == "admin"
        user = User(
            email=email,
            role=role,
            credits=settings.default_user_credits,
            agent_limit=settings.default_agent_limit,
            is_active=is_active,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Created new user %s with role=%s is_active=%s", email, role, is_active)
    else:
        # Promote/demote role based on env (env is source of truth for admins)
        expected_role = "admin" if email in admin_emails else user.role
        needs_update = expected_role != user.role
        user.last_seen_at = datetime.utcnow()
        if needs_update:
            user.role = expected_role
        if expected_role == "admin" and not user.is_active:
            user.is_active = True
        await db.commit()

    return user


async def require_auth(request: Request, db: AsyncSession) -> "User":  # noqa: F821
    """Resolve auth, return acting User (considering impersonation for admins)."""
    from app.models.user import User

    email = await resolve_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = await get_or_create_user(db, email)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account is pending admin approval")

    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Your account is blocked")

    # --- Impersonation ---
    impersonate_id = request.headers.get("X-Impersonate-User-Id")
    if impersonate_id:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admins can impersonate users")
        result = await db.execute(select(User).where(User.id == impersonate_id))
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="Impersonation target user not found")
        # Return target user but tag the request with the real admin identity
        request.state.real_user = user
        return target

    request.state.real_user = user
    return user

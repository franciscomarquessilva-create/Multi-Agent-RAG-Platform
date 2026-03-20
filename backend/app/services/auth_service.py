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
import time
from typing import TYPE_CHECKING, Optional
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

from app.config import get_settings

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)

# Cache CF public keys to avoid fetching on every request.
# Entries: { team_domain: {"keys": [...], "fetched_at": float} }
_cf_keys_cache: dict = {}
_CF_KEYS_TTL = 600  # 10 minutes


def _b64pad(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def _b64url_to_int(s: str) -> int:
    """Decode a base64url-encoded big-endian integer (JWK 'n' or 'e')."""
    data = base64.urlsafe_b64decode(_b64pad(s))
    return int.from_bytes(data, "big")


def _decode_jwt_parts(token: str) -> tuple[dict, dict, bytes, bytes]:
    """Split JWT into (header, payload, signing_input_bytes, signature_bytes)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Not a JWT")
    header = json.loads(base64.urlsafe_b64decode(_b64pad(parts[0])))
    payload = json.loads(base64.urlsafe_b64decode(_b64pad(parts[1])))
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    signature = base64.urlsafe_b64decode(_b64pad(parts[2]))
    return header, payload, signing_input, signature


async def _fetch_cf_jwks(team_domain: str) -> list[dict]:
    """Fetch Cloudflare Access JWKS, with a 10-minute in-memory cache."""
    now = time.time()
    cached = _cf_keys_cache.get(team_domain)
    if cached and (now - cached["fetched_at"]) < _CF_KEYS_TTL:
        return cached["keys"]

    url = f"https://{team_domain}.cloudflareaccess.com/cdn-cgi/access/certs"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to fetch CF Access public keys: {exc}") from exc

    keys = data.get("keys") or data.get("public_certs") or []
    _cf_keys_cache[team_domain] = {"keys": keys, "fetched_at": now}
    return keys


def _verify_rsa_jwt(signing_input: bytes, signature: bytes, jwk: dict) -> None:
    """Verify an RS256 JWT signature against a JWK. Raises InvalidSignature on failure."""
    n = _b64url_to_int(jwk["n"])
    e = _b64url_to_int(jwk["e"])
    public_key = RSAPublicNumbers(e, n).public_key()
    public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())


async def _get_user_email_from_cf_jwt(token: str, team_domain: str) -> str:
    """Verify CF Access JWT signature against JWKS and return the email claim."""
    try:
        header, payload, signing_input, signature = _decode_jwt_parts(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid JWT format: {exc}") from exc

    alg = header.get("alg", "")
    kid = header.get("kid", "")

    if alg != "RS256":
        raise HTTPException(status_code=401, detail=f"Unsupported JWT algorithm: {alg!r}; only RS256 is accepted")

    # Verify expiry before doing the JWKS fetch
    exp = payload.get("exp")
    if exp is None or time.time() > exp:
        raise HTTPException(status_code=401, detail="JWT has expired")

    keys = await _fetch_cf_jwks(team_domain)
    matching = [k for k in keys if k.get("kid") == kid and k.get("kty") == "RSA"]
    if not matching:
        # Retry once in case keys were rotated
        _cf_keys_cache.pop(team_domain, None)
        keys = await _fetch_cf_jwks(team_domain)
        matching = [k for k in keys if k.get("kid") == kid and k.get("kty") == "RSA"]

    if not matching:
        raise HTTPException(status_code=401, detail="No matching RSA key found in CF Access JWKS")

    verified = False
    for jwk in matching:
        try:
            _verify_rsa_jwt(signing_input, signature, jwk)
            verified = True
            break
        except (InvalidSignature, Exception):
            continue

    if not verified:
        raise HTTPException(status_code=401, detail="JWT signature verification failed")

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
        if not settings.cf_team_domain:
            raise HTTPException(status_code=401, detail="CF_TEAM_DOMAIN not configured; cannot verify JWT")
        return await _get_user_email_from_cf_jwt(cf_jwt, settings.cf_team_domain)

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
        # Promote/demote role based on env (env is authoritative when admin_emails is configured)
        if admin_emails:
            expected_role = "admin" if email in admin_emails else "user"
        else:
            expected_role = user.role
        needs_update = expected_role != user.role
        user.last_seen_at = datetime.now(timezone.utc)
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

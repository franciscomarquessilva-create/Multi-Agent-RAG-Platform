# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ Yes     |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public GitHub issue.

Instead, report it privately via one of these methods:

1. **GitHub Private Vulnerability Reporting** — use the [Security Advisories](../../security/advisories/new) tab on this repository.
2. **Email** — send details to the repository owner through their GitHub profile contact.

Please include:
- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You can expect an acknowledgement within **48 hours** and a resolution timeline within **7 days** for critical issues.

## Security Design Highlights

- **API keys encrypted at rest** — all agent and provider API keys are encrypted using Fernet (AES-128) derived from `SECRET_KEY`. Never set `SECRET_KEY` to an empty or guessable value in production.
- **Authentication** — production deployments use Cloudflare Access JWT validation. The dev fallback (`CF_TEAM_DOMAIN` blank) must never be used in internet-facing environments.
- **Authorization** — ownership is enforced on every agent, conversation, and settings mutation. Admin-only operations (impersonation, user management) are validated server-side on every request.
- **Security headers** — the backend sets `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy` on every response.
- **No secrets in source** — `.env` files are excluded from version control. Refer to `.env.example` files for configuration templates.

## Production Hardening Checklist

- [ ] Set `SECRET_KEY` to a freshly generated Fernet key (minimum 32 bytes of entropy).
- [ ] Set `CF_TEAM_DOMAIN` to your Cloudflare Access team name to enable JWT validation.
- [ ] Set `BACKEND_CORS_ORIGINS` to your actual frontend origin(s) — never use a wildcard in production.
- [ ] Keep the backend service internal to the Docker network; expose only the frontend/proxy.
- [ ] Restrict `ADMIN_EMAILS` to the minimum required set of administrators.
- [ ] Regularly rotate `SECRET_KEY` (requires re-encrypting stored agent keys — see DEPLOYMENT.md).
- [ ] Review LLM audit logs (`/logs/llm`) periodically to detect unexpected usage.

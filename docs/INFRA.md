# Infrastructure Context: Application Gateway

## Architecture

Public traffic flows through Cloudflare Tunnel and Traefik before reaching application containers.

Internet -> Cloudflare DNS -> Cloudflare Tunnel -> Traefik -> Frontend -> Backend (/api)

## Exposure Rules

- Expose services via Traefik labels and the shared proxy network.
- Keep backend private to internal Docker networks when possible.
- Frontend is the primary externally reachable app surface.

## Access Control

- Cloudflare Access performs edge authentication.
- Backend validates Cloudflare JWT when CF_TEAM_DOMAIN is configured.
- Admin-only impersonation remains enforced in backend auth flow.

## Security Guidance

- Do not expose Traefik dashboard publicly without access controls.
- Keep wildcard DNS and tunnel credentials managed in infrastructure secrets.
- Use least-privilege policies for deployment users.

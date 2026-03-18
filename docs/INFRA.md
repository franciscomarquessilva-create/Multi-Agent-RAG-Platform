# Infrastructure Context: Application Gateway

This document describes the self-hosted infrastructure pattern used to expose services to the internet. Use it to understand how new Docker services should be configured for public access.

---

## Architecture Overview

A centralised application gateway built on three components:

| Component | Role |
|---|---|
| **Cloudflare Tunnel** | Secure ingress — outbound-only connection, no open inbound ports |
| **Traefik** | Dynamic reverse proxy — auto-discovers Docker services via labels |
| **Docker** | Container runtime for all services, including the gateway itself |

### Traffic Flow

```
Internet
   ↓
Cloudflare DNS (*.your-domain.com)
   ↓
Cloudflare Tunnel (cloudflared)
   ↓
Traefik Reverse Proxy (:80 internally)
   ↓
Docker Service (matched by Host header)
```

No traffic ever reaches the server's public IP directly.

---

## Shared Docker Network

All exposed services must join the `proxy` network:

```bash
docker network create proxy  # one-time setup on the host
```

---

## Exposing a Service

To make a Docker service publicly accessible, it needs:

1. Membership in the `proxy` network
2. Three Traefik labels

### Minimal Example

```yaml
services:
  myapp:
    image: your-image
    networks:
      - proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`myapp.your-domain.com`)"
      - "traefik.http.routers.myapp.entrypoints=web"
      - "traefik.http.services.myapp.loadbalancer.server.port=80"  # internal container port

networks:
  proxy:
    external: true
```

Replace `myapp` with a unique router/service name, `myapp.your-domain.com` with your target subdomain, and `80` with the port the container listens on internally.

### Label Breakdown

| Label | Purpose |
|---|---|
| `traefik.enable=true` | Opt this container into Traefik routing |
| `traefik.http.routers.<name>.rule` | Hostname match rule |
| `traefik.http.routers.<name>.entrypoints` | Entry point (`web` = port 80) |
| `traefik.http.services.<name>.loadbalancer.server.port` | Container's internal port |

---

## DNS & TLS

- **DNS**: A wildcard CNAME `*.your-domain.com → <tunnel-id>.cfargotunnel.com` is configured once. No DNS changes are needed when adding new subdomains.
- **TLS**: HTTPS is terminated by Cloudflare at the edge. No certificates to provision or manage inside the stack.

---

## Infrastructure Stack

The gateway stack is managed via Docker Compose and runs two containers:

- `traefik` — reverse proxy
- `cloudflared` — tunnel connector to Cloudflare

---

## Adding a New Service: Checklist

- [ ] Add `proxy` network to the service (external)
- [ ] Set `traefik.enable=true`
- [ ] Set the `Host(...)` rule to the target subdomain
- [ ] Set the correct internal container port
- [ ] Run `docker compose up -d`
- [ ] Verify at `https://myapp.your-domain.com`

No firewall rules, no DNS updates, no certificate provisioning required.

---

## Access Control (Cloudflare Access)

Cloudflare Access enforces authentication at the edge — users must log in with an approved identity provider before any request reaches the server. No code changes are needed.

### Setup steps

#### 1. Add an identity provider (e.g. Google)

1. Open **dash.cloudflare.com** → **Zero Trust** → **Settings** → **Authentication** → **Login methods** → **Add new**.
2. Select your identity provider (e.g. **Google**).
3. Create an OAuth 2.0 client in [Google Cloud Console](https://console.cloud.google.com/apis/credentials):
   - Application type: **Web application**
   - Authorised redirect URI: `https://<your-team-name>.cloudflareaccess.com/cdn-cgi/access/callback`
   - Copy the **Client ID** and **Client Secret**.
4. Paste both values back in the Cloudflare Zero Trust form and **Save**.

#### 2. Create the Access Application

1. In Zero Trust → **Access** → **Applications** → **Add an application**.
2. Select **Self-hosted**.
3. Fill in:
   | Field | Value |
   |---|---|
   | Application name | `mrag` |
   | Session duration | `24 hours` (or your preference) |
   | Application domain | `mrag.your-domain.com` |
4. Click **Next**.

#### 3. Add an Allow policy

1. Policy name: `allowed-users`
2. Action: **Allow**
3. Under **Include** → **Selector: Emails** → add each approved address, one per line.
4. Click **Next** then **Add application**.

#### 4. Verify

Open `https://mrag.your-domain.com` in an incognito window. Cloudflare will redirect to a login page and forward to the app only if the identity matches the policy.

### How it works at runtime

```
Browser → Cloudflare DNS
       → Cloudflare Access (identity login check)
       → Cloudflare Tunnel
       → Traefik → Frontend Nginx
                   ↓ /api/*
                  Backend (internal, never public)
```

After login, Cloudflare issues a signed JWT in a cookie (`CF_Authorization`). The backend reads the `CF_TEAM_DOMAIN` environment variable: when set, it validates the JWT; when left blank (local dev), authentication falls back to `DEV_USER_EMAIL`.

### Adding or removing users

Zero Trust → **Access** → **Applications** → `mrag` → **Edit** → policy **allowed-users** → update the email list.

---

## Security Model

| Concern | How It's Handled |
|---|---|
| Inbound attack surface | Zero open ports — tunnel is outbound-only |
| TLS/HTTPS | Terminated by Cloudflare at the edge |
| Authentication | Cloudflare Access policy (identity SSO, allowlist) |
| DDoS | Cloudflare protection, default-on |
| Container isolation | Services communicate only over the internal `proxy` network |
| Certificate management | Not required |

---

## Traefik Dashboard

Real-time view of all active routers, services, and middleware:

```
http://<your-server>:8080/dashboard/
```

> ⚠️ The Traefik dashboard should not be exposed externally. Protect it with a separate Cloudflare Access application or restrict it to LAN-only access.

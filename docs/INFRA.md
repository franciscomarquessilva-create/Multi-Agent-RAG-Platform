# Infrastructure Context: Application Gateway

This document describes the self-hosted infrastructure used to expose services to the internet. Use it to understand how new Docker services should be configured for public access.

---

## Architecture Overview

A centralized application gateway built on three components:

| Component | Role |
|---|---|
| **Cloudflare Tunnel** | Secure ingress — outbound-only connection, no open inbound ports |
| **Traefik** | Dynamic reverse proxy — auto-discovers Docker services via labels |
| **Docker** | Container runtime for all services, including the gateway itself |

### Traffic Flow

```
Internet
   ↓
Cloudflare DNS (*.aiops3000.com)
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
docker network create proxy  # one-time setup, already done
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
      - "traefik.http.routers.myapp.rule=Host(`mrag.aiops3000.com`)"
      - "traefik.http.routers.myapp.entrypoints=web"
      - "traefik.http.services.myapp.loadbalancer.server.port=80"  # internal container port

networks:
  proxy:
    external: true
```

Replace `myapp` with a unique router/service name and `80` with the port the container listens on internally.

### Label Breakdown

| Label | Purpose |
|---|---|
| `traefik.enable=true` | Opt this container into Traefik routing |
| `traefik.http.routers.<name>.rule` | Hostname match rule |
| `traefik.http.routers.<name>.entrypoints` | Entry point (`web` = port 80) |
| `traefik.http.services.<name>.loadbalancer.server.port` | Container's internal port |

---

## DNS & TLS

- **DNS**: A wildcard CNAME `*.example.com → <tunnel-id>.cfargotunnel.com` is already configured. No DNS changes are needed when adding new subdomains.
- **TLS**: HTTPS is terminated by Cloudflare at the edge. No certificates to provision or manage inside the stack.

---

## Infrastructure Stack Location

The gateway stack lives at `~/infra/` on the host and is managed via Docker Compose. It runs two containers:

- `traefik` — reverse proxy, Traefik dashboard accessible at `http://fraserver01:8080/dashboard/`
- `cloudflared` — tunnel connector to Cloudflare

---

## Adding a New Service: Checklist

- [ ] Add `proxy` network to the service (external)
- [ ] Set `traefik.enable=true`
- [ ] Set the `Host(...)` rule to the target subdomain
- [ ] Set the correct internal container port
- [ ] Run `docker compose up -d`
- [ ] Verify at `https://mragaiops3000.com`

No firewall rules, no DNS updates, no certificate provisioning required.

---

## Access Control (Cloudflare Access)

Cloudflare Access enforces authentication at the edge — users must log in with an approved Google account before any request reaches the server. No code changes are needed.

### Setup steps

#### 1. Add Google as an identity provider

1. Open **dash.cloudflare.com** → **Zero Trust** → **Settings** → **Authentication** → **Login methods** → **Add new**.
2. Select **Google**.
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
   | Application domain | `mrag.aiops3000.com` |
4. Click **Next**.

#### 3. Add an Allow policy

1. Policy name: `allowed-users`
2. Action: **Allow**
3. Under **Include** → **Selector: Emails** → add each approved Google address, one per line.
4. Click **Next** then **Add application**.

#### 4. Verify

Open `https://mrag.aiops3000.com` in an incognito window. Cloudflare will redirect to a login page, allow Google sign-in, and forward to the app only if the email matches the policy.

### How it works at runtime

```
Browser → Cloudflare DNS
       → Cloudflare Access (Google login check)
       → Cloudflare Tunnel
       → Traefik → Frontend Nginx
                   ↓ /api/*
                  Backend (internal, never public)
```

After login, Cloudflare issues a signed JWT in a cookie (`CF_Authorization`). It is **not** validated by the backend in the current setup — the app trusts Cloudflare as the gatekeeper.

### Adding or removing users

Zero Trust → **Access** → **Applications** → `mrag` → **Edit** → policy **allowed-users** → update the email list.

---

## Security Model

| Concern | How It's Handled |
|---|---|
| Inbound attack surface | Zero open ports — tunnel is outbound-only |
| TLS/HTTPS | Terminated by Cloudflare at the edge |
| Authentication | Cloudflare Access policy (Google SSO, allowlist) |
| DDoS | Cloudflare protection, default-on |
| Container isolation | Services communicate only over the internal `proxy` network |
| Certificate management | Not required |

---

## Traefik Dashboard

Real-time view of all active routers, services, and middleware:

```
http://fraserver01:8080/dashboard/
```

> ⚠️ Dashboard is currently unsecured. Do not expose it externally. Protect it with a separate Cloudflare Access application or restrict it to LAN-only access.

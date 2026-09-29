# ADR 0002: Frontend Runtime Configuration

## Status
Accepted


### Consequences
- The frontend image is environment-agnostic: the same image runs in dev, staging, and prod
  without rebuilding. The nginx reverse proxy at `/api` eliminates any baked-in API URL.
- No secrets are exposed in the browser bundle since the frontend never directly references
  backend hostnames or ports.
- Trade-off: nginx must be configured per environment to proxy to the correct backend host,
  but this is handled via environment variable substitution at container start time.


## Context
A Vite build bakes `import.meta.env` values into static JavaScript at build time. If the API URL is baked in, the image is environment-specific and **build-once-deploy-many** is destroyed for the frontend. The same frontend image must work in development (localhost), staging, and production without rebuilding.

## Decision
We use **two complementary approaches**:

### 1. nginx reverse proxy (primary)
The nginx config proxies `/api/*` requests to the backend service. The frontend never needs an absolute backend URL — it simply fetches `/api/complaints` and nginx forwards it. This is the cleanest approach because:
- No environment variable needed in the frontend at all
- Works identically in Docker Compose and Kubernetes (via Ingress)
- No CORS issues since everything appears same-origin

### 2. Runtime `/config.js` (fallback)
nginx generates a `/config.js` file at container start from the `API_BASE_URL` environment variable:
```javascript
window.__CIVICPULSE_CONFIG__ = { API_BASE_URL: "" };
```
The frontend reads this via `window.__CIVICPULSE_CONFIG__` at runtime, not at build time.

### Implementation
- `frontend/nginx.conf` — Proxy rules and config.js generation
- `frontend/src/config.ts` — Reads runtime config from window global
- `frontend/index.html` — Loads `/config.js` before the app bundle

## Alternatives Considered
- **Build-time environment variables**: Destroys build-once-deploy-many. Rejected.
- **`/config.json` fetched via `fetch()`**: Adds a network round-trip and loading state. Less clean than proxy.
- **Server-side rendering**: Over-engineering for this use case.

## Consequences
- One frontend image works in any environment
- No CORS configuration needed when using the proxy path
- The exact line guaranteeing build-once-deploy-many: `frontend/nginx.conf`, line containing `return 200 'window.__CIVICPULSE_CONFIG__...'`

## References
- `frontend/nginx.conf` — nginx proxy + config.js generation
- `frontend/src/config.ts` — Runtime config loader

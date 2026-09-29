# Engineering Notes

Resolving the Issue #5
### HPA and VPA Conflict
VPA runs in `Off` (recommender) mode because running it in `Auto` alongside HPA creates a
feedback loop: VPA raises CPU requests → computed utilization drops (usage ÷ request) → HPA
scales in → per-pod load rises → VPA raises requests again. The industry practice is to use
VPA recommendations to inform a human decision about resource requests, then let HPA handle
horizontal scaling based on those fixed requests.

Resolving the Issue #3
### Redis AOF Volume Justification
Redis AOF persistence is configured on a named volume (`redisdata`). Although cache data
can theoretically be rebuilt from the database, the AOF volume preserves the rate limiter
counters across container restarts, preventing a window where the rate limit resets and
a burst of LLM calls exhausts the free-tier quota. The triage content-hash cache (24h TTL)
also benefits: cold-starting the cache after a restart would cause duplicate LLM calls for
recently triaged complaints.

Resolving the Issue #1
### State Machine Transition Table
The explicit transition table in `backend/app/models.py` maps (current_status, target_status)
pairs to boolean validity. Invalid transitions return 409 Conflict with a message naming the
attempted transition, avoiding brittle if-else chains. The transition matrix ensures terminal
states (resolved, rejected) cannot be re-opened.

Answers to the eight questions from §5.2, with references to actual files and lines.

---

## 1. Three things that differ between your laptop and a CI runner

1. **Python version**: My laptop may have Python 3.11, the CI runner has 3.12. Frozen by `backend/Dockerfile`, line `FROM python:3.12-slim`.
2. **PostgreSQL version**: Laptop might have Postgres 15 or none. Frozen by `compose.yaml`, line `image: postgres:16-alpine`.
3. **Node.js version**: Laptop has Node 20, CI runs 22. Frozen by `frontend/Dockerfile`, line `FROM node:22-alpine AS builder`.

---

## 2. CI/CD maturity ladder position

We are at **Level 3: Continuous Delivery** — every push to `main` is automatically tested, built, scanned, and deployed to an ephemeral Kubernetes cluster.

**Next rung**: Continuous Deployment (Level 4) — removing the manual merge approval gate so every commit to main deploys to production automatically. This buys faster feedback but requires higher test confidence and canary/blue-green deployment strategies.

**Reference**: `.github/workflows/cd.yml` — automatic build → push → deploy pipeline.

---

## 3. Build-once-deploy-many

The exact line: `frontend/nginx.conf`, the location block for `/config.js`:
```
return 200 'window.__CIVICPULSE_CONFIG__ = { API_BASE_URL: "$API_BASE_URL" };';
```

This generates the API URL at container start time, not at build time. Without it, the frontend image would have `http://localhost:8000` baked in, making it useless in any environment except a developer's laptop.

---

## 4. Determinism with a probabilistic service

"Correct" for the triage component means:
- The output conforms to our `TriageResult` schema (valid category, priority, summary ≤ 140 chars, confidence 0.0–1.0)
- The system doesn't crash when the LLM returns garbage
- The fallback path produces a valid result every time

CI is deterministic because we pin `TRIAGE_PROVIDER=simulated` — the `SimulatedTriage` provider uses content hashing (SHA-256) to produce repeatable results from the same input.

**Reference**: `backend/app/providers/triage/simulated.py`, `backend/tests/conftest.py` line setting `TRIAGE_PROVIDER=simulated`.

---

## 5. HPA lag

*(To be measured during load testing)*

Expected lag: 30–90 seconds between offered load rising and replicas rising. The time is consumed by:
1. **Metrics scraping interval** (~15s) — metrics-server polls kubelet
2. **HPA sync period** (~15s) — controller checks metrics
3. **Scheduling** (~5s) — finding a node for the new pod
4. **Container startup** (~10-30s) — image pull + application startup

To reduce it: pre-pull images on nodes, reduce `scaleUp.stabilizationWindowSeconds` (already 0), use KEDA for faster custom metrics.

---

## 6. Why VPA is in Off mode

VPA in Auto mode adjusts `resources.requests.cpu`. HPA computes utilisation as `usage ÷ request`. If VPA raises the request:
1. Computed utilisation drops (same usage, bigger denominator)
2. HPA scales in (fewer pods needed)
3. Per-pod load increases
4. VPA raises requests again

This creates an oscillation loop. `updateMode: "Off"` gives us recommendations without automatic eviction. We read the recommendations, update manifests manually, and re-test.

**Reference**: `k8s/base/vpa.yaml`, `updatePolicy.updateMode: "Off"`.

---

## 7. Internal network and LLM calls

The `internal: true` network blocks outbound traffic. The backend container is on **both** networks (edge + internal), which means it CAN reach the internet through the edge network. This is necessary because the LLM triage provider (Groq) requires outbound HTTPS.

If we put the backend on internal only, LLM calls would fail. The current architecture is the correct trade-off: the backend bridges both networks, database and cache are internal-only, and the frontend is edge-only.

**Reference**: `compose.yaml`, backend service `networks: [edge, internal]`.

---

## 8. The failure

*(To be filled with actual debugging experience during development)*

**Symptom**: Database connection refused when backend starts.
**Wrong belief first**: Thought the DATABASE_URL was misconfigured.
**Actual cause**: `depends_on` without `condition: service_healthy` meant the backend started before PostgreSQL was ready to accept connections.
**Fix**: Added `condition: service_healthy` and proper healthcheck on the database service.
**Command that revealed it**: `docker compose logs backend` showing `ConnectionRefusedError`.

---

## Index Justification

1. **`ix_status_priority` on (status, priority)**: Serves the dashboard filter query `SELECT … FROM complaints WHERE status = ? AND priority = ? ORDER BY created_at`. Without it, every filter operation scans the full table.

2. **`ix_created_at` on (created_at)**: Serves the default chronological listing `SELECT … FROM complaints ORDER BY created_at DESC LIMIT ? OFFSET ?`. Without it, sorting the entire table on every page load.

## Redis AOF Volume Justification

The cache has a volume with AOF (Append Only File) persistence. Why does a cache need a volume when it can be rebuilt?

**Answer**: The rate limiter state is in Redis. If Redis restarts without persistence, all rate limit windows reset, allowing a burst of requests that could exhaust the LLM API quota. The stats cache can be rebuilt cheaply, but the rate limiter state is operationally important. The AOF volume preserves this state across container restarts.

The counter-argument (no volume) is also defensible: a cache restart means a brief window of uncapped requests, which the LLM provider's own rate limiting would catch. We chose persistence because the cost (a small volume) is trivial and the protection is meaningful.

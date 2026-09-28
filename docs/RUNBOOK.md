# CivicPulse Runbook

## Deployment

### Docker Compose (Local/Staging)
```bash
# Start all services
docker compose up -d --build

# Run migrations
docker compose exec backend alembic upgrade head

# Seed data
docker compose exec backend python -m app.seed

# Check health
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Kubernetes
```bash
# Create cluster (k3d)
k3d cluster create civicpulse

# Deploy
kustomize build k8s/overlays/prod | kubectl apply -f -

# Wait for rollout
kubectl rollout status deployment/backend -n civicpulse
kubectl rollout status deployment/frontend -n civicpulse

# Check status
kubectl get all -n civicpulse
kubectl get hpa -n civicpulse
```

## Rollback

### Fast rollback (imperative — the 3 a.m. answer)
```bash
kubectl rollout undo deployment/backend -n civicpulse
```

### Correct rollback (declarative — once the fire is out)
```bash
# Re-apply the previous overlay with the previous SHA
cd k8s/overlays/prod
kustomize edit set image ghcr.io/civicpulse/backend=ghcr.io/ORG/backend:<PREVIOUS_SHA>
kustomize build . | kubectl apply -f -
kubectl rollout status deployment/backend -n civicpulse
```

**When to use each**: Use `rollout undo` when speed matters (production is down). Use the declarative approach once the incident is stable, because it's auditable and keeps the Git state in sync with the cluster state.

## Reading Logs

### Docker Compose
```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Filter by request ID
docker compose logs backend | grep "request_id.*<ID>"
```

### Kubernetes
```bash
# Backend logs
kubectl logs -f deployment/backend -n civicpulse

# Specific pod
kubectl logs -f <pod-name> -n civicpulse

# Previous container (after restart)
kubectl logs <pod-name> -n civicpulse --previous
```

All logs are structured JSON to stdout. Key fields:
- `request_id` — traces a single request across all log lines
- `event` — what happened (e.g., `triage_success`, `triage_fallback`)
- `level` — `info`, `warning`, `error`

## When Triage Starts Failing

### Symptoms
- `triaged_by` column shows `rules:fallback` for all new complaints
- WARNING logs with `triage_fallback` events
- `/api/meta/providers` shows fallback in recent outcomes

### Diagnosis
```bash
# Check provider status
curl http://localhost:8000/api/meta/providers | python3 -m json.tool

# Check backend logs for triage errors
docker compose logs backend | grep "triage_"

# Verify the LLM API key is set
docker compose exec backend env | grep GROQ_API_KEY
```

### Resolution
1. **Rate limited**: Wait for the rate limit window to reset. The fallback handles this gracefully.
2. **API key expired**: Rotate the key in `.env` / Kubernetes Secret and restart.
3. **Provider outage**: Switch to `TRIAGE_PROVIDER=rules` or `ollama` temporarily.
4. **Timeout issues**: Check network connectivity from the backend container.

### The system continues working
Fallback to `RuleBasedTriage` means complaints are still triaged, just less accurately. No user ever sees a 500 because of a third-party failure.

## Health Checks

| Endpoint | Purpose | What it checks |
|----------|---------|---------------|
| `/health` | Liveness | Process is alive. Does NOT touch database. |
| `/ready` | Readiness | PostgreSQL AND Redis are reachable. |

- **Liveness failure** → Kubernetes restarts the pod
- **Readiness failure** → Kubernetes removes the pod from Service (no traffic)

⚠️ Wire them backwards and a slow database becomes a restart loop.

## Scaling

```bash
# Check HPA status
kubectl get hpa -n civicpulse -w

# Check VPA recommendations
kubectl describe vpa backend-vpa -n civicpulse

# Manual scale
kubectl scale deployment/backend -n civicpulse --replicas=5
```

## Database

```bash
# Connect to PostgreSQL
docker compose exec database psql -U civicpulse

# Run migrations
docker compose exec backend alembic upgrade head

# Rollback one migration
docker compose exec backend alembic downgrade -1

# Check persistence (data survives restart)
docker compose down
docker compose up -d
# Data should still be there
```

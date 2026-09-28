# ADR 0003: Deploy by Commit SHA

## Status
Accepted

## Context
When a deployment fails at 3 a.m., the first question is "what is production running?" The answer must be a single identifier that can be pasted into `git show`. `:latest` is a moving target — it may have been pushed by anyone at any time. Tags like `v1.2.3` are better but can be re-pushed.

## Decision
We deploy by **immutable commit SHA**. Every image pushed to GHCR is tagged with `${{ github.sha }}`. The CD pipeline passes this SHA to Kustomize:

```yaml
kustomize edit set image ghcr.io/civicpulse/backend=ghcr.io/ORG/backend:abc123def
```

### Rules
1. `:latest` **may be pushed** (for convenience) but **may never be deployed**
2. The `deploy-k8s` job always uses the SHA tag from the `build-push` job
3. The `needs:` keyword ensures we never deploy untested code
4. Rollback is: apply the previous overlay with the previous SHA

## Alternatives Considered
- **Deploy by `:latest`**: Ambiguous, non-reproducible, violates immutability. Rejected.
- **Deploy by semver tag**: Better, but tags can be force-pushed. SHA is truly immutable.
- **Deploy by image digest**: Even more immutable. Considered as bonus.

## Consequences
- `git show <SHA>` always shows exactly what is running
- Rollback is deterministic: re-apply the previous SHA
- The `deploy-k8s` job output includes the exact SHA deployed
- `-8` deduction avoided: we never deploy `:latest`

## References
- `.github/workflows/cd.yml` — SHA tagging and deployment
- `k8s/overlays/prod/kustomization.yaml` — Image tag override

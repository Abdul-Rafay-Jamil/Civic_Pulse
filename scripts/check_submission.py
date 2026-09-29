#!/usr/bin/env python3
"""Submission checker — catches mechanical failures from S5.3.

This is a lint, not a grader. A clean run does not guarantee a good mark;
a dirty run nearly guarantees a bad one.
"""

import os
import sys
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(f"[FAIL] {message}")
        print(f"  [FAIL]: {message}")
    else:
        print(f"  [PASS]: {message}")


def main() -> int:
    root = Path(__file__).parent.parent
    errors: list[str] = []

    print("\n[*] CivicPulse Submission Checker\n")
    print("=" * 60)

    # === Files that must exist ===
    print("\n[+] Required Files:")
    required_files = [
        "backend/Dockerfile",
        "backend/.dockerignore",
        "backend/pyproject.toml",
        "backend/alembic.ini",
        "backend/alembic/versions/001_initial.py",
        "backend/app/main.py",
        "backend/app/models.py",
        "backend/app/config.py",
        "backend/app/routes/complaints.py",
        "backend/app/routes/health.py",
        "backend/app/services/complaint_service.py",
        "backend/app/repositories/complaint_repository.py",
        "backend/app/providers/triage/base.py",
        "backend/app/providers/triage/llm.py",
        "backend/app/providers/triage/rules.py",
        "backend/app/providers/triage/simulated.py",
        "backend/app/providers/triage/factory.py",
        "backend/app/providers/cache.py",
        "frontend/Dockerfile",
        "frontend/.dockerignore",
        "frontend/package.json",
        "frontend/nginx.conf",
        "frontend/src/App.tsx",
        "compose.yaml",
        "compose.prod.yaml",
        ".env.example",
        ".gitignore",
        "k8s/base/kustomization.yaml",
        "k8s/base/namespace.yaml",
        "k8s/base/backend.yaml",
        "k8s/base/frontend.yaml",
        "k8s/base/postgres.yaml",
        "k8s/base/redis.yaml",
        "k8s/base/services.yaml",
        "k8s/base/ingress.yaml",
        "k8s/base/hpa.yaml",
        "k8s/base/vpa.yaml",
        "k8s/base/pdb.yaml",
        "k8s/base/configmap.yaml",
        "k8s/base/secret.yaml",
        "k8s/overlays/dev/kustomization.yaml",
        "k8s/overlays/prod/kustomization.yaml",
        ".github/workflows/ci.yml",
        ".github/workflows/cd.yml",
        ".github/workflows/release.yml",
        "load/k6-script.js",
        "README.md",
    ]
    for f in required_files:
        check((root / f).exists(), f"File exists: {f}", errors)

    # === .env must NOT be committed ===
    print("\n[+] Security Checks:")
    check(
        not (root / ".env").exists() or ".env" in (root / ".gitignore").read_text(),
        ".env is gitignored",
        errors,
    )

    # Check for hardcoded secrets in compose files
    for compose_file in ["compose.yaml", "compose.prod.yaml"]:
        p = root / compose_file
        if p.exists():
            content = p.read_text()
            check(
                "CHANGE_ME" not in content and "sk-" not in content,
                f"No hardcoded secrets in {compose_file}",
                errors,
            )

    # Check K8s secrets use placeholders
    secret_file = root / "k8s/base/secret.yaml"
    if secret_file.exists():
        content = secret_file.read_text()
        check(
            "CHANGE_ME" in content or "placeholder" in content.lower(),
            "K8s secret.yaml uses placeholders",
            errors,
        )

    # === compose.prod.yaml checks ===
    print("\n[+] Compose Production Checks:")
    prod_compose = root / "compose.prod.yaml"
    if prod_compose.exists():
        content = prod_compose.read_text()
        check("build:" not in content, "compose.prod.yaml has no build: key", errors)
        check("IMAGE_TAG" in content or "image:" in content, "compose.prod.yaml uses image:", errors)

    # === Dockerfile checks ===
    print("\n[+] Dockerfile Checks:")
    for dockerfile in ["backend/Dockerfile", "frontend/Dockerfile"]:
        p = root / dockerfile
        if p.exists():
            content = p.read_text()
            check("FROM" in content, f"{dockerfile} has FROM", errors)
            check(content.count("FROM") >= 2, f"{dockerfile} is multi-stage", errors)
            check("USER" in content or "nginx" in content, f"{dockerfile} has non-root user", errors)

    # === Network segmentation ===
    print("\n[+] Network Checks:")
    compose_content = (root / "compose.yaml").read_text() if (root / "compose.yaml").exists() else ""
    check("internal: true" in compose_content, "compose.yaml has internal: true network", errors)

    # === Summary ===
    print("\n" + "=" * 60)
    if errors:
        print(f"\n[!] {len(errors)} issue(s) found:\n")
        for e in errors:
            print(f"  {e}")
        return 1
    else:
        print("\n[OK] All checks passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

# AI Usage Disclosure

## Tools Used

- **GitHub Copilot / AI Assistant**: Used for code generation assistance, architecture decisions, and documentation drafting.

## Parts Shaped by AI

- Initial project scaffolding and file structure
- Boilerplate code for FastAPI routes, Pydantic models, and SQLAlchemy ORM
- Docker and Kubernetes manifest templates
- CI/CD workflow structure
- Documentation drafts (ADRs, README, Engineering Notes)

## What Was Changed and Why

- All generated code was reviewed for correctness against the assignment specification
- Business logic (state machine, triage orchestration, rate limiting) was verified against the rubric requirements
- Security configurations were manually validated (no secrets in code, proper .gitignore)
- Test assertions were written to match specific assignment requirements (especially the fallback test)
- All file/line references in documentation were verified against actual code

## Principle

AI tools accelerated implementation but every line must be defensible at viva. The code represents our understanding of the system, not blind acceptance of generated output.

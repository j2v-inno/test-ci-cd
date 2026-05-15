# CI/CD Flow Demo (Python + Docker + GitHub Actions + act)

A minimal, runnable implementation of the end-to-end CI/CD flow:
**Local dev → PR validation → Build → Artifact store → Dev → QA gate → Staging → Prod → Post-deploy monitoring.**

Everything runs **locally** on Docker — no cloud account required. The same workflows work unchanged when pushed to GitHub.

---

## Pieces

| Diagram stage | What it is here |
|---|---|
| 1. Onboarding | Clone repo, install Docker Desktop + [`act`](https://github.com/nektos/act) |
| 2. Local development | [app/](app/), [`scripts/dev-loop.ps1`](scripts/dev-loop.ps1) |
| 3. Git repository | Local `git init` (or push to GitHub) |
| 4. PR & review | GitHub PR (or `act pull_request`) |
| 5. PR Validation Pipeline | [.github/workflows/pr-validation.yml](.github/workflows/pr-validation.yml) — build, lint, bandit, pytest, pip-audit |
| 6. Merge to main | `git merge` |
| 7. Build & package | [.github/workflows/main-build.yml](.github/workflows/main-build.yml) — `docker build` |
| 8. Artifact store | Local Docker registry on `localhost:5000` ([docker-compose.registry.yml](docker-compose.registry.yml)) |
| 9. Deploy to Dev | [.github/workflows/deploy-dev.yml](.github/workflows/deploy-dev.yml) → [docker-compose.dev.yml](docker-compose.dev.yml) on port **8001** |
| 10. QA testing | [.github/workflows/qa-tests.yml](.github/workflows/qa-tests.yml) — `tests/integration/` + `tests/smoke/` |
| 11. QA gate | Pass/fail of the QA workflow |
| 12. Deploy to UAT/Staging | [.github/workflows/deploy-staging.yml](.github/workflows/deploy-staging.yml) → port **8002** |
| 13. Release approval | GitHub protected `production` environment (manual trigger under `act`) |
| 14. Deploy to Prod | [.github/workflows/deploy-prod.yml](.github/workflows/deploy-prod.yml) → port **8003** |
| 15. Post-deploy monitoring | 60-second health watch inside `deploy-prod.yml` |

## Prereqs

1. Docker Desktop running (Linux containers).
2. `act` installed — Windows: `winget install nektos.act` or `choco install act-cli`.
3. Python 3.12+ (only needed for the local `dev-loop` script — CI itself runs in containers).

## One-time setup: start the artifact store

```powershell
.\scripts\registry-up.ps1
```

This starts a Docker registry on `localhost:5000`. Verify with `curl http://localhost:5000/v2/_catalog`.

## Run the full pipeline

```powershell
# PR validation → build → push to registry → deploy dev → QA tests
.\scripts\run-pipeline.ps1

# Then promote (manual gates, just like real life):
.\scripts\run-pipeline.ps1 -Stage staging -ImageTag latest
.\scripts\run-pipeline.ps1 -Stage prod    -ImageTag latest
```

Run a single stage at a time:

```powershell
.\scripts\run-pipeline.ps1 -Stage pr      # just lint + tests + security scan
.\scripts\run-pipeline.ps1 -Stage build   # build + push image
.\scripts\run-pipeline.ps1 -Stage dev     # deploy to dev
.\scripts\run-pipeline.ps1 -Stage qa      # integration + smoke against dev
```

After deploy, hit the running environments directly:

```
http://localhost:8001/health    # dev
http://localhost:8002/health    # staging
http://localhost:8003/health    # prod
```

## Try it without act (pure Python)

```powershell
.\scripts\dev-loop.ps1    # creates .venv, installs deps, runs ruff + unit tests
```

Run the app directly:

```powershell
python -m app.main
# then visit http://localhost:8000/items
```

## Tear it all down

```powershell
.\scripts\teardown.ps1
```

## Going to real GitHub

The workflows under [.github/workflows/](.github/workflows/) work as-is on GitHub. To match production realities you'd typically:

- Swap `localhost:5000` for `ghcr.io/<owner>/cicd-demo` and add a `docker/login-action` step.
- Configure protected **environments** `staging` and `production` in repo Settings → Environments to enforce reviewer approvals.
- Add the deploy targets as self-hosted runners or replace the `docker compose` steps with `ssh` / `terraform apply`.
- Push artifacts (coverage reports, manifests) somewhere durable.

## Layout

```
.
├── app/                     Flask service (health, version, items CRUD)
├── tests/
│   ├── unit/                Fast tests against the app in-process
│   ├── integration/         API tests against a running container
│   └── smoke/               Minimal post-deploy probes
├── .github/workflows/       6 workflows = 6 pipeline stages
├── docker-compose.*.yml     One stack per environment + registry
├── scripts/                 PowerShell helpers
├── Dockerfile               App image
└── pyproject.toml           ruff / pytest / bandit config
```

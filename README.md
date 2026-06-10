# CI/CD Flow Demo (Python + Docker + GitHub Actions + act)

A minimal, runnable implementation of the end-to-end CI/CD flow:
**Local dev → PR validation → Build → Artifact store → Dev → QA gate → Staging → Prod → Post-deploy monitoring.**

Everything runs **locally** on Docker — no cloud account required. The same workflows work unchanged when pushed to GitHub.

> See [CHECKLISTS.md](CHECKLISTS.md) for a developer workflow checklist (pre-dev → post-merge) and a step-by-step local-testing checklist.

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

1. **Docker Desktop** running (Linux containers mode).
2. **Python 3.10+** on `PATH` (`python --version`).
3. **`act`** (only for running the CI workflows locally). Install on Windows:
   ```powershell
   winget install --id nektos.act
   ```
   > After install, **open a fresh PowerShell window** — winget adds `act` to PATH but existing shells won't see it until you reopen them. Verify with `act --version`.

---

## Path A — Run just the app (fastest, no CI)

Use this when you just want to play with the Flask service.

1. **Create venv + install + run unit tests + lint** (one command does it all):
   ```powershell
   .\scripts\dev-loop.ps1
   ```
   Expect: `11 passed`, `All checks passed!`
2. **Start the app**:
   ```powershell
   .\.venv\Scripts\python.exe -m app.main
   ```
3. **Hit it** in another shell:
   ```powershell
   curl.exe http://localhost:8000/health
   curl.exe http://localhost:8000/version
   curl.exe -X POST http://localhost:8000/items -H "Content-Type: application/json" -d '{\"name\":\"widget\",\"price\":9.99}'
   curl.exe http://localhost:8000/items
   ```
4. **Stop**: `Ctrl+C` in the app shell.

---

## Path B — Run the full CI/CD pipeline locally

This drives every workflow under [.github/workflows/](.github/workflows/) via `act`, in the same order as the diagram.

### Step 1 — Start the local artifact store (stage 8)

```powershell
.\scripts\registry-up.ps1
```

Verify the registry is up:
```powershell
curl.exe http://localhost:5000/v2/_catalog
# expect: {"repositories":[]}
```

### Step 2 — Run PR Validation (stage 5)

Build + lint + bandit + unit tests + `pip-audit`:
```powershell
.\scripts\run-pipeline.ps1 -Stage pr
```
All 5 jobs should print `🏁 Job succeeded`.

> 💡 If `pip-audit` flags a CVE, that's the gate doing its job — bump the offending package in [requirements.txt](requirements.txt) and re-run. Don't drop `--strict` to silence it.

### Step 3 — Build & push the image (stages 7 + 8)

```powershell
.\scripts\run-pipeline.ps1 -Stage build
```
Verify the image landed in the registry:
```powershell
curl.exe http://localhost:5000/v2/cicd-demo/tags/list
# expect: {"name":"cicd-demo","tags":["<short-sha>","latest"]}
```

### Step 4 — Deploy to Dev (stage 9)

```powershell
.\scripts\run-pipeline.ps1 -Stage dev
```
Wait for `Attempt N: healthy`, then verify:
```powershell
curl.exe http://localhost:8001/health
# expect: {"message":"hello world","status":"ok"}
curl.exe http://localhost:8001/version
# expect: environment=dev
```

### Step 5 — Run QA Tests + Gate (stages 10 + 11)

```powershell
.\scripts\run-pipeline.ps1 -Stage qa
```
Expect: 4 integration + 2 smoke tests pass, then `[QA GATE] Integration + smoke suites passed.`

### Step 6 — Promote to Staging (stage 12)

After QA passes (the human approval), promote the same image:
```powershell
.\scripts\run-pipeline.ps1 -Stage staging -ImageTag latest
curl.exe http://localhost:8002/health    # staging
```

### Step 7 — Release to Production (stages 13 + 14 + 15)

```powershell
.\scripts\run-pipeline.ps1 -Stage prod -ImageTag latest
curl.exe http://localhost:8003/health    # prod
```
The prod workflow includes a 60-second health watch as post-deploy monitoring.

### Or: do steps 2–5 in one shot

```powershell
.\scripts\run-pipeline.ps1   # runs pr → build → dev → qa
```

Then run staging / prod separately when you're ready to "approve" each gate.

---

## Tear it all down

```powershell
.\scripts\teardown.ps1
```
Stops every container the demo brought up (registry + dev + staging + prod).

---

## Troubleshooting (real things that bit during the first run)

| Symptom | Fix |
|---|---|
| `act` not found in your PowerShell session right after `winget install` | Open a **new** PowerShell window — winget's PATH update isn't visible to existing shells |
| `act` errors with "Cannot connect to the Docker daemon" | Start Docker Desktop |
| `docker push localhost:5000/...` connection refused | Registry container is down — `.\scripts\registry-up.ps1` |
| Port 8001 / 8002 / 8003 / 5000 already in use | Stop the other service, or change the `ports:` mapping in the relevant compose file |
| `pip-audit --strict` fails in PR validation | A CVE landed in a pinned dep — bump the version in `requirements.txt`. Do **not** drop `--strict` |
| Integration test `test_create_then_get_then_delete` returns 404 after POST | Gunicorn workers > 1 split in-memory state across processes. The [Dockerfile](Dockerfile) is pinned to `--workers 1` for this demo; a real service would use Redis/a DB |
| `upload-artifact@v4` fails with `ACTIONS_RUNTIME_TOKEN` missing | Make sure `--artifact-server-path=.act-artifacts` is in [.actrc](.actrc) |

## Environment Variables & Secrets

The workflows use a mix of **GitHub Secrets** (sensitive values you store in the GitHub UI — never in the codebase) and **workflow inputs** (non-sensitive parameters with safe defaults).

### GitHub Secrets — configure once in the GitHub UI

These are the only values you must store as secrets. GitHub encrypts them and injects them at runtime; they are never visible in logs or code.

| Secret | Required | Purpose |
|---|---|---|
| `REGISTRY_USER` | Only for private registries | Username for Docker registry login |
| `REGISTRY_PASSWORD` | Only for private registries | Password for Docker registry login |

If you're using a public or local registry (`localhost:5000`, GHCR with a token), these are optional — the build workflow will skip the login step automatically if they're not set.

**How to add them (repository-level):**
1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add `REGISTRY_USER` and `REGISTRY_PASSWORD`

**Recommended — environment-level secrets** (scopes credentials per environment, enables approval gates):
1. Go to **Settings** → **Environments** → create `staging` and `production`
2. Under each environment, add the secrets there instead
3. Add required reviewers to enforce manual approval before deploys

> Environment-level secrets override repository-level ones for that environment — useful when staging and prod use different registries or credentials.

---

### Workflow Inputs — non-sensitive, set at dispatch time

These are passed when triggering a workflow manually (`workflow_dispatch`). They have safe defaults and should **not** be stored as secrets.

| Variable | Default | Which workflows | Purpose |
|---|---|---|---|
| `REGISTRY` | `localhost:5000` | build, deploy-dev/staging/prod | Docker registry URL |
| `IMAGE_NAME` | `cicd-demo` | build, deploy-dev/staging/prod | Docker image name |
| `IMAGE_TAG` | auto (short `GITHUB_SHA`) | build, deploy-dev/staging/prod | Tag to build or deploy |
| `MODE` | `build-and-push` | main-build | `build-and-push` or `build-only` |
| `APP_PORT` | `8001` / `8002` / `8003` | deploy-dev / staging / prod | Host port per environment |
| `TARGET_URL` | `http://host.docker.internal:8001` | qa-tests, smoke steps | URL the test suite hits |

These can be overridden at dispatch time without touching any files.

---

### Quick reference — what lives where

| Value | Where it lives | Why |
|---|---|---|
| `REGISTRY_USER` / `REGISTRY_PASSWORD` | GitHub Secrets (UI only) | Sensitive — never commit credentials |
| Registry URL, image name, ports | Workflow inputs with defaults | Non-sensitive, safe to change at runtime |
| `GITHUB_SHA` | GitHub built-in | Auto-injected, no setup needed |

---

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

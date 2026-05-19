# Project Context — CI/CD Flow Demo

> Reference doc for an LLM acting as a coding assistant on this repo. Self-contained: do **not** assume prior conversation context.

## 1. Purpose

A runnable, end-to-end implementation of a 15-stage CI/CD flow, designed to run entirely on a developer's local machine using Docker and `nektos/act`. Same GitHub Actions workflows are intended to work unchanged on real GitHub (with registry/host substitutions noted in the README).

Repo: <https://github.com/j2v-inno/test-ci-cd>

Pipeline stages (numbering matches the source diagram):

| # | Stage | Implementation |
|---|---|---|
| 1 | Onboarding | README prereqs |
| 2 | Local dev | `app/`, `scripts/dev-loop.ps1` |
| 3 | Git repo | local `git init` / GitHub |
| 4 | PR & review | GitHub PR / `act pull_request` |
| 5 | PR Validation | `.github/workflows/pr-validation.yml` |
| 6 | Merge to main | `git merge` |
| 7 | Build & package | `.github/workflows/main-build.yml` |
| 8 | Artifact store | local Docker registry on `localhost:5000` (`docker-compose.registry.yml`) |
| 9 | Deploy to Dev | `.github/workflows/deploy-dev.yml` → `:8001` |
| 10 | QA testing | `.github/workflows/qa-tests.yml` |
| 11 | QA gate | workflow pass/fail |
| 12 | Deploy to Staging | `.github/workflows/deploy-staging.yml` → `:8002` |
| 13 | Release approval | GitHub protected env `production` |
| 14 | Deploy to Prod | `.github/workflows/deploy-prod.yml` → `:8003` |
| 15 | Post-deploy monitoring | 60-second health watch inside `deploy-prod.yml` |

## 2. Stack

- **Language**: Python (project pins 3.12 in CI; works on 3.10+ locally because of `from __future__ import annotations`)
- **Web framework**: Flask 3.1.3
- **WSGI server**: gunicorn 22.0.0
- **Container**: Docker (single multi-stage `Dockerfile`)
- **Orchestration**: `docker compose` (one file per environment)
- **CI**: GitHub Actions, runnable locally with `nektos/act` 0.2.88+
- **Artifact store**: local `registry:2` container on `:5000`
- **Lint / format**: ruff 0.6.9 (rules `E,F,W,I,B,UP`, line length 100)
- **Security scan**: bandit 1.7.10
- **Dependency audit**: pip-audit 2.7.3 (`--strict` mode)
- **Tests**: pytest 8.3.3 + pytest-cov 5.0.0; HTTP client `requests` 2.32.3
- **Shell scripts**: PowerShell (project is Windows-first; `.ps1` helpers under `scripts/`)

## 3. Repository layout

```
.
├── app/
│   ├── __init__.py            re-exports create_app
│   ├── main.py                Flask app factory; defines routes
│   └── items.py               in-process thread-safe ItemStore (no persistence)
├── tests/
│   ├── unit/                  in-process Flask test client; runs in PR validation
│   ├── integration/           requests-based; runs in QA stage against deployed env
│   └── smoke/                 minimal /health + /version probes; runs post-deploy
├── .github/workflows/         6 workflows — one per pipeline stage 5,7,9,10,12,14
├── scripts/
│   ├── dev-loop.ps1           venv + ruff + pytest (Path A: no CI)
│   ├── registry-up.ps1        starts local Docker registry
│   ├── registry-down.ps1      stops local Docker registry
│   ├── run-pipeline.ps1       drives act through stages: pr/build/dev/qa/staging/prod
│   └── teardown.ps1           docker compose down for all envs + registry
├── docker-compose.dev.yml     :8001  APP_ENV=dev
├── docker-compose.staging.yml :8002  APP_ENV=staging
├── docker-compose.prod.yml    :8003  APP_ENV=prod (+ resource limits)
├── docker-compose.registry.yml :5000 (artifact store)
├── Dockerfile                 python:3.12-slim, gunicorn, --workers 1
├── requirements.txt           runtime deps only
├── requirements-dev.txt       includes test/lint/audit tooling
├── pyproject.toml             ruff + pytest + bandit config
├── .actrc                     act flags (image override, artifact server path)
├── .dockerignore
├── .gitignore                 excludes .venv, .act/, .act-artifacts/
├── README.md                  human-facing usage docs with 7-step walkthrough
├── CHECKLISTS.md              dev-workflow + local-test checklists
└── PROJECT_CONTEXT.md         this file
```

## 4. The Flask app

Tiny CRUD over an in-memory `ItemStore` (`app/items.py`). Endpoints in `app/main.py`:

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{"status":"ok","message":"hello world"}` |
| GET | `/version` | `{"version","environment","commit"}` (env vars `APP_ENV`, `GIT_COMMIT`) |
| GET | `/items` | list of items |
| POST | `/items` | create (body: `{"name":str,"price":float}`); 400 on invalid |
| GET | `/items/<id>` | get; 404 if missing |
| DELETE | `/items/<id>` | 204 / 404 |

The store is in-process and not shared across gunicorn workers — see [§7](#7-decisions--gotchas).

## 5. Workflow contracts

All workflows take `workflow_dispatch` so they can be triggered manually via `act` (or the GitHub UI). Push/PR triggers exist for real GitHub.

| Workflow | Triggers | Notable inputs |
|---|---|---|
| `pr-validation.yml` | `pull_request[main]`, `workflow_dispatch` | none — 5 parallel jobs |
| `main-build.yml` | `push[main]`, `workflow_dispatch` | computes tag from `${GITHUB_SHA::7}`; pushes `:<sha>` + `:latest` to `localhost:5000/cicd-demo` |
| `deploy-dev.yml` | `workflow_run[main-build success]`, `workflow_dispatch` | `image_tag` (default `latest`) |
| `qa-tests.yml` | `workflow_run[deploy-dev success]`, `workflow_dispatch` | `target_url` (default `http://host.docker.internal:8001`) |
| `deploy-staging.yml` | `workflow_dispatch` only | `image_tag` required; gated by `environment: staging` |
| `deploy-prod.yml` | `workflow_dispatch` only | `image_tag` required; gated by `environment: production`; 60s post-deploy health watch |

The `environment:` keys are GitHub protected-environment names; on `act` they no-op. On real GitHub they enforce reviewer approval (release approval gate, stage 13).

## 6. Environments

| Env | Port | `APP_ENV` | docker-compose | Container name |
|---|---|---|---|---|
| dev | 8001 | `dev` | `docker-compose.dev.yml` | `cicd-demo-dev` |
| staging | 8002 | `staging` | `docker-compose.staging.yml` | `cicd-demo-staging` |
| prod | 8003 | `prod` | `docker-compose.prod.yml` | `cicd-demo-prod` |
| registry | 5000 | — | `docker-compose.registry.yml` | `cicd-registry` |

All envs pull `localhost:5000/cicd-demo:${IMAGE_TAG:-latest}`. Tests inside `act` containers reach the host's published ports via `host.docker.internal` (provided automatically by Docker Desktop on Windows/Mac).

## 7. Decisions & gotchas

These are non-obvious choices baked into the repo. Preserve them unless the user explicitly asks to change.

1. **Single gunicorn worker** — `Dockerfile` pins `--workers 1`. The `ItemStore` is per-process. Adding workers without a shared backing store (Redis/DB) breaks CRUD (POST → worker A, GET → worker B → 404). The Dockerfile comments this; don't silently bump it.
2. **bandit B104 suppressed** in `app/main.py` for `app.run(host="0.0.0.0")` — required for container port forwarding. The suppression carries a `# nosec B104` and an inline comment.
3. **`from __future__ import annotations`** is on in `app/items.py` and `app/main.py`. PEP 604 syntax like `Item | None` is therefore string-only and compatible with Python 3.10.
4. **`.actrc` quirks**:
   - `--container-options` is a single-string flag; declaring it multiple times confuses `act`'s arg parser. Don't add a second line.
   - `.actrc` splits on whitespace, so flag *values* with spaces also break parsing.
   - `--artifact-server-path=.act-artifacts` is required so `actions/upload-artifact@v4` doesn't fail with `ACTIONS_RUNTIME_TOKEN`.
   - On Docker Desktop, `host.docker.internal` resolves without `--add-host`; on Linux it would need it.
5. **`pip-audit --strict`** is the security gate. When a CVE lands (e.g. flask 3.0.3 → GHSA-68rp-wp8r-4726), the correct fix is to bump the pinned version in `requirements.txt`. Do not drop `--strict` to silence findings.
6. **Image tag scheme**: `${GITHUB_SHA::7}` short SHA, plus `latest`. Promotion across environments uses the same explicit tag — never re-tag `latest` for prod releases.
7. **`localhost:5000` is local-only**. Pushing this repo's workflows to real GitHub Actions will fail on the build stage because the cloud runner can't reach a local registry. Going to real GitHub requires swapping for `ghcr.io/<owner>/cicd-demo` plus a `docker/login-action` step (called out in README "Going to real GitHub").
8. **Windows-first scripting**. Helper scripts are PowerShell. `act` is installed via `winget install --id nektos.act`. After install, a fresh PowerShell window is required for `act` to be on PATH.
9. **Coverage** is reported during unit tests (`pytest --cov=app --cov-report=term-missing`) but is **not** gated. There's no minimum threshold.
10. **In-memory state is intentional**. Don't propose adding a database/Redis unless the user asks — it would balloon the demo and obscure the pipeline mechanics, which is the point of the repo.

## 8. Conventions to follow when editing

- Prefer `Edit` over `Write` for existing files.
- Don't add comments explaining *what* the code does — names already do that. Only add a comment for non-obvious *why* (e.g. the `# nosec B104`, the `--workers 1` rationale, the `.actrc` parsing constraint).
- Keep tests next to the stage that runs them: `tests/unit/` for PR validation, `tests/integration/` for QA, `tests/smoke/` for post-deploy.
- If you add a workflow, mirror the existing style: `workflow_dispatch` always present, explicit `runs-on: ubuntu-latest`, named jobs, `needs:` between dependent jobs.
- Don't commit unless the user explicitly asks. Don't push to remote unless asked.
- Don't bypass quality gates. If `pip-audit`/bandit/ruff fail, fix the cause.

## 9. Verified end-to-end

The complete pipeline (PR validation → build → deploy dev → QA tests) has been run successfully via `act` on a Windows + Docker Desktop machine. Final state:

- PR Validation: 5/5 jobs green (build, lint, bandit, pip-audit, unit tests)
- Main Build: image pushed to `localhost:5000/cicd-demo:<sha>` and `:latest`
- Deploy to Dev: container reports `healthy`, post-deploy smoke passes
- QA Tests: 4 integration + 2 smoke pass, QA Approval Gate prints success

Staging and prod stages exist and use identical mechanics, just on different ports.

## 10. How to run (one-liner pointers)

- **Just the app, no CI**: `.\scripts\dev-loop.ps1` then `.\.venv\Scripts\python.exe -m app.main`
- **Full pipeline locally**: `.\scripts\registry-up.ps1` then `.\scripts\run-pipeline.ps1`
- **Promote**: `.\scripts\run-pipeline.ps1 -Stage staging -ImageTag latest`; same with `-Stage prod`
- **Tear down**: `.\scripts\teardown.ps1`

See `README.md` for the full step-by-step. See `CHECKLISTS.md` for dev-workflow + local-test checklists.

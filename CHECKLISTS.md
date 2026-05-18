# Checklists

Two checklists:

1. **[Developer workflow](#1-developer-workflow)** — what to do before you start coding and after you push/merge.
2. **[Local pipeline testing](#2-local-pipeline-testing)** — how to run this demo end-to-end on your machine.

---

## 1. Developer workflow

Numbers in `()` reference the stages in the CI/CD diagram.

### Pre-dev (stages 1–2)

- [ ] **Pull latest** — `git checkout main && git pull`
- [ ] **Cut a feature branch** — `git checkout -b feat/<short-name>` (never commit straight to `main`)
- [ ] **Activate / refresh local env** — `.\.venv\Scripts\Activate.ps1`; if `requirements*.txt` changed since you last pulled, re-run `pip install -r requirements-dev.txt`
- [ ] **Docker Desktop running** (only if your change touches `Dockerfile`, `docker-compose.*.yml`, or container behavior)
- [ ] **Understand the ticket** — acceptance criteria, expected endpoints/fields, who reviews

### While coding (stage 2)

- [ ] Write or update a **unit test** alongside the change — never push code without one
- [ ] If the change adds an HTTP-visible behavior, add an **integration test** in [tests/integration/](tests/integration/)
- [ ] Keep commits **small and focused** — one logical change per commit, clear message
- [ ] Re-run [`scripts/dev-loop.ps1`](scripts/dev-loop.ps1) frequently — it's the fastest feedback you have

### Pre-push (the PR Validation gates you locally before CI does)

- [ ] **Rebase on main** — `git fetch origin && git rebase origin/main` (resolve conflicts now, not in CI)
- [ ] **Lint clean** — `ruff check . && ruff format --check .`
- [ ] **Unit tests green** — `pytest tests/unit`
- [ ] **Security scan clean** — `bandit -r app -ll`
- [ ] **Dependency audit clean** (only if you touched `requirements.txt`) — `pip-audit -r requirements.txt --strict`
- [ ] **Container builds** (only if you touched `Dockerfile` or `app/`) — `docker build -t cicd-demo:dev .`
- [ ] **No secrets in the diff** — scan for tokens, passwords, `.env` files

### Post-push (stages 3–5)

- [ ] **PR opened** with a description that says **what** and **why** (not how — the diff shows that)
- [ ] **All PR Validation checks green** in the Actions tab (build / lint / static-analysis / unit-tests / security-scan)
- [ ] **Self-review the diff first** — comment on anything non-obvious before a reviewer has to ask
- [ ] **Request reviewers** — at least one approver per your team's rules
- [ ] **Respond to every review comment** — don't silently push fixes
- [ ] **Do not merge** until: ≥1 approval AND all checks green AND no unresolved threads

### Post-merge (stages 6–10)

- [ ] **Watch `Main Build & Package`** run on `main` — fix forward immediately if it goes red (a red `main` blocks everyone)
- [ ] **Watch `Deploy to Dev`** complete and its smoke job pass — your change is live on `dev`
- [ ] **Watch `QA Tests`** — if it fails, this is *your* fault to triage (you're the most recent change)
- [ ] **Notify QA** if your change needs targeted manual testing on `dev`
- [ ] **Don't pile a hot release on top** — let your change soak on `dev` while QA exercises it
- [ ] **Delete the merged branch** — `git push origin --delete feat/<short-name>`

### Promotion (stages 12–14)

- [ ] **Wait for QA pass** before triggering `Deploy to Staging`
- [ ] **Coordinate the prod release** — release notes, stakeholders aware, on-call covered
- [ ] **Trigger `Deploy to Production`** with the exact image tag you tested in staging — never re-tag `latest`
- [ ] **Watch the post-deploy monitoring window** (stage 15) — if it goes red, roll back to the previous tag

---

## 2. Local pipeline testing

How to drive every stage of the pipeline on your machine.

### One-time prerequisites

- [ ] **Docker Desktop** installed and running (Linux containers mode)
- [ ] **Python 3.10+** on PATH (`python --version`)
- [ ] **act** installed — `act --version` should print `0.2.88` or newer
- [ ] **Repo cloned** and you `cd` into it

### First-run setup

- [ ] **Create venv + run unit tests + lint** — verifies the local-dev side works
  ```powershell
  .\scripts\dev-loop.ps1
  ```
  Expect: `11 passed`, `All checks passed!`
- [ ] **Start the local artifact store** (stage 8)
  ```powershell
  .\scripts\registry-up.ps1
  ```
- [ ] **Verify the registry is reachable**
  ```powershell
  curl http://localhost:5000/v2/_catalog
  ```
  Expect: `{"repositories":[]}`

### Run each stage individually

Run them in order the first time — later you can jump to a single stage.

- [ ] **Stage 5 — PR Validation** (lint + unit tests + security scan)
  ```powershell
  .\scripts\run-pipeline.ps1 -Stage pr
  ```
  Expect: all 5 jobs (build, lint, static-analysis, unit-tests, security-scan) green
- [ ] **Stage 7 + 8 — Build & push to registry**
  ```powershell
  .\scripts\run-pipeline.ps1 -Stage build
  ```
  Verify: `curl http://localhost:5000/v2/cicd-demo/tags/list` lists your tag
- [ ] **Stage 9 — Deploy to dev**
  ```powershell
  .\scripts\run-pipeline.ps1 -Stage dev
  ```
  Verify: `curl http://localhost:8001/health` → `{"status":"ok"}`
  Verify: `curl http://localhost:8001/version` shows `"environment":"dev"`
- [ ] **Stage 10 + 11 — QA tests + gate**
  ```powershell
  .\scripts\run-pipeline.ps1 -Stage qa
  ```
  Expect: integration + smoke suites pass against `http://localhost:8001`
- [ ] **Stage 12 — Deploy to staging** (the "QA approved" promotion)
  ```powershell
  .\scripts\run-pipeline.ps1 -Stage staging -ImageTag latest
  ```
  Verify: `curl http://localhost:8002/health` → `{"status":"ok"}`
- [ ] **Stages 13–15 — Release approval + prod + post-deploy monitoring**
  ```powershell
  .\scripts\run-pipeline.ps1 -Stage prod -ImageTag latest
  ```
  Verify: `curl http://localhost:8003/health` → `{"status":"ok"}`
  Watch: the 60-second health watch in the workflow output stays green

### Or: full pipeline up to the QA gate, in one shot

- [ ] `.\scripts\run-pipeline.ps1` runs `pr → build → dev → qa` back-to-back. Then promote with the `staging` / `prod` stages above.

### Smoke-check the running app by hand

- [ ] Each env exposes the same API; only `APP_ENV` and the port differ.
  ```powershell
  curl http://localhost:8001/items                                    # list (dev)
  curl -X POST http://localhost:8001/items -H "Content-Type: application/json" -d '{"name":"widget","price":9.99}'
  curl http://localhost:8001/items/1
  curl -X DELETE http://localhost:8001/items/1
  ```
- [ ] Try the same against `:8002` (staging) and `:8003` (prod) — note that the in-memory store is **per-container**, so state doesn't carry between envs.

### Tear down

- [ ] **Stop every container the demo brought up**
  ```powershell
  .\scripts\teardown.ps1
  ```
- [ ] **Wipe the venv** (only if you want a fully clean slate)
  ```powershell
  Remove-Item -Recurse -Force .venv
  ```

### Common troubleshooting

| Symptom | Fix |
|---|---|
| `act` errors with "Cannot connect to the Docker daemon" | Docker Desktop isn't running — start it |
| `docker push localhost:5000/...` fails with "connection refused" | Registry container is down — `.\scripts\registry-up.ps1` |
| Port `8001`/`8002`/`8003`/`5000` already in use | Either stop the other service, or change the `ports:` mapping in the relevant compose file |
| `host.docker.internal` doesn't resolve inside an act job | Make sure [.actrc](.actrc) is present in the repo root — it adds the host-gateway mapping |
| QA tests fail with "app never became healthy" | Dev stack didn't come up — `docker logs cicd-demo-dev` to see why |
| `pip-audit --strict` fails in PR validation | A new CVE landed in `flask`/`gunicorn` — bump the version in `requirements.txt`; do **not** drop `--strict` to silence it |

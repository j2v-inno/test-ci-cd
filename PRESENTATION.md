# Presentation: CI/CD Pipeline — From Code to Production
**Audience:** Mixed (engineers + stakeholders)
**Format:** Slide outline + talking points
**Assisted by:** Claude AI

---

## Slide 1 — Title Slide

**Title:** From Code to Production: A Modern CI/CD Pipeline
**Subtitle:** Automated, reliable, and repeatable software delivery
**Presenter:** [Your name] | [Date]

---

## Slide 2 — The Problem We're Solving

**Headline:** "Shipping software used to be risky and manual."

**Talking points:**
- Before CI/CD: developers would write code for days or weeks, then manually deploy — often breaking things
- Bugs found late are expensive to fix; bugs found in production are even more expensive
- Teams wasted time on repetitive checks (does it build? do tests pass? is it safe to ship?)
- CI/CD replaces all of that with an automated safety net — every change goes through the same gauntlet, every time

**For non-tech audience:** Think of it like a quality control line in a factory — every product gets inspected the same way before it ships. No shortcuts, no "we'll check it later."

---

## Slide 3 — What Is CI/CD?

**Headline:** "Two ideas, one pipeline."

**Talking points:**
- **CI (Continuous Integration):** Every code change is automatically built, tested, and verified the moment it's submitted — no waiting, no manual steps
- **CD (Continuous Delivery/Deployment):** Once code passes CI, it can be promoted through environments (Dev → Staging → Production) in a controlled, automated way
- The goal: make deployments boring — small, frequent, predictable, reversible

**Visual suggestion:** A simple left-to-right arrow: `Code → Test → Build → Deploy`

---

## Slide 4 — Our Pipeline at a Glance (15 Stages)

**Headline:** "15 stages. One goal: confidence before production."

**Visual suggestion:** The CI/CD flow diagram (horizontal pipeline, color-coded by phase)

**Talking points:**
- Walk through the four phases at a high level (don't go deep here — the next slides do that):
  1. **Development** — write code, open a PR
  2. **Validation** — automated checks run on every PR
  3. **Build & Package** — create a deployable artifact (Docker image)
  4. **Promote** — move through Dev → QA → Staging → Production with gates at each step
- Every arrow in the diagram is automated; every gate is a deliberate checkpoint

---

## Slide 5 — Phase 1: Developer Workflow (Stages 1–4)

**Headline:** "It starts with a developer and a branch."

**Talking points:**
- Developer clones the repo, creates a feature branch, writes code locally
- Local tools (linter, unit tests) give immediate feedback before anything hits the server
- When ready: open a **Pull Request** — this is the trigger that starts the automated pipeline
- A PR is also where human code review happens — the pipeline and the review run in parallel

**For non-tech audience:** A pull request is like submitting a proposal — before any change goes in, it gets reviewed by the system AND by teammates.

---

## Slide 6 — Phase 2: PR Validation Pipeline (Stage 5)

**Headline:** "5 automated checks run on every single PR."

**Talking points (each is a job in `pr-validation.yml`):**
1. **Compile** — does the code even run? Catches syntax errors immediately
2. **Lint** — enforces code style; keeps the codebase consistent and readable
3. **Static analysis (Bandit)** — scans for common security vulnerabilities in the code itself
4. **Unit tests** — 11 fast tests that verify the app logic works correctly
5. **Dependency scan (pip-audit)** — checks every third-party library for known CVEs
6. **Secret scanning (gitleaks)** — scans the full git history for accidentally committed credentials, tokens, or private keys

- All 6 must pass. One failure blocks the merge.
- This stage typically runs in under 2 minutes.
- gitleaks version is configurable per project via a GitHub repository variable (`GITLEAKS_VERSION`) — no code change needed to upgrade or pin it across projects.

**Key message:** Problems caught here cost almost nothing to fix. Problems caught in production can cost days — and a leaked credential can cost far more than that.

---

## Slide 7 — Phase 3: Build & Package (Stages 6–8)

**Headline:** "Merge to main triggers the build."

**Talking points:**
- Once a PR is approved and merged, the **Main Build** workflow fires automatically
- It builds a **Docker image** — a self-contained package that includes the app and everything it needs to run
- The image is tagged with the Git commit SHA (a unique fingerprint) so every build is traceable
- The image is pushed to the **artifact store** (Docker registry) — a versioned library of deployable images
- From this point on, what gets deployed is always a specific, immutable image — not "whatever's on the server"

**For non-tech audience:** Think of the Docker image as a sealed box. Everything the app needs is inside. You ship the same sealed box to Dev, Staging, and Production — no surprises.

---

## Slide 8 — Phase 4: Promote Through Environments (Stages 9–15)

**Headline:** "Same image. Three environments. Manual gates between each."

**Visual suggestion:** Three boxes left-to-right: Dev (port 8001) → Staging (port 8002) → Production (port 8003), with gate icons between them

**Talking points:**
- **Dev (auto):** Image is deployed automatically after a successful build. A smoke test confirms it's alive.
- **QA Gate (manual trigger):** Full integration + smoke test suite runs. A human reviews the results before promotion.
- **Staging (manual approval):** A protected environment — requires an authorized reviewer to approve before the workflow can run.
- **Production (release approval):** Second protected gate. Release notes are logged. After deploy, a 60-second health watch monitors the live service.

**Key message:** Automation handles the mechanics; humans make the go/no-go calls at the right moments.

---

## Slide 9 — What "Healthy" Looks Like

**Headline:** "Every deploy is verified, not assumed."

**Talking points:**
- After each deploy, the workflow waits for the container to report **healthy** (up to 60 seconds, checking every 2 seconds)
- If health check fails → workflow fails, logs are printed automatically, no silent failures
- Smoke tests hit the live `/health` and `/version` endpoints to confirm the right version is running
- In production: an additional 60-second monitoring loop polls `/health` every 10 seconds post-deploy

**For non-tech audience:** It's like a nurse checking vitals after surgery — we don't leave until we know the patient is stable.

---

## Slide 10 — How Claude AI Was Used in This Project

**Headline:** "Claude AI as a development partner."

**Talking points:**
- Used throughout the project for: explaining workflow decisions, generating documentation, answering "what env vars do we need?" questions
- The README's **Environment Variables & Secrets** section — written with Claude's help after asking: *"based on the workflows, what environment variables should we have?"*
- Claude helped explain **how GitHub Secrets work** and why credentials should never live in code
- Used to review workflow YAML for missing steps, error handling, and best practices
- Claude AI doesn't replace engineers — it accelerates the work engineers are already doing

**Demo opportunity:** Live Q&A with Claude about the pipeline (e.g., ask it to explain a workflow step, or ask what would happen if REGISTRY_PASSWORD was missing).

---

## Slide 11 — Secrets & Security

**Headline:** "Credentials never touch the codebase."

**Talking points:**
- Two secrets are used: `REGISTRY_USER` and `REGISTRY_PASSWORD` (for pushing images to a private registry)
- These live in **GitHub's encrypted secrets store** — injected at runtime, masked in all logs
- Environment-level secrets allow `staging` and `production` to use different credentials
- Protected environments enforce **required reviewers** before any deploy can run
- The pipeline itself enforces security: `pip-audit` blocks merges if a known CVE is found in dependencies

---

## Slide 12 — Running It Locally

**Headline:** "The entire pipeline runs on your laptop."

**Talking points:**
- Tool used: [`act`](https://github.com/nektos/act) — runs GitHub Actions workflows locally inside Docker
- No cloud account, no GitHub billing, no waiting for CI runners
- The same 6 workflow files run identically locally and on real GitHub
- One command runs the full pipeline: `.\scripts\run-pipeline.ps1`
- Useful for: onboarding new devs, debugging failures, demoing the pipeline without internet

---

## Slide 13 — Key Takeaways

**Headline:** "What this pipeline gives you."

**Talking points:**
1. **Speed** — feedback in minutes, not hours; small frequent deployments instead of big risky ones
2. **Consistency** — every change goes through the same process; no "it works on my machine"
3. **Safety** — security scans, health checks, and approval gates prevent bad code from reaching production
4. **Traceability** — every deployed image is tagged to a specific commit; you always know exactly what's running
5. **Confidence** — when a deploy goes out, the team knows it passed every gate

---

## Slide 14 — Q&A / Live Demo

**Options for a live demo:**
- Run `.\scripts\run-pipeline.ps1 -Stage pr` and show PR validation passing in real time
- Show the GitHub Actions UI with workflow runs
- Open Claude AI and ask it a live question about the pipeline (e.g., "What happens if the health check fails in deploy-prod.yml?")

**Suggested closing line:**
> "The goal of a CI/CD pipeline isn't to slow down developers — it's to give them the confidence to ship fast, knowing that the system has their back."

---

## Appendix — Technical Reference

### Workflow summary

| Workflow | Trigger | What it does |
|---|---|---|
| `pr-validation.yml` | PR opened | Compile, lint, bandit, unit tests, pip-audit |
| `main-build.yml` | Push to main | Docker build + push to registry |
| `deploy-dev.yml` | After main-build | Deploy to dev (port 8001) + smoke |
| `qa-tests.yml` | After deploy-dev | Integration + smoke tests |
| `deploy-staging.yml` | Manual | Deploy to staging (port 8002) + smoke |
| `deploy-prod.yml` | Manual + approval | Deploy to prod (port 8003) + health watch |

### Environment variables quick ref

| Variable | Type | Where it lives |
|---|---|---|
| `REGISTRY_USER` | Secret | GitHub Secrets (UI) |
| `REGISTRY_PASSWORD` | Secret | GitHub Secrets (UI) |
| `REGISTRY` | Workflow input | Default: `localhost:5000` |
| `IMAGE_NAME` | Workflow input | Default: `cicd-demo` |
| `IMAGE_TAG` | Workflow input | Default: short `GITHUB_SHA` |
| `APP_PORT` | Workflow input | Default: 8001 / 8002 / 8003 |
| `TARGET_URL` | Workflow input | Default: `http://host.docker.internal:8001` |

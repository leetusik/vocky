# P6.S8 — CI production-deploy chain · result

Ported hi2vi_web's proven three-file GitHub Actions deploy chain to vocky, changing only the
documented vocky deltas. vocky had **no `.github/` before this slice** — all three files are net-new.
S7's `deploy/deploy.sh` was **not modified**: the chain reuses it unchanged (confirmed via
`git status` — clean).

## Files created

- **`.github/workflows/deploy-production.yml`** — manual `workflow_dispatch`, `permissions: contents:
  read`; `preflight` job (guards `refs/heads/main`, outputs `target_sha=GITHUB_SHA`); `deploy` job
  (`needs: preflight`, `timeout-minutes: 90`, `environment: { name: production, url:
  https://vocky.hi2vi.com }`, `concurrency: { group: vocky-deploy, cancel-in-progress: false }`).
  Steps: checkout target SHA → **Validate deploy helpers** (`bash -n deploy/deploy.sh
  deploy/github-actions-production-deploy.sh deploy/oracle-production-deploy-remote.sh` — references
  the existing S7 `deploy.sh`) → **Deploy through Oracle deploy.sh** (env `TARGET_SHA`,
  `ORACLE_SSH_PRIVATE_KEY`, `ORACLE_SSH_KNOWN_HOSTS`, `ORACLE_SSH_PASSPHRASE`, `ARTIFACT_DIR`) →
  **External smoke** → **Upload deploy artifacts** (`if: always()`).
  - **Smoke (vocky delta):** a `smoke()` helper checks **both** `https://vocky.hi2vi.com/healthz`
    (api via edge) and `https://vocky.hi2vi.com/` (web via edge), each retried 5×6s, each must return
    200; the step fails if **either** endpoint never returns 200. (hi2vi smoked a single `/`.)
- **`deploy/github-actions-production-deploy.sh`** (`+x`) — runner transport. Deltas from hi2vi:
  `ORACLE_REPO_PATH` default → `/home/opc/vocky`; remote temp names → `/tmp/vocky-gha-deploy-*` /
  `/tmp/vocky-gha-artifacts-*`; log prefix → `[vocky-deploy]`. SSH prep (temp key file, `umask 077`,
  `StrictHostKeyChecking=yes` + `UserKnownHostsFile`, optional passphrase via ssh-agent + askpass),
  `TARGET_SHA` 40-hex assert, `require_env` gating, artifact scp-back, and cleanup trap kept
  **verbatim**. Same box: `ORACLE_SSH_HOST` default `140.245.64.173`, user `opc`.
- **`deploy/oracle-production-deploy-remote.sh`** (`+x`) — on-box gate. Deltas from hi2vi: `REPO_PATH`
  default → `/home/opc/vocky`; `PROJECT_NAME` → `vocky`; `COMPOSE_ENV_FILE` → `.env`;
  `REMOTE_ARTIFACT_DIR` default → `/tmp/vocky-gha-artifacts`; `collect_status` → `docker compose -f
  compose.prod.yml ps` (no `-p`, no `--env-file` — mirrors deploy.sh's `dc()`). The dirty-tracked-tree
  refusal, `git fetch --prune origin main`, the `TARGET_SHA` ancestor-verify
  (`git merge-base --is-ancestor`), and the handoff `deploy/deploy.sh "${TARGET_SHA}"` are kept
  **exactly**.

## Verification (actual output)

| Check | Command | Result |
|---|---|---|
| Syntax, transport script | `bash -n deploy/github-actions-production-deploy.sh` | **PASS** |
| Syntax, on-box gate | `bash -n deploy/oracle-production-deploy-remote.sh` | **PASS** |
| Syntax, S7 deploy.sh (unchanged) | `bash -n deploy/deploy.sh` | **PASS** |
| Executable bit | `chmod +x` both new scripts | both `-rwxr-xr-x` |
| Workflow YAML parses | `uv run --with pyyaml python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy-production.yml'))"` | **PASS** — jobs `[preflight, deploy]`, `environment.url=https://vocky.hi2vi.com`, `concurrency.group=vocky-deploy` |
| Validate step references S7 deploy.sh | grep `deploy/deploy.sh` in workflow | line 54, and `deploy/deploy.sh` exists on disk |
| S7 deploy.sh untouched | `git status --short deploy/deploy.sh` | empty (no diff) |
| Workspace state | `python3 scripts/workflow.py validate` | **Workflow validation passed** |

- **`shellcheck` is NOT installed in this sandbox** — skipped; manual review done instead (the SSH,
  quoting, and control-flow lines are byte-for-byte faithful to hi2vi's proven scripts).
- **`actionlint` is NOT installed** — skipped; YAML structure validated via PyYAML `safe_load`. The
  system `python3` has no `yaml` module, so the parse ran under `uv run --with pyyaml` (no project
  mutation — no dependency added to `pyproject.toml`).
- **No CI run happened in this slice.** The workflow only fires on operator `workflow_dispatch` and
  needs the three `ORACLE_SSH_*` GitHub secrets **and** a live box + `.env` + DNS (S10). Behavioral
  proof of the chain (SSH transport, ancestor-verify gate, `deploy.sh` on the box, the external smoke)
  lands at S10 / the first real dispatch — as with S7.

## Deviations from plan

Faithful port; **no functional deviation** from the documented deltas. Two within-intent
adaptations, both cosmetic (product identity, not behavior):

1. **Product-name strings/comments** rewritten from hi2vi → vocky where they name the deploy's
   identity: the three files' header comments, and the on-box gate's artifact summary header
   (`# hi2vi Production Deploy Artifact` → `# vocky Production Deploy Artifact`). Leaving "hi2vi" in
   vocky's files would be actively wrong; the plan's core intent is a faithful *vocky* port. All
   logic, control flow, SSH/key handling, and the ancestor-verify gate are unchanged.
2. **`PROJECT_NAME` and `COMPOSE_ENV_FILE` are retained but not referenced.** The plan sets
   `PROJECT_NAME → vocky` and `COMPOSE_ENV_FILE → .env` **and** simplifies `collect_status` to
   `docker compose -f compose.prod.yml ps` (no `-p`, no `--env-file`, matching deploy.sh's `dc()`),
   which leaves those two vars unreferenced. Kept as declared per the plan (documenting the deploy
   identity); an inline comment explains that `dc()` pins no project and lets compose auto-read
   `./.env`. (Would be a shellcheck SC2034 if shellcheck were run — but it is not installed, so no
   verification impact.)

No delta forced any change to S7's `deploy.sh` contract, so no escalation was warranted.

#!/usr/bin/env bash
set -Eeuo pipefail

# Runs ON the Oracle host (shipped + invoked by github-actions-production-deploy.sh). Refuses a dirty
# tracked worktree, fetches origin/main, and verifies the target SHA is an ancestor of fetched
# origin/main, then hands off to vocky's OWN deploy/deploy.sh — which owns the checkout + build +
# health-gate + rollback — and collects artifacts. This helper does NOT itself check out. Ported from
# hi2vi_web/deploy/oracle-production-deploy-remote.sh for the vocky checkout (/home/opc/vocky) and
# project (vocky, derived from the clone dir basename — deploy.sh's dc() pins no `-p`).

TARGET_SHA="${TARGET_SHA:-}"
REPO_PATH="${REPO_PATH:-/home/opc/vocky}"
REMOTE_ARTIFACT_DIR="${REMOTE_ARTIFACT_DIR:-/tmp/vocky-gha-artifacts}"
# Identity of this deploy, kept for documentation/parity with the sibling scripts. vocky's
# deploy/deploy.sh dc() runs `docker compose -f compose.prod.yml` with NO `-p` pin (project name =
# clone dir basename) and lets compose auto-read ./.env, so collect_status below mirrors dc() exactly
# and passes NEITHER -p NOR --env-file (it cd's to REPO_PATH first, where ./.env resolves).
PROJECT_NAME="${DEPLOY_PROJECT_NAME:-vocky}"
COMPOSE_ENV_FILE="${DEPLOY_ENV_FILE:-.env}"
COMPOSE_FILE="${DEPLOY_COMPOSE_FILE:-compose.prod.yml}"

SUMMARY_FILE=""

log() {
  printf '[oracle-production-deploy] %s\n' "$*"
}

die() {
  printf '[oracle-production-deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

append_summary() {
  if [ -n "${SUMMARY_FILE}" ]; then
    printf '%s\n' "$*" >> "${SUMMARY_FILE}"
  fi
}

run_capture() {
  local label="$1"
  shift
  log "+ $*"
  "$@" > "${REMOTE_ARTIFACT_DIR}/${label}.txt" 2>&1
}

collect_status() {
  docker compose -f "${COMPOSE_FILE}" ps \
    > "${REMOTE_ARTIFACT_DIR}/compose-ps.txt" 2>&1 || true
}

main() {
  [ -n "${TARGET_SHA}" ] || die "TARGET_SHA is required"
  [[ "${TARGET_SHA}" =~ ^[0-9a-fA-F]{40}$ ]] || die "TARGET_SHA must be a 40-character git SHA"
  [ -d "${REPO_PATH}/.git" ] || die "REPO_PATH is not a git checkout: ${REPO_PATH}"

  mkdir -p "${REMOTE_ARTIFACT_DIR}"
  SUMMARY_FILE="${REMOTE_ARTIFACT_DIR}/summary.md"
  : > "${SUMMARY_FILE}"

  cd "${REPO_PATH}"

  append_summary "# vocky Production Deploy Artifact"
  append_summary ""
  append_summary "- Target SHA: \`${TARGET_SHA}\`"
  append_summary "- Repo path: \`${REPO_PATH}\`"
  append_summary "- Started at: \`$(date -u '+%Y-%m-%dT%H:%M:%SZ')\`"

  run_capture "git-before" git status --short --branch

  if ! git diff --quiet || ! git diff --cached --quiet; then
    git status --short > "${REMOTE_ARTIFACT_DIR}/dirty-tracked-worktree.txt" 2>&1 || true
    append_summary "- Result: failed before deploy because tracked changes were present."
    die "tracked production checkout has local changes; refusing to deploy"
  fi

  log "Fetching origin main."
  if ! git fetch --prune origin main > "${REMOTE_ARTIFACT_DIR}/git-fetch.txt" 2>&1; then
    append_summary "- Result: failed while fetching \`origin/main\`."
    cat "${REMOTE_ARTIFACT_DIR}/git-fetch.txt" >&2 || true
    die "failed to fetch origin/main"
  fi
  fetched_main_sha="$(git rev-parse --verify "FETCH_HEAD^{commit}" 2>/dev/null)" || die "FETCH_HEAD is not a valid commit after fetching origin main"
  git cat-file -e "${TARGET_SHA}^{commit}" 2>/dev/null || die "target commit is not available after fetching origin main"
  git merge-base --is-ancestor "${TARGET_SHA}" "${fetched_main_sha}" || die "target commit is not reachable from fetched origin main"

  log "Running deploy/deploy.sh (vocky's deploy.sh owns checkout + build + health-gate + rollback)."
  set +e
  deploy/deploy.sh "${TARGET_SHA}" > >(tee "${REMOTE_ARTIFACT_DIR}/deploy-output.txt") \
    2> >(tee "${REMOTE_ARTIFACT_DIR}/deploy-error.txt" >&2)
  local deploy_status=$?
  set -e

  collect_status

  append_summary "- Finished at: \`$(date -u '+%Y-%m-%dT%H:%M:%SZ')\`"
  if [ "${deploy_status}" -ne 0 ]; then
    append_summary "- Result: deploy failed with status \`${deploy_status}\`."
    exit "${deploy_status}"
  fi

  append_summary "- Result: deploy completed successfully."
  log "Deploy completed successfully."
}

main "$@"

#!/usr/bin/env bash
set -Eeuo pipefail

# Runs on the GitHub Actions runner: SSH to the shared Oracle host and execute vocky's OWN remote
# deploy helper against its OWN checkout (/home/opc/vocky) and Compose project (vocky). Ported from
# hi2vi_web/deploy/github-actions-production-deploy.sh; never touches the sibling co-tenants'
# checkouts or projects (hi2vi, knowledge, changple).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REMOTE_SCRIPT_SOURCE="${SCRIPT_DIR}/oracle-production-deploy-remote.sh"

TARGET_SHA="${TARGET_SHA:-${GITHUB_SHA:-}}"
ORACLE_SSH_HOST="${ORACLE_SSH_HOST:-140.245.64.173}"
ORACLE_SSH_USER="${ORACLE_SSH_USER:-opc}"
ORACLE_SSH_PORT="${ORACLE_SSH_PORT:-22}"
ORACLE_REPO_PATH="${ORACLE_REPO_PATH:-/home/opc/vocky}"
ORACLE_SSH_PRIVATE_KEY="${ORACLE_SSH_PRIVATE_KEY:-}"
ORACLE_SSH_KNOWN_HOSTS="${ORACLE_SSH_KNOWN_HOSTS:-}"
ORACLE_SSH_PASSPHRASE="${ORACLE_SSH_PASSPHRASE:-}"
ARTIFACT_DIR="${ARTIFACT_DIR:-production-deploy-artifacts}"
RUN_ID="${GITHUB_RUN_ID:-manual}"

TMP_DIR=""
SSH_AGENT_STARTED=0

log() {
  printf '[vocky-deploy] %s\n' "$*"
}

die() {
  printf '[vocky-deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

require_env() {
  local name="$1"
  local value="${!name:-}"
  if [ -z "${value}" ]; then
    die "required environment variable is missing: ${name}"
  fi
}

shell_quote() {
  printf '%q' "$1"
}

cleanup() {
  if [ "${SSH_AGENT_STARTED}" -eq 1 ]; then
    ssh-agent -k >/dev/null 2>&1 || true
  fi
  if [ -n "${TMP_DIR}" ]; then
    rm -rf "${TMP_DIR}"
  fi
}

validate_inputs() {
  require_env TARGET_SHA
  require_env ORACLE_SSH_HOST
  require_env ORACLE_SSH_USER
  require_env ORACLE_REPO_PATH
  require_env ORACLE_SSH_PRIVATE_KEY
  require_env ORACLE_SSH_KNOWN_HOSTS

  [[ "${TARGET_SHA}" =~ ^[0-9a-fA-F]{40}$ ]] || die "TARGET_SHA must be a 40-character git SHA"
  [[ "${ORACLE_SSH_PORT}" =~ ^[0-9]+$ ]] || die "ORACLE_SSH_PORT must be numeric"
  [ -f "${REMOTE_SCRIPT_SOURCE}" ] || die "remote deploy helper not found: ${REMOTE_SCRIPT_SOURCE}"
}

prepare_ssh() {
  TMP_DIR="$(mktemp -d)"
  local key_file="${TMP_DIR}/oracle_deploy_key"
  local known_hosts_file="${TMP_DIR}/known_hosts"

  umask 077
  printf '%s\n' "${ORACLE_SSH_PRIVATE_KEY}" > "${key_file}"
  printf '%s\n' "${ORACLE_SSH_KNOWN_HOSTS}" > "${known_hosts_file}"

  SSH_COMMON=(
    -o BatchMode=yes
    -o StrictHostKeyChecking=yes
    -o UserKnownHostsFile="${known_hosts_file}"
    -o IdentitiesOnly=yes
  )

  if [ -n "${ORACLE_SSH_PASSPHRASE}" ]; then
    local askpass="${TMP_DIR}/askpass.sh"
    cat > "${askpass}" <<'ASKPASS'
#!/usr/bin/env bash
printf '%s\n' "${ORACLE_SSH_PASSPHRASE}"
ASKPASS
    chmod 700 "${askpass}"
    eval "$(ssh-agent -s)" >/dev/null
    SSH_AGENT_STARTED=1
    DISPLAY=none SSH_ASKPASS="${askpass}" SSH_ASKPASS_REQUIRE=force ssh-add "${key_file}" </dev/null >/dev/null
  fi

  SSH_COMMON+=(-i "${key_file}")

  SSH_CMD=(ssh "${SSH_COMMON[@]}" -p "${ORACLE_SSH_PORT}")
  SCP_CMD=(scp "${SSH_COMMON[@]}" -P "${ORACLE_SSH_PORT}")
}

collect_remote_artifacts() {
  local remote="$1"
  local remote_artifact_dir="$2"

  mkdir -p "${REPO_ROOT}/${ARTIFACT_DIR}"
  set +e
  "${SCP_CMD[@]}" -r "${remote}:${remote_artifact_dir}/." "${REPO_ROOT}/${ARTIFACT_DIR}/"
  local scp_status=$?
  set -e
  if [ "${scp_status}" -ne 0 ]; then
    log "Remote artifact collection failed; continuing so deploy status is preserved."
  fi
}

main() {
  validate_inputs
  trap cleanup EXIT
  prepare_ssh

  local remote="${ORACLE_SSH_USER}@${ORACLE_SSH_HOST}"
  local sha_short="${TARGET_SHA:0:12}"
  local remote_script="/tmp/vocky-gha-deploy-${RUN_ID}-${sha_short}.sh"
  local remote_artifact_dir="/tmp/vocky-gha-artifacts-${RUN_ID}-${sha_short}"

  log "Deploying ${sha_short} to ${ORACLE_SSH_HOST}:${ORACLE_REPO_PATH}"

  "${SCP_CMD[@]}" "${REMOTE_SCRIPT_SOURCE}" "${remote}:${remote_script}"
  "${SSH_CMD[@]}" "${remote}" "chmod 700 $(shell_quote "${remote_script}") && rm -rf $(shell_quote "${remote_artifact_dir}") && mkdir -p $(shell_quote "${remote_artifact_dir}")"

  local remote_command
  remote_command="TARGET_SHA=$(shell_quote "${TARGET_SHA}") REPO_PATH=$(shell_quote "${ORACLE_REPO_PATH}") REMOTE_ARTIFACT_DIR=$(shell_quote "${remote_artifact_dir}") bash $(shell_quote "${remote_script}")"

  set +e
  "${SSH_CMD[@]}" "${remote}" "${remote_command}"
  local deploy_status=$?
  set -e

  collect_remote_artifacts "${remote}" "${remote_artifact_dir}"
  "${SSH_CMD[@]}" "${remote}" "rm -f $(shell_quote "${remote_script}") && rm -rf $(shell_quote "${remote_artifact_dir}")" || true

  if [ "${deploy_status}" -ne 0 ]; then
    die "remote deploy failed with status ${deploy_status}"
  fi

  log "Remote deploy completed successfully."
}

main "$@"

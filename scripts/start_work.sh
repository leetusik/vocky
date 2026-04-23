#!/bin/sh
set -eu

usage() {
  printf 'Usage: %s <phase_id> <slice_id> <slug>\n' "$0" >&2
  exit 1
}

[ $# -eq 3 ] || usage

validate_id() {
  label=$1
  value=$2

  case "$value" in
    ''|*[!A-Za-z0-9._-]*)
      printf 'Error: %s must contain only letters, digits, dot, underscore, or hyphen.\n' "$label" >&2
      exit 1
      ;;
  esac
}

phase_id=$1
slice_id=$2
raw_slug=$3

validate_id "phase_id" "$phase_id"
validate_id "slice_id" "$slice_id"

slug=$(printf '%s' "$raw_slug" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9._-' '_' | sed 's/^_*//; s/_*$//')

if [ -z "$slug" ]; then
  printf 'Error: slug must contain at least one valid character.\n' >&2
  exit 1
fi

plan_template='works/templates/plan.md'
result_template='works/templates/result.md'

[ -f "$plan_template" ] || {
  printf 'Error: missing template %s\n' "$plan_template" >&2
  exit 1
}

[ -f "$result_template" ] || {
  printf 'Error: missing template %s\n' "$result_template" >&2
  exit 1
}

mkdir -p works/current

timestamp=$(date '+%Y%m%d_%H%M')
work_dir="works/current/${timestamp}_${slug}"

[ ! -e "$work_dir" ] || {
  printf 'Error: work item already exists at %s\n' "$work_dir" >&2
  exit 1
}

mkdir "$work_dir"

sed \
  -e "s|__WORK_ITEM__|$work_dir|g" \
  -e "s|__CREATED_AT__|$timestamp|g" \
  -e "s|__PHASE_ID__|$phase_id|g" \
  -e "s|__SLICE_ID__|$slice_id|g" \
  "$plan_template" > "$work_dir/plan.md"

sed \
  -e "s|__WORK_ITEM__|$work_dir|g" \
  -e "s|__CREATED_AT__|$timestamp|g" \
  -e "s|__PHASE_ID__|$phase_id|g" \
  -e "s|__SLICE_ID__|$slice_id|g" \
  "$result_template" > "$work_dir/result.md"

printf '%s\n' "$work_dir"

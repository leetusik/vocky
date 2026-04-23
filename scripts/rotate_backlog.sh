#!/bin/sh
set -eu

if [ $# -ne 0 ]; then
  printf 'Usage: %s\n' "$0" >&2
  exit 1
fi

template='works/templates/backlog.md'
current='works/backlog.md'
archive_dir='works/archives/backlogs'

[ -f "$template" ] || {
  printf 'Error: missing template %s\n' "$template" >&2
  exit 1
}

[ -f "$current" ] || {
  printf 'Error: backlog not found at %s\n' "$current" >&2
  exit 1
}

mkdir -p "$archive_dir"

timestamp=$(date '+%Y%m%d_%H%M')
archive="$archive_dir/${timestamp}_backlog.md"

[ ! -e "$archive" ] || {
  printf 'Error: archive path already exists at %s\n' "$archive" >&2
  exit 1
}

mv "$current" "$archive"
cp "$template" "$current"

printf 'archived: %s\n' "$archive"
printf 'fresh: %s\n' "$current"

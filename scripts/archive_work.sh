#!/bin/sh
set -eu

usage() {
  printf 'Usage: %s <work_dir_name>\n' "$0" >&2
  exit 1
}

[ $# -eq 1 ] || usage

case "$1" in
  */*)
    printf 'Error: pass a work directory name, not a path.\n' >&2
    exit 1
    ;;
esac

name=$1
src="works/current/$name"
dst="works/archives/work_items/$name"

[ -d "$src" ] || {
  printf 'Error: work item not found at %s\n' "$src" >&2
  exit 1
}

mkdir -p works/archives/work_items

[ ! -e "$dst" ] || {
  printf 'Error: archive destination already exists at %s\n' "$dst" >&2
  exit 1
}

mv "$src" "$dst"

printf '%s\n' "$dst"

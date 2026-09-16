#!/bin/sh
set -eu

artifact_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target=${1:-"$artifact_dir/MODIFIED_FILE.md"}

cp "$artifact_dir/ORIGINAL.md" "$target"
printf 'restored=%s\n' "$target"

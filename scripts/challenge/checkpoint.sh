#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "usage: $0 <checkpoint_name> [challenge_dir]" >&2
    exit 1
fi

checkpoint_name="$1"
target_dir="${2:-.}"

command -v git >/dev/null 2>&1 || {
    echo "git not found; cannot create checkpoint" >&2
    exit 1
}

git -C "${target_dir}" init -q
if ! git -C "${target_dir}" config user.name >/dev/null 2>&1; then
    git -C "${target_dir}" config user.name "Amadeus"
fi
if ! git -C "${target_dir}" config user.email >/dev/null 2>&1; then
    git -C "${target_dir}" config user.email "amadeus@local"
fi

git -C "${target_dir}" add -A
if git -C "${target_dir}" diff --cached --quiet; then
    echo "no git changes for checkpoint ${checkpoint_name}"
    exit 0
fi

if git -C "${target_dir}" rev-parse --verify HEAD >/dev/null 2>&1; then
    commit_count="$(git -C "${target_dir}" rev-list --count HEAD)"
else
    commit_count=0
fi

git -C "${target_dir}" commit -m "[ckpt${commit_count} ${checkpoint_name}]" >/dev/null
commit_hash="$(git -C "${target_dir}" rev-parse --short HEAD)"
echo "created git checkpoint [ckpt${commit_count} ${checkpoint_name}] ${commit_hash}"

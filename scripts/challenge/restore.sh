#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "usage: $0 <checkpoint_commit|latest> [challenge_dir]" >&2
    exit 1
fi

checkpoint_ref="$1"
target_dir="${2:-.}"

command -v git >/dev/null 2>&1 || {
    echo "git not found; cannot restore checkpoint" >&2
    exit 1
}

if ! git -C "${target_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "not a git checkpoint directory: ${target_dir}" >&2
    exit 1
fi

if [ "${checkpoint_ref}" = "latest" ]; then
    checkpoint_ref="HEAD"
fi

commit_hash="$(git -C "${target_dir}" rev-parse --verify "${checkpoint_ref}^{commit}" 2>/dev/null)" || {
    echo "checkpoint commit not found: ${checkpoint_ref}" >&2
    exit 1
}

git -C "${target_dir}" restore --source="${commit_hash}" --staged --worktree .
echo "restored tracked files from git checkpoint $(git -C "${target_dir}" rev-parse --short "${commit_hash}")"

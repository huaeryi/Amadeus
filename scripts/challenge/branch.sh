#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 3 ]; then
    echo "usage: $0 <branch_name> [checkpoint_ref] [challenge_dir]" >&2
    echo "       $0 <branch_name> [challenge_dir]" >&2
    exit 1
fi

branch_name="$1"
checkpoint_ref="HEAD"
target_dir="."

if [ $# -eq 2 ]; then
    if [ -d "$2/.git" ] && git -C "$2" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        target_dir="$2"
    else
        checkpoint_ref="$2"
    fi
elif [ $# -eq 3 ]; then
    checkpoint_ref="$2"
    target_dir="$3"
fi

command -v git >/dev/null 2>&1 || {
    echo "git not found; cannot create checkpoint branch" >&2
    exit 1
}

if ! git -C "${target_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "not a git checkpoint directory: ${target_dir}" >&2
    exit 1
fi

if ! git -C "${target_dir}" rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "no checkpoint commits found in: ${target_dir}" >&2
    exit 1
fi

if ! git -C "${target_dir}" check-ref-format --branch "${branch_name}" >/dev/null 2>&1; then
    echo "invalid branch name: ${branch_name}" >&2
    exit 1
fi

if git -C "${target_dir}" show-ref --verify --quiet "refs/heads/${branch_name}"; then
    echo "branch already exists: ${branch_name}" >&2
    exit 1
fi

if [ -n "$(git -C "${target_dir}" status --porcelain)" ]; then
    echo "working tree has uncommitted changes; create a checkpoint or clean the tree before branching" >&2
    exit 1
fi

commit_hash="$(git -C "${target_dir}" rev-parse --verify "${checkpoint_ref}^{commit}" 2>/dev/null)" || {
    echo "checkpoint commit not found: ${checkpoint_ref}" >&2
    exit 1
}

git -C "${target_dir}" switch -q -c "${branch_name}" "${commit_hash}"
short_hash="$(git -C "${target_dir}" rev-parse --short HEAD)"
echo "created checkpoint branch ${branch_name} at ${short_hash}"

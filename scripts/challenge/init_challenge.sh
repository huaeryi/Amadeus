#!/usr/bin/env bash
set -euo pipefail

if [ $# -gt 1 ]; then
    echo "usage: $0 [challenge_dir]" >&2
    exit 1
fi

target_dir="${1:-.}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(cd "${script_dir}/../.." && pwd)"
state_dir="${target_dir}/amds_state"

mkdir -p "${target_dir}"
mkdir -p "${state_dir}/evidence"

git_commit_if_needed() {
    local commit_name="$1"

    command -v git >/dev/null 2>&1 || {
        echo "git not found; skipped initial checkpoint commit" >&2
        return 0
    }

    git -C "${target_dir}" init -q
    if ! git -C "${target_dir}" config user.name >/dev/null 2>&1; then
        git -C "${target_dir}" config user.name "Amadeus"
    fi
    if ! git -C "${target_dir}" config user.email >/dev/null 2>&1; then
        git -C "${target_dir}" config user.email "amadeus@local"
    fi

    if git -C "${target_dir}" rev-parse --verify HEAD >/dev/null 2>&1; then
        return 0
    fi

    git -C "${target_dir}" add -A
    if git -C "${target_dir}" diff --cached --quiet; then
        echo "no files to commit for initial checkpoint"
        return 0
    fi

    git -C "${target_dir}" commit -m "[ckpt0 ${commit_name}]" >/dev/null
    echo "created git checkpoint [ckpt0 ${commit_name}]"
}

for name in run.env cognition.json exp_example.py; do
    src="${root_dir}/templates/${name}"
    dst="${state_dir}/${name}"
    if [ ! -e "${dst}" ]; then
        cp "${src}" "${dst}"
        echo "created ${dst}"
    fi
done

python3 "${root_dir}/scripts/state/state_docs.py" init "${target_dir}" >/dev/null
echo "initialized ${state_dir}/cognition.json"
echo "rendered ${state_dir}/COGNITION.md"

if [ -f "${target_dir}/exp_template.py" ] && [ ! -e "${target_dir}/exp.py" ]; then
    cp "${target_dir}/exp_template.py" "${target_dir}/exp.py"
    echo "created ${target_dir}/exp.py from exp_template.py"
fi

challenge_name="$(basename "$(cd "${target_dir}" && pwd)")"
git_commit_if_needed "${challenge_name}"

echo "initialized ${target_dir}"

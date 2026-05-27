#!/usr/bin/env bash
set -euo pipefail

if [ $# -gt 1 ]; then
    echo "usage: $0 [challenge_dir]" >&2
    exit 1
fi

target_dir="${1:-.}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(cd "${script_dir}/.." && pwd)"

mkdir -p "${target_dir}"

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

for name in .ctf-files .pwnrun metadata.json capabilities.json facts.json state.json; do
    src="${root_dir}/templates/${name}"
    dst="${target_dir}/${name}"
    if [ ! -e "${dst}" ]; then
        cp "${src}" "${dst}"
        echo "created ${dst}"
    fi
done

ctf_files="${target_dir}/.ctf-files"
if [ -f "${ctf_files}" ]; then
    for name in metadata.json facts.json state.json STATE.md FACTS.md capabilities.json CAPABILITIES.md .pwnrun; do
        if ! grep -Fxq "${name}" "${ctf_files}"; then
            printf '%s\n' "${name}" >> "${ctf_files}"
            echo "tracked ${name} in ${ctf_files}"
        fi
    done
fi

python3 "${root_dir}/bin/state_docs.py" init "${target_dir}" >/dev/null
echo "initialized ${target_dir}/facts.json"
echo "initialized ${target_dir}/state.json"
echo "rendered ${target_dir}/FACTS.md"
echo "rendered ${target_dir}/STATE.md"

if [ -f "${target_dir}/exp_template.py" ] && [ ! -e "${target_dir}/exp.py" ]; then
    cp "${target_dir}/exp_template.py" "${target_dir}/exp.py"
    echo "created ${target_dir}/exp.py from exp_template.py"
fi

python3 "${root_dir}/bin/capabilities.py" init "${target_dir}" >/dev/null
echo "initialized ${target_dir}/capabilities.json"
echo "rendered ${target_dir}/CAPABILITIES.md"

challenge_name="$(basename "$(cd "${target_dir}" && pwd)")"
git_commit_if_needed "${challenge_name}"

echo "initialized ${target_dir}"

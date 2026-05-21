#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "usage: $0 <checkpoint_name|latest> [challenge_dir]" >&2
    exit 1
fi

checkpoint_name="$1"
target_dir="${2:-.}"
checkpoint_dir="${target_dir}/checkpoints/${checkpoint_name}"
head_file="${target_dir}/checkpoints/.amadeus-head"

if [ "${checkpoint_name}" = "latest" ]; then
    checkpoint_dir="${target_dir}/checkpoints/latest"
fi

if [ ! -e "${checkpoint_dir}" ]; then
    echo "checkpoint not found: ${checkpoint_name}" >&2
    exit 1
fi

resolved_dir="$(cd "${checkpoint_dir}" && pwd)"
manifest="${resolved_dir}/.ctf-files"
files_dir="${resolved_dir}/files"

if [ ! -f "${manifest}" ]; then
    echo "missing manifest in ${resolved_dir}" >&2
    exit 1
fi

while IFS= read -r path || [ -n "${path}" ]; do
    case "${path}" in
        ""|\#*)
            continue
            ;;
    esac

    src="${files_dir}/${path}"
    dst="${target_dir}/${path}"

    if [ ! -e "${src}" ]; then
        continue
    fi

    if [ -d "${src}" ]; then
        echo "skip directory path in checkpoint manifest: ${path}" >&2
        continue
    fi

    mkdir -p "$(dirname "${dst}")"
    cp -a "${src}" "${dst}"
done < "${manifest}"

printf '%s\n' "$(basename "${resolved_dir}")" > "${head_file}"
echo "restored ${checkpoint_name} into ${target_dir}"

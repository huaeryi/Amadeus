#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "usage: $0 <checkpoint_name> [challenge_dir]" >&2
    exit 1
fi

checkpoint_name="$1"
target_dir="${2:-.}"
manifest="${target_dir}/.ctf-files"

if [ ! -f "${manifest}" ]; then
    echo "missing ${manifest}; run init_challenge.sh first" >&2
    exit 1
fi

slug="$(printf '%s' "${checkpoint_name}" | tr ' /' '--' | tr -cd 'A-Za-z0-9._-')"
timestamp="$(date +%Y%m%d-%H%M%S)"
checkpoint_id="${timestamp}-${slug}"
checkpoint_dir="${target_dir}/checkpoints/${checkpoint_id}"
files_dir="${checkpoint_dir}/files"

mkdir -p "${files_dir}"
cp "${manifest}" "${checkpoint_dir}/.ctf-files"

while IFS= read -r path || [ -n "${path}" ]; do
    case "${path}" in
        ""|\#*)
            continue
            ;;
    esac

    src="${target_dir}/${path}"
    dst="${files_dir}/${path}"

    if [ ! -e "${src}" ]; then
        continue
    fi

    if [ -d "${src}" ]; then
        echo "skip directory path in manifest: ${path}" >&2
        continue
    fi

    mkdir -p "$(dirname "${dst}")"
    cp -a "${src}" "${dst}"
done < "${manifest}"

cat > "${checkpoint_dir}/META.txt" <<EOF
checkpoint_id=${checkpoint_id}
name=${checkpoint_name}
created_at=$(date -Is)
target_dir=${target_dir}
EOF

ln -sfn "${checkpoint_id}" "${target_dir}/checkpoints/latest"

echo "created checkpoint ${checkpoint_id}"

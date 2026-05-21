#!/usr/bin/env bash
set -euo pipefail

if [ $# -gt 1 ]; then
    echo "usage: $0 [challenge_dir]" >&2
    exit 1
fi

target_dir="${1:-.}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(cd "${script_dir}/.." && pwd)"

mkdir -p "${target_dir}/checkpoints" "${target_dir}/attempts"
touch "${target_dir}/checkpoints/.amadeus-head"
if [ ! -e "${target_dir}/checkpoints/.checkpoint-graph.json" ]; then
    cat > "${target_dir}/checkpoints/.checkpoint-graph.json" <<'EOF'
{
  "nodes": [],
  "edges": []
}
EOF
fi

for name in STATE.md FACTS.md .ctf-files .pwnrun; do
    src="${root_dir}/templates/${name}"
    dst="${target_dir}/${name}"
    if [ ! -e "${dst}" ]; then
        cp "${src}" "${dst}"
        echo "created ${dst}"
    fi
done

if [ -f "${target_dir}/exp_template.py" ] && [ ! -e "${target_dir}/exp.py" ]; then
    cp "${target_dir}/exp_template.py" "${target_dir}/exp.py"
    echo "created ${target_dir}/exp.py from exp_template.py"
fi

echo "initialized ${target_dir}"

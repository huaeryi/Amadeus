#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "usage: $0 <checkpoint_name> [challenge_dir]" >&2
    exit 1
fi

checkpoint_name="$1"
target_dir="${2:-.}"
manifest="${target_dir}/.ctf-files"
head_file="${target_dir}/checkpoints/.amadeus-head"
graph_file="${target_dir}/checkpoints/.checkpoint-graph.json"

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

parent_checkpoint=""
if [ -f "${head_file}" ]; then
    parent_checkpoint="$(tr -d '\n' < "${head_file}")"
fi

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
parent_checkpoint=${parent_checkpoint}
EOF

printf '%s\n' "${checkpoint_id}" > "${head_file}"
ln -sfn "${checkpoint_id}" "${target_dir}/checkpoints/latest"

python3 - "$graph_file" "$checkpoint_id" "$checkpoint_name" "$parent_checkpoint" "$target_dir" <<'PY'
import json
import os
import sys
from datetime import datetime
from pathlib import Path

graph_path = Path(sys.argv[1])
checkpoint_id = sys.argv[2]
checkpoint_name = sys.argv[3]
parent_checkpoint = sys.argv[4]
target_dir = sys.argv[5]

graph = {"nodes": [], "edges": []}
if graph_path.exists():
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except Exception:
        graph = {"nodes": [], "edges": []}

graph.setdefault("nodes", [])
graph.setdefault("edges", [])
graph["nodes"] = [node for node in graph["nodes"] if node.get("id") != checkpoint_id]
graph["nodes"].append(
    {
        "id": checkpoint_id,
        "name": checkpoint_name,
        "parent_id": parent_checkpoint or None,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "target_dir": target_dir,
    }
)
graph["edges"] = [edge for edge in graph["edges"] if edge.get("child") != checkpoint_id]
if parent_checkpoint:
    graph["edges"].append({"parent": parent_checkpoint, "child": checkpoint_id})

graph_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

echo "created checkpoint ${checkpoint_id}"

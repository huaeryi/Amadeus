#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
usage: run_pwn.sh <challenge_dir> [local|remote|patched|info] [host] [port] [-- extra exp args]

examples:
  run_pwn.sh challenges/fsb
  run_pwn.sh challenges/fsb local
  run_pwn.sh challenges/fsb remote 127.0.0.1 5000
  run_pwn.sh challenges/fsb patched
  run_pwn.sh challenges/fsb info

behavior:
  - reads optional amds_state/.pwnrun, falling back to legacy .pwnrun
  - exports normalized PWN_* environment variables
  - runs exp.py when present
  - falls back to direct binary execution when exp.py is absent
EOF
}

die() {
    echo "run_pwn.sh: $*" >&2
    exit 1
}

abspath() {
    local path="$1"
    if [ -z "$path" ]; then
        return 0
    fi

    if [ "${path#/}" != "$path" ]; then
        printf '%s\n' "$path"
    else
        printf '%s\n' "$(cd "$challenge_dir" && realpath "$path")"
    fi
}

read_words() {
    local value="${1:-}"
    local -n out_ref="$2"
    out_ref=()
    if [ -n "$value" ]; then
        # shellcheck disable=SC2206
        out_ref=($value)
    fi
}

detect_patched_binary() {
    find "$challenge_dir" -maxdepth 1 -type f \
        ! -name '*.py' \
        ! -name '*.md' \
        ! -name '*.txt' \
        ! -name '*.log' \
        ! -name '*.zip' \
        ! -name '*.tar*' \
        ! -name '*.i64' \
        ! -name '*.id*' \
        ! -name '*.so*' \
        ! -name 'ld-*' \
        ! -name 'libc*' \
        ! -name '.*' \
        -iname '*patched*' \
        | sort | head -n 1
}

detect_main_binary() {
    local result
    result="$(find "$challenge_dir" -maxdepth 1 -type f -executable \
        ! -name '*.py' \
        ! -name '*.md' \
        ! -name '*.txt' \
        ! -name '*.log' \
        ! -name '*.zip' \
        ! -name '*.tar*' \
        ! -name '*.i64' \
        ! -name '*.id*' \
        ! -name '*.so*' \
        ! -name 'ld-*' \
        ! -name 'libc*' \
        ! -iname '*patched*' \
        ! -name '.*' \
        ! -name 'flag*' \
        | sort | head -n 1)"

    if [ -n "$result" ]; then
        printf '%s\n' "$result"
        return
    fi

    result="$(find "$challenge_dir" -maxdepth 1 -type f \
        ! -name '*.py' \
        ! -name '*.md' \
        ! -name '*.txt' \
        ! -name '*.log' \
        ! -name '*.zip' \
        ! -name '*.tar*' \
        ! -name '*.i64' \
        ! -name '*.id*' \
        ! -name '*.so*' \
        ! -name 'ld-*' \
        ! -name 'libc*' \
        ! -iname '*patched*' \
        ! -name '.*' \
        ! -name 'flag*' \
        | sort | head -n 1)"

    printf '%s\n' "$result"
}

detect_libc() {
    local result
    result="$(find "$challenge_dir" -maxdepth 1 -type f \
        \( -name 'libc*.so*' -o -name 'libc*.so' -o -name 'libc*.musl*' -o -name 'libc.so*' \) \
        | sort | head -n 1)"
    printf '%s\n' "$result"
}

detect_ld() {
    local result
    result="$(find "$challenge_dir" -maxdepth 1 -type f \
        \( -name 'ld-*.so*' -o -name 'ld-linux*.so*' -o -name 'ld.so*' \) \
        | sort | head -n 1)"
    printf '%s\n' "$result"
}

direct_run_cmd() {
    if [ -n "$active_bin" ] && [ -n "$ld_path" ]; then
        if [ -n "$libc_path" ]; then
            printf '%q ' "$ld_path" --library-path "$(dirname "$libc_path")" "$active_bin"
        else
            printf '%q ' "$ld_path" "$active_bin"
        fi
        return
    fi

    if [ -n "$active_bin" ] && [ -n "$libc_path" ]; then
        printf '%q ' env "LD_PRELOAD=$libc_path" "$active_bin"
        return
    fi

    if [ -n "$active_bin" ]; then
        printf '%q ' "$active_bin"
    fi
}

if [ $# -lt 1 ]; then
    usage
    exit 1
fi

challenge_dir="$1"
shift

mode="local"
if [ $# -gt 0 ]; then
    case "$1" in
        local|remote|patched|info)
            mode="$1"
            shift
            ;;
    esac
fi

host=""
port=""
if [ "$mode" = "remote" ]; then
    if [ $# -gt 0 ] && [ "$1" != "--" ]; then
        host="$1"
        shift
    fi
    if [ $# -gt 0 ] && [ "$1" != "--" ]; then
        port="$1"
        shift
    fi
fi

if [ $# -gt 0 ] && [ "$1" = "--" ]; then
    shift
fi

extra_args=("$@")

challenge_dir="$(realpath "$challenge_dir")"
[ -d "$challenge_dir" ] || die "challenge directory not found: $challenge_dir"

config_path="$challenge_dir/amds_state/.pwnrun"
if [ ! -f "$config_path" ] && [ -f "$challenge_dir/.pwnrun" ]; then
    config_path="$challenge_dir/.pwnrun"
fi
if [ -f "$config_path" ]; then
    # shellcheck disable=SC1090
    source "$config_path"
fi

EXP_PYTHON="${EXP_PYTHON:-python3}"
EXP="${EXP:-exp.py}"
LOCAL_ARGS="${LOCAL_ARGS:-}"
REMOTE_ARGS="${REMOTE_ARGS:-r}"
REMOTE_APPEND_HOSTPORT="${REMOTE_APPEND_HOSTPORT:-1}"

bin_path="${BIN:-}"
patched_bin_path="${PATCHED_BIN:-}"
libc_path="${LIBC:-}"
ld_path="${LD:-}"

if [ -z "$bin_path" ]; then
    bin_path="$(detect_main_binary)"
fi
if [ -z "$patched_bin_path" ]; then
    patched_bin_path="$(detect_patched_binary)"
fi
if [ -z "$libc_path" ]; then
    libc_path="$(detect_libc)"
fi
if [ -z "$ld_path" ]; then
    ld_path="$(detect_ld)"
fi

bin_path="$(abspath "$bin_path")"
patched_bin_path="$(abspath "$patched_bin_path")"
libc_path="$(abspath "$libc_path")"
ld_path="$(abspath "$ld_path")"

exp_path="$(abspath "$EXP")"
if [ ! -f "$exp_path" ]; then
    exp_path=""
fi

if [ "$mode" = "remote" ]; then
    host="${host:-${HOST:-}}"
    port="${port:-${PORT:-}}"

    if [ "$REMOTE_APPEND_HOSTPORT" = "1" ]; then
        [ -n "$host" ] || die "remote host missing; pass it on the command line or set HOST in amds_state/.pwnrun"
        [ -n "$port" ] || die "remote port missing; pass it on the command line or set PORT in amds_state/.pwnrun"
    fi
fi

active_bin="$bin_path"
if [ "$mode" = "patched" ] && [ -n "$patched_bin_path" ]; then
    active_bin="$patched_bin_path"
fi

export PWN_MODE="$mode"
export PWN_CHAL_DIR="$challenge_dir"
export PWN_EXP="${exp_path:-}"
export PWN_BIN="${bin_path:-}"
export PWN_PATCHED_BIN="${patched_bin_path:-}"
export PWN_ACTIVE_BIN="${active_bin:-}"
export PWN_LIBC="${libc_path:-}"
export PWN_LD="${ld_path:-}"
export PWN_HOST="${host:-}"
export PWN_PORT="${port:-}"
export PWN_LOCAL_ARGS="${LOCAL_ARGS:-}"
export PWN_REMOTE_ARGS="${REMOTE_ARGS:-}"

if [ -n "$libc_path" ]; then
    export PWN_LIB_DIR="$(dirname "$libc_path")"
elif [ -n "$ld_path" ]; then
    export PWN_LIB_DIR="$(dirname "$ld_path")"
else
    export PWN_LIB_DIR=""
fi

if [ "$mode" = "info" ]; then
    cat <<EOF
challenge_dir=$challenge_dir
mode=$mode
exp=${exp_path:-}
bin=${bin_path:-}
patched_bin=${patched_bin_path:-}
active_bin=${active_bin:-}
libc=${libc_path:-}
ld=${ld_path:-}
host=${host:-}
port=${port:-}
local_args=${LOCAL_ARGS:-}
remote_args=${REMOTE_ARGS:-}
remote_append_hostport=$REMOTE_APPEND_HOSTPORT
direct_patched_run=$(direct_run_cmd)
EOF
    exit 0
fi

if [ -n "$exp_path" ]; then
    local_args_arr=()
    remote_args_arr=()
    read_words "$LOCAL_ARGS" local_args_arr
    read_words "$REMOTE_ARGS" remote_args_arr

    cmd=("$EXP_PYTHON" "$exp_path")
    if [ "$mode" = "remote" ]; then
        cmd+=("${remote_args_arr[@]}")
        if [ "$REMOTE_APPEND_HOSTPORT" = "1" ]; then
            cmd+=("$host" "$port")
        fi
    else
        cmd+=("${local_args_arr[@]}")
    fi
    cmd+=("${extra_args[@]}")

    echo "run_pwn.sh: mode=$mode exp=${exp_path#$challenge_dir/}" >&2
    (cd "$challenge_dir" && exec "${cmd[@]}")
    exit $?
fi

[ -n "$active_bin" ] || die "no exp.py and no binary detected in $challenge_dir"

echo "run_pwn.sh: mode=$mode direct_binary=${active_bin#$challenge_dir/}" >&2

if [ "$mode" = "remote" ]; then
    die "remote mode requires exp.py"
fi

if [ "$mode" = "patched" ] && [ -n "$ld_path" ]; then
    if [ -n "$libc_path" ]; then
        (cd "$challenge_dir" && exec "$ld_path" --library-path "$(dirname "$libc_path")" "$active_bin" "${extra_args[@]}")
    else
        (cd "$challenge_dir" && exec "$ld_path" "$active_bin" "${extra_args[@]}")
    fi
fi

if [ "$mode" = "patched" ] && [ -n "$libc_path" ]; then
    (cd "$challenge_dir" && exec env LD_PRELOAD="$libc_path" "$active_bin" "${extra_args[@]}")
fi

(cd "$challenge_dir" && exec "$active_bin" "${extra_args[@]}")

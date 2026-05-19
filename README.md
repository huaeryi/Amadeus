# Amadeus

Minimal file-based solve-state helpers for Codex-driven CTF work.

## Files

- `bin/init_challenge.sh`: create `STATE.md`, `FACTS.md`, `.ctf-files`, `checkpoints/`, and `attempts/`
- `bin/checkpoint.sh`: snapshot tracked files into a named checkpoint
- `bin/restore.sh`: restore tracked files from a checkpoint
- `bin/run_pwn.sh`: unified local / remote / patched execution entrypoint
- `templates/`: default templates copied into challenge directories

## Usage

```bash
bin/init_challenge.sh challenges/baby_tcache
bin/checkpoint.sh env-ok challenges/baby_tcache
bin/checkpoint.sh leak-confirmed challenges/baby_tcache
bin/restore.sh latest challenges/baby_tcache
bin/restore.sh 20260519-120000-leak-confirmed challenges/baby_tcache
bin/run_pwn.sh challenges/baby_tcache
bin/run_pwn.sh challenges/baby_tcache remote 127.0.0.1 5000
bin/run_pwn.sh challenges/baby_tcache patched
```

Add extra tracked files by editing `.ctf-files` inside the challenge directory.
Keep it to files, not directories.

## run_pwn.sh

`run_pwn.sh` gives one entrypoint for:

- local exploit runs
- remote exploit runs
- patched local runs

It reads optional `.pwnrun` per challenge and exports normalized `PWN_*` environment variables:

- `PWN_MODE`
- `PWN_CHAL_DIR`
- `PWN_BIN`
- `PWN_PATCHED_BIN`
- `PWN_ACTIVE_BIN`
- `PWN_LIBC`
- `PWN_LD`
- `PWN_HOST`
- `PWN_PORT`

For legacy exploits, the default behavior is compatible with the common pattern:

- local: `python3 exp.py`
- remote: `python3 exp.py r <host> <port>`

For new exploits, prefer reading `PWN_*` so that one script works cleanly across local, remote, and patched modes.

## libc policy

Prefer this order:

1. Use the challenge-provided `libc` and `ld` if they exist.
2. Reproduce locally with `patchelf`, the provided loader, or `run_pwn.sh patched`.
3. If libc is not provided, leak symbols first and then identify the remote libc from a database such as `libc.rip`.

Avoid silently using the host libc unless that choice is explicitly verified.

## ctf-pwn compatibility

This workflow is designed to sit next to the `ctf-pwn` skill, not replace it.

- `ctf-pwn` provides exploitation patterns and technique guidance.
- `Amadeus` provides local state files, rollback points, and a consistent output structure.

The intended pairing is:

1. Let Codex read `challenges/AGENTS.md`.
2. Let the pwn skill drive the exploit reasoning.
3. Use `STATE.md`, `FACTS.md`, `checkpoints/`, and `attempts/` to keep the local solve process recoverable.

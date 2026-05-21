# Amadeus

Amadeus is a lightweight CTF workspace for Codex-driven solving.

It gives you:

- file-based solve state for each challenge
- checkpoints and rollback for risky exploit branches
- a unified `run_pwn.sh` entrypoint for local, remote, and patched runs
- a small Web UI for challenge management on port `9999`

Amadeus is meant to work with Codex skills such as `ctf-pwn`, not replace them.

## Layout

- `bin/init_challenge.sh`: create `STATE.md`, `FACTS.md`, `.ctf-files`, `.pwnrun`, `checkpoints/`, and `attempts/`
- `bin/checkpoint.sh`: snapshot tracked files into a named checkpoint
- `bin/restore.sh`: restore tracked files from a checkpoint
- `bin/run_pwn.sh`: unified local / remote / patched execution entrypoint
- `templates/`: default files copied into challenge directories
- `challenges/`: challenge folders such as `challenges/baby_tcache`
- `webui/`: challenge management frontend and backend

## Quick Start

Initialize a challenge:

```bash
bin/init_challenge.sh challenges/baby_tcache
```

Run a local exploit:

```bash
bin/run_pwn.sh challenges/baby_tcache
```

Run against a remote service:

```bash
bin/run_pwn.sh challenges/baby_tcache remote 127.0.0.1 5000
```

Run with the patched binary / provided loader setup:

```bash
bin/run_pwn.sh challenges/baby_tcache patched
```

Create and restore checkpoints:

```bash
bin/checkpoint.sh env-ok challenges/baby_tcache
bin/checkpoint.sh leak-confirmed challenges/baby_tcache
bin/restore.sh latest challenges/baby_tcache
bin/restore.sh 20260519-120000-leak-confirmed challenges/baby_tcache
```

## Pwn Workflow

When solving a pwn challenge under `challenges/`, read these first:

1. `AGENTS.md`
2. `challenges/AGENTS.md`

The intended loop is:

1. Initialize the challenge if `STATE.md` and `FACTS.md` do not exist yet.
2. Inspect the binary, patched binary, `libc`, `ld`, and `exp_template.py` if present.
3. Record confirmed facts in `FACTS.md`.
4. Record current stage, primitive, next step, checkpoint plan, rejected branches, and open questions in `STATE.md`.
5. Use `bin/run_pwn.sh <challenge_dir> [local|remote|patched]` as the standard entrypoint.
6. Checkpoint only after a real milestone such as `primitive-confirmed` or `libc-base-confirmed`.
7. Produce `exp.py` and `wp.md` as final outputs.

Add extra tracked files by editing `.ctf-files` inside the challenge directory.
Keep it to files, not directories.

## Checkpoint Strategy

Use checkpoints as rollback anchors, not autosaves.

- Simple stack or format-string challenge: usually 3 to 4 checkpoints.
- Medium stack, format-string, or heap challenge: usually 4 to 6 checkpoints.
- Complex heap, seccomp, sandbox, or kernel challenge: usually 5 to 8 checkpoints.

Name checkpoints after confirmed facts or working capabilities:

- `env-ok`
- `primitive-confirmed`
- `offset-confirmed`
- `pie-leaked`
- `canary-leaked`
- `libc-base-confirmed`
- `arb-read-confirmed`
- `arb-write-confirmed`
- `rop-ready`
- `setcontext-ready`
- `fsop-ready`
- `orw-working`
- `flag-confirmed`

Recommended cadence by challenge type:

- stack: `env-ok` -> `offset-confirmed` -> `leak-confirmed` or `libc-base-confirmed` -> `rop-working` or `orw-working` -> `flag-confirmed`
- format string: `env-ok` -> `fmt-offset-confirmed` -> `leak-confirmed` -> `write-confirmed` -> `flag-confirmed`
- heap: `env-ok` -> `heap-layout-confirmed` -> `heap-base-confirmed` and/or `libc-base-confirmed` -> `arb-write-confirmed` -> `pivot-ready`, `setcontext-ready`, or `fsop-ready` -> `orw-working` -> `flag-confirmed`
- seccomp or sandboxed userland: `env-ok` -> `seccomp-profile-confirmed` -> `primitive-confirmed` -> `openat-orw-working` or `mmap-bypass-working` -> `flag-confirmed`

Always checkpoint before risky pivots such as:

- the first large heap metadata corruption
- the first `setcontext`, FSOP, ret2dlresolve, sigreturn, or `house-of-*` attempt
- switching exploit paths
- adapting a locally working exploit to remote

## Web UI

The Web UI is a zero-dependency Python service that serves a small frontend plus JSON APIs.

Start it with:

```bash
python3 webui/server.py
```

or:

```bash
./webui/start.sh
```

Default bind:

- host: `0.0.0.0`
- port: `9999`

Open:

```text
http://127.0.0.1:9999/
```

If you want it in the background:

```bash
nohup python3 webui/server.py --host 0.0.0.0 --port 9999 >/tmp/amadeus-webui.log 2>&1 &
```

### Frontend Usage

The current frontend is challenge-management first.

It supports:

- challenge list and filtering
- create + initialize a challenge
- edit `STATE.md`, `FACTS.md`, `.ctf-files`, and `.pwnrun`
- view `run_pwn.sh info` output
- create and restore checkpoints
- preview top-level files such as `exp.py`, `wp.md`, `exp_template.py`
- preview `attempts/*.md`
- preview binary files as a hex dump

Typical usage:

1. Open the page and pick a challenge from the left sidebar.
2. Use `Init Files` if the challenge has not been initialized yet.
3. Edit the core docs in the `Core Documents` panel and save them in place.
4. Use `Run Info` to confirm the resolved binary, `libc`, `ld`, host, and port.
5. Use `View` in `Top-Level Files` to inspect `exp.py`, `wp.md`, or other text files.
6. Create checkpoints before risky exploit pivots.
7. Restore a checkpoint if a branch goes bad.

### API Notes

Useful routes:

- `GET /api/challenges`
- `GET /api/challenges/<name>`
- `POST /api/challenges`
- `POST /api/challenges/<name>/init`
- `GET /api/challenges/<name>/run-info`
- `PUT /api/challenges/<name>/document?name=STATE.md`
- `POST /api/challenges/<name>/checkpoints`
- `POST /api/challenges/<name>/restore`
- `GET /api/challenges/<name>/file?path=exp.py`

## Skills

Amadeus is most useful when paired with Codex skills.

### Required for pwn work

- `ctf-pwn`

Use `ctf-pwn` for:

- stack overflow
- format string
- heap exploitation
- ret2libc / ROP
- GOT overwrite
- seccomp bypass
- sandbox escape in pwn-style binaries

### Strongly recommended

- `solve-challenge`

Use `solve-challenge` when you want one higher-level entrypoint that decides whether the target is pwn, reverse, web, crypto, or misc and then pulls in the right technique flow.

### Useful supporting skills

- `exploit-chain-planning`: refine exploit hypotheses into explicit staged plans
- `ctf-reverse`: binary reversing, obfuscated logic, custom VM analysis
- `ctf-web`: web challenge exploitation
- `ctf-crypto`: cryptography challenge solving
- `ctf-misc`: encoding, z3, jails, QR, audio, and other odd formats

### Recommended pairing

For pwn challenges:

1. Read `AGENTS.md`.
2. Read `challenges/AGENTS.md`.
3. Use `ctf-pwn` for exploit reasoning.
4. Use `STATE.md`, `FACTS.md`, `checkpoints/`, and `attempts/` to keep progress recoverable.

## `run_pwn.sh`

`run_pwn.sh` gives one entrypoint for:

- local exploit runs
- remote exploit runs
- patched local runs

It reads optional `.pwnrun` per challenge and exports normalized `PWN_*` environment variables:

- `PWN_MODE`
- `PWN_CHAL_DIR`
- `PWN_EXP`
- `PWN_BIN`
- `PWN_PATCHED_BIN`
- `PWN_ACTIVE_BIN`
- `PWN_LIBC`
- `PWN_LD`
- `PWN_HOST`
- `PWN_PORT`
- `PWN_LOCAL_ARGS`
- `PWN_REMOTE_ARGS`

For legacy exploits, the default behavior is compatible with the common pattern:

- local: `python3 exp.py`
- remote: `python3 exp.py r <host> <port>`

For new exploits, prefer reading `PWN_*` so that one script works cleanly across local, remote, and patched modes.

If setup looks wrong, inspect the resolved state first:

```bash
bin/run_pwn.sh challenges/baby_tcache info
```

## Libc Policy

Prefer this order:

1. Use the challenge-provided `libc` and `ld` if they exist.
2. Reproduce locally with `patchelf`, the provided loader, or `run_pwn.sh patched`.
3. If `libc` is not provided, leak symbols first and then identify the remote libc from a database such as `libc.rip`.

Avoid silently using the host libc unless that choice is explicitly verified.

## Outputs

For a finished pwn solve, the expected final artifacts are:

- `exp.py`
- `wp.md`

Optional but recommended supporting files:

- `STATE.md`
- `FACTS.md`
- `.pwnrun`
- `attempts/<note>.md`
- `checkpoints/<timestamp>-<name>/`

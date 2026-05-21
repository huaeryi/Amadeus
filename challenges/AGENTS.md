# Pwn Challenge Workflow

This directory contains pwn challenge folders such as `challenges/<name>`.

For any challenge in this directory:

1. Work inside that challenge directory.
2. Start by running `bin/init_challenge.sh <challenge_dir>` if `STATE.md` and `FACTS.md` do not exist yet.
3. Read the challenge files first and identify the main binary, patched binary, libc, ld, and `exp_template.py` if present.
4. Treat `FACTS.md` as confirmed facts only.
5. Use `STATE.md` for the current stage, next step, rejected branches, and open questions.
6. Build `exp.py` from `exp_template.py` when the template exists.
7. Prefer using `bin/run_pwn.sh <challenge_dir> [local|remote|patched]` as the standard execution entrypoint.
8. If `run_pwn.sh` is used, keep `.pwnrun` accurate for `BIN`, `PATCHED_BIN`, `LIBC`, `LD`, `HOST`, and `PORT`.
9. When writing or updating `exp.py`, prefer reading the `PWN_*` environment variables exported by `run_pwn.sh` so that local, remote, and patched runs share one interface.
10. Libc strategy:
    - If the challenge provides `libc` and `ld`, use those first.
    - For local reproduction, prefer `patchelf`, the provided loader, or `run_pwn.sh patched` instead of silently falling back to the host libc.
    - If the challenge does not provide libc, leak enough symbols first and then identify libc from databases such as `libc.rip`.
11. Do not default to the system libc when a challenge-local libc should exist but has not been verified yet.
12. Validate assumptions with local commands, `checksec`, `file`, `ldd`, `pwndbg`, `gdb`, `ROPgadget`, and the binary itself as needed.
13. Treat `FACTS.md` as append-only verified data. If a detail is still a guess, keep it in `STATE.md`, not in `FACTS.md`.
14. Use `STATE.md` for the current stage, next step, checkpoint plan, rejected branches, and open questions.
15. Create checkpoints only at meaningful milestones. They are rollback anchors, not autosaves.
16. Name checkpoints after confirmed capabilities or facts, not intent. Good generic names include:
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
17. Default checkpoint budget:
   - simple stack or format-string challenge: 3 to 4 checkpoints
   - medium stack, format-string, or heap challenge: 4 to 6 checkpoints
   - complex heap, seccomp, sandbox, or kernel challenge: 5 to 8 checkpoints
18. Recommended checkpoint cadence by bug class:
   - stack: `env-ok` -> `offset-confirmed` -> `leak-confirmed` or `libc-base-confirmed` -> `rop-working` or `orw-working` -> `flag-confirmed`
   - format string: `env-ok` -> `fmt-offset-confirmed` -> `leak-confirmed` -> `write-confirmed` -> `flag-confirmed`
   - heap: `env-ok` -> `heap-layout-confirmed` -> `heap-base-confirmed` and/or `libc-base-confirmed` -> `arb-write-confirmed` -> `pivot-ready`, `setcontext-ready`, or `fsop-ready` -> `orw-working` -> `flag-confirmed`
   - seccomp or sandboxed userland: `env-ok` -> `seccomp-profile-confirmed` -> `primitive-confirmed` -> `openat-orw-working` or `mmap-bypass-working` -> `flag-confirmed`
19. Always checkpoint before risky pivots such as:
   - the first heap metadata corruption that may poison later tests
   - the first `setcontext`, FSOP, ret2dlresolve, sigreturn, or `house-of-*` attempt
   - switching from one exploit path to a different path
   - adapting a locally working exploit to remote
20. If a branch fails, write a short note under `attempts/` with what was tried, why it failed, and which checkpoint was last good. Then restore instead of continuing on a dirty state.
21. Final outputs are `exp.py` and `wp.md`.

Suggested pwn loop:

1. Inspect protections and runtime environment.
2. Identify the bug class and exploitation primitive.
3. Record confirmed offsets, leaks, gadget choices, and libc reasoning in `FACTS.md`.
4. Record candidate exploit branches and why one branch was chosen in `STATE.md`.
5. Use `run_pwn.sh info <challenge_dir>` to inspect the resolved binary/libc/ld/host/port state when setup looks wrong.
6. After the first stable primitive, create a checkpoint such as `primitive-confirmed`.
7. If libc is unknown, treat symbol leaks as a distinct milestone before choosing offsets or one-gadgets.
8. After the first stable PIE, canary, heap, or libc leak, create the corresponding checkpoint.
9. Checkpoint again before risky pivots and before the remote adaptation pass.
10. Verify the final exploit locally before adapting to remote.
11. Create `flag-confirmed` only after the final exploit is stable and the tracked files are worth preserving.

This workflow is compatible with `ctf-pwn`: the skill provides exploitation technique knowledge, while these files provide local state management and rollback points.

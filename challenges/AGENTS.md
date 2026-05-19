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
13. Create checkpoints only at meaningful milestones. The principle is fixed, but the names should match the actual exploit progress of the current challenge.
14. Good checkpoint names describe a confirmed capability or fact, for example:
   - `env-ok`
   - `primitive-confirmed`
   - `offset-confirmed`
   - `leak-confirmed`
   - `libc-base-confirmed`
   - `code-exec-confirmed`
15. For format-string, heap, seccomp, sandbox, or kernel challenges, prefer more specific names such as `fmt-offset-confirmed`, `heap-base-confirmed`, `openat-orw-working`, or `kbase-leaked`.
16. If a branch fails, write a short note under `attempts/` and restore a prior checkpoint instead of continuing on a dirty state.
17. Final outputs are `exp.py` and `wp.md`.

Suggested pwn loop:

1. Inspect protections and runtime environment.
2. Identify the bug class and exploitation primitive.
3. Record confirmed offsets, leaks, gadget choices, and libc reasoning in `FACTS.md`.
4. Record candidate exploit branches and why one branch was chosen in `STATE.md`.
5. Use `run_pwn.sh info <challenge_dir>` to inspect the resolved binary/libc/ld/host/port state when setup looks wrong.
6. If libc is unknown, treat symbol leaks as a distinct milestone before choosing offsets or one-gadgets.
7. Name checkpoints after what has been confirmed, not after vague intent.
8. Checkpoint before risky exploit pivots.
9. Verify the final exploit locally before adapting to remote.

This workflow is compatible with `ctf-pwn`: the skill provides exploitation technique knowledge, while these files provide local state management and rollback points.

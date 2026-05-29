# Challenges

This directory stores local CTF challenge workspaces.

Each challenge should live in its own subdirectory:

```text
challenges/<challenge-name>/
```

Typical files inside a challenge directory:

- `cognition.json`: machine-readable facts, state, and capabilities
- `COGNITION.md`: generated human-readable view of cognition
- `evidence/`: command output, debugger logs, screenshots, and script result artifacts
- `cognition.json.metadata.tracked_files`: important files tracked by the workflow
- `.pwnrun`: pwn run configuration for `bin/run_pwn.sh`
- `attempts/`: notes for failed or abandoned branches
- `checkpoints/`: rollback snapshots created by `bin/checkpoint.sh`
- `exp.py` or `solve.py`: final exploit or solver script
- `wp.md`: final writeup
- challenge attachments such as binaries, source archives, libc, or ld

Initialize a challenge workspace with:

```bash
bin/init_challenge.sh challenges/<challenge-name>
```

For pwn challenges, prefer:

```bash
bin/run_pwn.sh challenges/<challenge-name> info
bin/run_pwn.sh challenges/<challenge-name> local
bin/run_pwn.sh challenges/<challenge-name> remote <host> <port>
bin/run_pwn.sh challenges/<challenge-name> patched
```

Checkpoint meaningful milestones only:

```bash
bin/checkpoint.sh env-ok challenges/<challenge-name>
bin/restore.sh latest challenges/<challenge-name>
```

Do not commit private flags, live tokens, cookies, session files, personal notes with secrets, or unrelated downloaded materials.

For workflow prompts, use `prompts/` through `bin/amds`; this directory is only for per-challenge state and artifacts.

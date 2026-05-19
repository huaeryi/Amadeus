# Amadeus Workflow

Use this directory as a lightweight toolbox for Codex-driven CTF work.

- `bin/` contains tiny helpers for initializing challenge state, creating checkpoints, and restoring checkpoints.
- `templates/` contains the default `STATE.md`, `FACTS.md`, and `.ctf-files`.
- `challenges/AGENTS.md` contains the generic pwn workflow that Codex should follow inside `challenges/<name>`.

When solving a pwn challenge under `challenges/`, prefer the challenge-local workflow in `challenges/AGENTS.md`.

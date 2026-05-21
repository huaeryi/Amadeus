# Amadeus Workflow

Use this directory as a lightweight toolbox for Codex-driven CTF work.

- `bin/` contains tiny helpers for initializing challenge state, creating checkpoints, and restoring checkpoints.
- `templates/` contains the default `STATE.md`, `FACTS.md`, and `.ctf-files`.
- `prompts/` contains workflow prompts used by `bin/amds`, including the pwn workflow.

When solving a pwn challenge through `bin/amds`, prefer the workflow embedded in `prompts/pwn.md`.

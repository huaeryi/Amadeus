# Amadeus Workflow

Use this directory as a lightweight toolbox for Codex-driven CTF work.

- `bin/` contains tiny helpers for initializing challenge state, creating checkpoints, and restoring checkpoints.
- `templates/` contains the default `cognition.json` and runtime metadata templates.
- `prompts/` contains workflow prompts used by `bin/amds`, including the pwn workflow.
- `prompts/guided.md` is appended by `bin/amds guide ...` to make Codex ask short thinking questions before key pivots.
- `challenges/` may contain grouped challenge paths such as `challenges/defcon/baby_tcache`.

When solving a pwn challenge through `bin/amds`, prefer the workflow embedded in `prompts/pwn.md`.

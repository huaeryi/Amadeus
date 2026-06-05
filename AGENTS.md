# Amadeus Workflow

Use this directory as a lightweight toolbox for Codex-driven CTF work.

- `bin/` contains only the `amds` launcher.
- `scripts/` contains grouped helper scripts for challenge setup, state docs, platform fetching, and pwn execution.
- `templates/` contains the default `cognition.json` and runtime metadata templates.
- `prompts/` contains workflow prompts used by `bin/amds`, including the pwn workflow.
- `prompts/cmds/guide.md` is used by `bin/amds guide ...` to make Codex ask short thinking questions before key pivots.
- `challenges/` may contain grouped challenge paths such as `challenges/defcon/baby_tcache`.

When solving a pwn challenge through `bin/amds`, prefer the workflow embedded in `prompts/skills/pwn.md`.

# Amadeus Workflow

Use this directory as a lightweight toolbox for Codex-driven CTF work.

- `bin/` contains only the `amds` launcher.
- `scripts/` contains grouped helper scripts for challenge setup, state docs, platform fetching, and pwn execution.
- `templates/` contains the default `cognition.json` and runtime metadata templates.
- `prompts/` contains workflow prompts used by `bin/amds`, including the pwn workflow.
- `prompts/cmds/guide.md` is used by `bin/amds guide ...` to make Codex ask short thinking questions before key pivots.
- `challenges/` may contain grouped challenge paths such as `challenges/defcon/baby_tcache`.

Treat the Amadeus root as a toolbox, not a challenge workspace. When solving, preprocessing, auditing, or learning from a challenge through `bin/amds`, Codex/Claude should be launched with the current working directory set to the resolved challenge directory under `challenges/`. Create, edit, delete, run, and checkpoint challenge files only inside that challenge directory unless the prompt explicitly asks to update shared Amadeus files such as `prompts/learn/*`.

When solving a pwn challenge through `bin/amds`, prefer the workflow embedded in `prompts/workflow/pwn.md`.

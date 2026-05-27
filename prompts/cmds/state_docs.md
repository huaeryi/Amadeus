facts/state 机制：
- `facts.json` 是已确认事实的机器可读 source of truth；`FACTS.md` 只能由 `{{root_name}}/bin/state_docs.py render {{challenge_path}}` 生成
- `state.json` 是当前阶段、下一步、失败路线、开放问题的机器可读 source of truth；`STATE.md` 只能由 `{{root_name}}/bin/state_docs.py render {{challenge_path}}` 生成
- 如果题目目录没有 `facts.json` 或 `state.json`，运行 `{{root_name}}/bin/state_docs.py init {{challenge_path}}`
- 每次新增或更新事实/状态后，必须运行 `{{root_name}}/bin/state_docs.py render {{challenge_path}}`
- 不要直接手写 `FACTS.md` 或 `STATE.md`

写入规则：
- 已确认事实写入 `facts.json`
- 推测、候选路线、失败路线、下一步和开放问题写入 `state.json`
- 当前调试会话信息写入 `state.json.debug`；pwn 题默认 `pwndbg_mcp` 是 `127.0.0.1:8780`，多题并行时必须换端口并记录清楚
- `FACTS.md` / `STATE.md` 只用于阅读和汇报，不作为编辑入口

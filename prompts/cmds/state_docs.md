cognition 机制：
- `amds_state/cognition.json` 是 metadata、facts、state、capabilities 的机器可读 source of truth；`amds_state/COGNITION.md` 只能由 `{{root_name}}/scripts/state/state_docs.py render {{challenge_path}}` 生成
- `amds_state/cognition.json.metadata` 放题目来源、平台、分类、标签、附件和本地文件信息
- `amds_state/cognition.json.metadata.evidence_dir` 固定为 `amds_state/evidence`；后续命令输出、调试日志、截图、脚本结果等证据文件都放进 `{{challenge_path}}/amds_state/evidence/`
- `amds_state/cognition.json.facts` 只放已确认事实
- `amds_state/cognition.json.state` 放当前阶段、下一步、失败路线、开放问题和调试会话
- 如果题目目录没有 `amds_state/cognition.json`，运行 `{{root_name}}/scripts/state/state_docs.py init {{challenge_path}}`
- 每次新增或更新 cognition 后，必须运行 `{{root_name}}/scripts/state/state_docs.py render {{challenge_path}}`
- 不要直接手写 `amds_state/COGNITION.md`

写入规则：
- 已确认事实写入 `amds_state/cognition.json.facts`
- 推测、候选路线、失败路线、下一步和开放问题写入 `amds_state/cognition.json.state`
- 当前调试会话信息写入 `amds_state/cognition.json.state.debug`；pwn 题默认 `pwndbg_mcp` 是 `127.0.0.1:8780`，多题并行时必须换端口并记录清楚
- `amds_state/COGNITION.md` 只用于阅读和汇报，不作为编辑入口

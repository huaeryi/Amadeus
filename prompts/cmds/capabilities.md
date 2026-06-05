capabilities 机制：
- `amds_state/cognition.json.capabilities` 是机器可读 source of truth；`amds_state/COGNITION.md` 只能由 `{{root_name}}/scripts/state/capabilities.py render {{challenge_path}}` 生成
- 如果题目目录没有 `amds_state/cognition.json`，运行 `{{root_name}}/scripts/state/capabilities.py init {{challenge_path}}`
- 每次新增或更新 capability 后，必须运行 `{{root_name}}/scripts/state/capabilities.py render {{challenge_path}}`；如果校验失败，先修 JSON

status 生命周期：
- `hypothesis`：推测可能成立，只能作为探索方向，不能作为强依赖
- `observed`：已有 runtime/debugger/IDA/日志证据，但还没有稳定验证
- `verified`：通过明确测试验证，可以作为 planner 强依赖；必须包含 evidence 和 verification
- `blocked`：由于 mitigation/constraint/environment 被阻塞；必须包含 blocked_by、reason/summary 和 evidence
- `target`：当前正在尝试获得的 capability

env 规则：
- 每个 capability 必须带 `env`
- 可用 env：`local`、`native`、`docker`、`patched`、`remote`
- `local` verified 不等于 `remote` verified；跨环境迁移必须新建或更新对应 env 的 capability 并重新验证
- planner 后续会按 env 过滤 capability，不要把不同环境的能力合并成一条

evidence 规则：
- 每个 capability 必须有 evidence
- evidence 至少写 `type`、`summary`，并提供 `artifact` 或 `command`
- runtime/gdb/pwndbg/IDA/checksec/脚本输出都可以作为 evidence，但必须能复现或定位；需要保存的输出统一写入 `amds_state/evidence/`，artifact 使用相对路径如 `amds_state/evidence/checksec.txt`
- verified capability 的 `verification` 必须包含 `verified: true`、`method`、`summary`，并提供 `artifact` 或 `command`
- blocked capability 的 `blocked_by` 不能为空，summary 要说明阻塞原因

更新规则：
- 新建 capability 时填写 `created_at` 和 `updated_at`
- 更新已有 capability 时保留 `created_at`，只更新 `updated_at`
- 不要只在 `amds_state/COGNITION.md` 写结论；所有结论必须先进 `amds_state/cognition.json.capabilities`

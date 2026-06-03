开始对 `{{challenge_path}}` 做安全审计/挖洞。

本次审计动作由 `audit` 命令触发；具体审计方法由 `--workflow {{workflow}}` 决定，流程见后续 `{{root_name}}/prompts/skills/{{workflow}}.md`。不要把本任务当作 CTF solve 或拿 flag 流程；目标是找出可验证、可复现、可解释影响的 findings。

通用入口要求：
1. 在目标目录内工作
2. 如果 `amds_state/cognition.json` 不存在，先运行 `{{root_name}}/bin/init_challenge.sh {{challenge_path}}`
3. 先读 `{{root_name}}/AGENTS.md`
4. 再按 `{{root_name}}/prompts/skills/{{workflow}}.md` 的审计约束推进
5. checkpoint 统一遵守 `{{root_name}}/prompts/cmds/checkpoint.md`
6. 已确认事实写入 `amds_state/cognition.json.facts`，审计假设、候选漏洞、失败路线和下一步写入 `amds_state/cognition.json.state`
7. capability 统一写入 `amds_state/cognition.json.capabilities`；更新后用 `{{root_name}}/bin/state_docs.py render {{challenge_path}}` 生成 `amds_state/COGNITION.md`，不要直接手写 `amds_state/COGNITION.md`
8. 长命令输出、调试日志、PoC 输出、HTTP transcript、测试日志和截图等证据文件统一保存到 `{{challenge_path}}/amds_state/evidence/`，在 `amds_state/cognition.json` 中只写摘要和相对路径
9. 不要攻击非授权目标，不要对真实资金、真实账号或生产系统执行有副作用的操作
10. 不要搜索或复制公开审计报告、issue、漏洞复现或第三方 findings；可以使用本地源码和项目文档作为事实来源

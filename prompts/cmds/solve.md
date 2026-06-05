开始解决 `{{challenge_path}}` 这道 CTF 题。

本次 CTF 方向由 `--workflow {{workflow}}` 决定；具体题型流程见后续 `{{root_name}}/prompts/skills/{{workflow}}.md` 内容，不要根据题目名或旧经验擅自切换方向。若实际材料明显不属于该方向，先在 `amds_state/cognition.json.state` 记录证据和 pivot 原因，再渲染 `amds_state/COGNITION.md` 后切换思路。

通用入口要求：
1. 在题目目录内工作
2. 如果 `amds_state/cognition.json` 不存在，先运行 `{{root_name}}/scripts/challenge/init_challenge.sh {{challenge_path}}`
3. 先读 `{{root_name}}/AGENTS.md`
4. 再按 `{{root_name}}/prompts/skills/{{workflow}}.md` 的题型约束推进
5. checkpoint 统一遵守 `{{root_name}}/prompts/cmds/checkpoint.md`
6. 已确认事实写入 `amds_state/cognition.json.facts`，推测、候选路线、失败路线和下一步写入 `amds_state/cognition.json.state`
7. capability 统一写入 `amds_state/cognition.json.capabilities`；更新后用 `{{root_name}}/scripts/state/state_docs.py render {{challenge_path}}` 生成 `amds_state/COGNITION.md`，不要直接手写 `amds_state/COGNITION.md`
8. 长命令输出、调试日志、脚本结果、截图等证据文件统一保存到 `{{challenge_path}}/amds_state/evidence/`，在 `amds_state/cognition.json` 中只写摘要和相对路径
9. 不要搜索或读取任何 WP、题解、公开 exploit、博客复现或 GitHub 解法

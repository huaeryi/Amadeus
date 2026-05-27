开始解决 `{{challenge_path}}` 这道 CTF 题。

本次 CTF 方向由 `--workflow {{workflow}}` 决定；具体题型流程见后续 `{{root_name}}/prompts/skills/{{workflow}}.md` 内容，不要根据题目名或旧经验擅自切换方向。若实际材料明显不属于该方向，先在 `state.json` 记录证据和 pivot 原因，再渲染 `STATE.md` 后切换思路。

通用入口要求：
1. 在题目目录内工作
2. 如果 `state.json` 和 `facts.json` 不存在，先运行 `{{root_name}}/bin/init_challenge.sh {{challenge_path}}`
3. 先读 `{{root_name}}/AGENTS.md`
4. 再按 `{{root_name}}/prompts/skills/{{workflow}}.md` 的题型约束推进
5. checkpoint 统一遵守 `{{root_name}}/prompts/cmds/checkpoint.md`
6. 已确认事实写入 `facts.json`，推测、候选路线、失败路线和下一步写入 `state.json`，再用 `{{root_name}}/bin/state_docs.py render {{challenge_path}}` 生成 Markdown
7. capability 统一写入 `capabilities.json`，并用 `{{root_name}}/bin/capabilities.py render {{challenge_path}}` 生成 `CAPABILITIES.md`；不要直接手写 `CAPABILITIES.md`
8. 不要搜索或读取任何 WP、题解、公开 exploit、博客复现或 GitHub 解法

主动学习模式已启用，开始带我解决 `{{challenge_path}}` 这道 CTF 题。

本次 CTF 方向由 `--workflow {{workflow}}` 决定；具体题型流程见后续 `{{root_name}}/prompts/skills/{{workflow}}.md` 内容。你既要推进题目，也要让我同步思考并看懂关键判断。

通用入口要求：
1. 在题目目录内工作
2. 如果 `state.json` 和 `facts.json` 不存在，先运行 `{{root_name}}/bin/init_challenge.sh {{challenge_path}}`
3. 先读 `{{root_name}}/AGENTS.md`
4. 再按 `{{root_name}}/prompts/skills/{{workflow}}.md` 的题型约束推进
5. checkpoint 统一遵守 `{{root_name}}/prompts/cmds/checkpoint.md`
6. 已确认事实写入 `facts.json`，推测、候选路线、失败路线和下一步写入 `state.json`，再用 `{{root_name}}/bin/state_docs.py render {{challenge_path}}` 生成 Markdown
7. capability 统一写入 `capabilities.json`，并用 `{{root_name}}/bin/capabilities.py render {{challenge_path}}` 生成 `CAPABILITIES.md`；不要直接手写 `CAPABILITIES.md`
8. 不要搜索或读取任何 WP、题解、公开 exploit、博客复现或 GitHub 解法

交互节奏：
1. 每进入一个新阶段，先用 3 到 6 行说明当前阶段的目标、已知事实和你准备验证的假设。
2. 在关键分叉前先停下来问我 1 到 3 个具体问题，让我先判断；问题必须能用题目事实回答，不要问泛泛的开放问题。
3. 如果我回答错了，先指出错在哪里，再给最小反例、命令输出或代码位置；不要直接跳到最终 payload。
4. 如果我暂时不回答，而你继续推进，必须在 `state.json` 的 `your_turn` 记录我应该补想的判断题和当前正确答案暂不展开的部分，再渲染 `STATE.md`。
5. 每跑一个关键命令后，先解释输出中哪几行改变了判断，再决定下一步。

思考门槛：
- 环境确认后，问我：保护、架构、运行方式或服务入口分别会限制哪些路线。
- 发现 bug、oracle、约束或核心行为后，问我：输入如何影响状态，最可能形成什么 primitive 或解题抓手。
- 选择 exploit/solve 路线前，问我：至少两条候选路线、各自依赖的 leak/写入/oracle/约束是什么。
- 写关键脚本前，问我：脚本的输入、输出、失败条件和验证方式是什么。
- 拿到 flag 前，问我：为什么这条链本地成立，远程或最终验证还缺哪些假设。

讲解要求：
- 使用“事实 -> 推理 -> 验证 -> 下一步”的格式解释关键步骤。
- 把容易迁移的模式写进 `wp.md` 的解题思路，不只写命令流水账。
- 遇到我明显依赖 AI 代想时，降低速度，给提示和检查问题，而不是继续完整代做。
- 不要展示隐藏推理长文；给我可检查的结论、关键中间值、验证命令和必要的短解释。

产物要求：
- 在 `state.json` 中维护 `your_turn`，保留 3 到 5 个当前阶段我应该能回答的问题，并渲染到 `STATE.md` 的 `Your Turn` 小节。
- 在 `wp.md` 中增加 `Learning checkpoints` 小节，记录这题最值得复用的 3 到 5 个判断点。
- 最终汇报时除了 flag 和文件，还要列出我应该复盘的判断题。

从 `{{challenge_path}}` 这道已经完成或阶段性完成的 CTF 题中提炼最简单、最有效、可迁移的做题经验，并直接维护对应题型的长期学习文件。

这是学习任务，不是重新解题任务。不要重写 exploit，不要重新搜索题解，不要访问 WP、公开 exploit、博客复现或 GitHub 解法。

先读：
- `{{root_name}}/AGENTS.md`
- `{{challenge_path}}/cognition.json`
- `{{challenge_path}}/COGNITION.md`，仅作为 JSON 渲染视图辅助阅读
- `{{challenge_path}}/wp.md`，如果存在
- `{{challenge_path}}/exp.py` 或 `solve.py`，如果存在
- `{{challenge_path}}/REFLECTION.md`，如果存在
- 题目目录 git 历史，例如 `git -C {{challenge_path}} log --oneline --decorate --all`，如果存在

Session 输入：
- session id: `{{session}}`
- session path: `{{session_path}}`

学习来源：
- 如果 session id 为空，只从 challenge 目录中的文件学习。
- 如果 session id 非空，从 challenge 文件 + 指定 session 一起学习；challenge 文件仍是事实基准，session 只作为过程证据。
- 指定 session 时，优先读取该 session 目录中的 `meta.json`、`prompt.md`、`transcript.md`、`transcript.ansi`、`events.log`、`summary.md`，存在什么读什么。
- 如果 session id 是 `latest`，按 `{{session_path}}` 指向的最新 session 读取；否则按指定 session id 读取。
- 如果指定 session 但目录不存在或没有 transcript，继续从 challenge 文件学习，并在 `REFLECTION.md` 和 `LEARNING_LOG.md` 的 `skipped` 中记录 session 不可用。
- 不要把 session 中的完整对话复制进长期学习文件，只提炼最简单有效的过程规则。

根据 `cognition.json.metadata`、`description.md`、`cognition.json.facts` 或 `cognition.json.state` 判断题型，然后只修改对应文件：
- pwn: `{{root_name}}/prompts/learn/pwn_learning.md`
- web: `{{root_name}}/prompts/learn/web_learning.md`
- crypto: `{{root_name}}/prompts/learn/crypto_learning.md`
- reverse: `{{root_name}}/prompts/learn/reverse_learning.md`
- misc: `{{root_name}}/prompts/learn/misc_learning.md`

每次执行还必须更新学习日志：
- `{{root_name}}/prompts/learn/LEARNING_LOG.md`

如果题型不确定，先从题目材料中判断最主要的题型；仍然不确定时，只更新 `{{challenge_path}}/REFLECTION.md`，不要改长期学习文件。

核心目标：
1. 找出这题里最值得复用的 1 到 5 条经验
2. 把经验压缩成未来做题时能立刻执行的短规则
3. 直接修改对应的 `prompts/learn/<category>_learning.md`
4. 优先改写、合并、替换或删除旧规则；只有确实没有覆盖时才新增
5. 在题目目录更新一个简短 `REFLECTION.md`，说明本次从这题学到了什么、更新了哪个长期学习文件
6. 在 `prompts/learn/LEARNING_LOG.md` 追加一条简短日志，记录这次学习改动

什么可以写进长期学习文件：
- 触发信号：看到什么现象、文件、保护、源码模式、参数规模、输出特征时该想到这条规则
- 最小有效动作：下一步最应该做什么，优先是最小验证或最高收益检查
- 验证方式：用什么命令、脚本、调试观察、回代测试来确认
- 常见误区：什么做法会浪费时间
- 换路线条件：什么证据出现后应该停止当前方向

什么不要写进长期学习文件：
- 本题 flag、远程地址、账号、cookie、token
- 本题一次性地址、offset、gadget、payload、文件名魔数
- 完整 writeup 或详细解题流水账
- 没有被当前题验证的猜测
- 只适用于当前题目录结构、当前远程环境或当前二进制布局的内容
- 已经存在的同义规则

长期学习文件的维护方式：
- 先读完整文件，判断新经验是否已经被现有规则覆盖
- 优先修改已有规则，让它更短、更准、更可执行
- 合并语义重复的规则，删除过长、过细、题目专属或低价值规则
- 只有现有规则无法覆盖新经验时才新增规则
- 每条规则要短，能指导下一次行动
- 用“信号 -> 动作 -> 验证 -> 避免”的结构
- 保留题型文件原有结构；必要时可以重排小节让文件更清晰
- 每次维护后，整个题型学习文件仍应保持简短有效；不要为了记录本题而让文件膨胀

建议规则格式：

```md
## Learned Process Rules

### <short rule name>

- Signal:
- Action:
- Verify:
- Avoid:
```

`REFLECTION.md` 简短记录即可：

```md
# Reflection

## Learned

- 

## Time Wasters

- 

## Updated Long-term Learning

- file:
- rules changed:
```

`LEARNING_LOG.md` 追加记录格式：

```md
## YYYY-MM-DD HH:MM <challenge-name>

- category:
- updated:
- changed:
- removed:
- skipped:
```

日志规则：
- 追加到文件末尾，不要重写历史记录
- `changed` 写修改、新增或合并的规则名/一句话摘要
- `removed` 写删除或被合并掉的低价值规则；没有则写 `none`
- `skipped` 记录没有写入长期学习文件的题目专属内容或低置信度结论
- 不要写 flag、token、远程地址、具体 exploit payload、一次性 offset

最终汇报：
- 更新了哪个 `prompts/learn/*_learning.md`
- 在 `prompts/learn/LEARNING_LOG.md` 追加了什么日志
- 修改、合并、新增或删除了哪几条最重要规则
- 哪些内容因为太题目专属没有写入长期学习文件

在当前题目目录中推断 Amadeus solve 命令，但不要开始解题。

当前题目目录：
`{{challenge_path}}`

目标是产出一个可直接运行的命令，格式必须等价于：

```bash
{{root_name}}/bin/amds --mode solve --workflow <pwn|web|crypto|reverse|misc|x402> {{challenge_path}}
```

推断规则：
1. 优先使用用户通过 `--append` 提供的明确题型、命令片段或线索，例如 `--workflow web`、`amds solve crypto`、`题型 reverse`
2. 其次读取当前目录的 `description.md`、`amds_state/cognition.json`、`cognition.json` 和明显附件类型
3. 只允许选择 `pwn`、`web`、`crypto`、`reverse`、`misc`、`x402` 之一，不要发明新的 workflow
4. 如果证据冲突，说明冲突点，并选择证据最强的 workflow
5. 如果没有足够证据，默认选择 `pwn`

输出要求：
- 第一行只输出最终命令，不要加解释
- 后续最多用 3 行说明 workflow 依据
- 不要运行命令，不要初始化题目，不要读取 WP/题解/公开 exploit

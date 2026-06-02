题型 workflow：crypto。按 `ctf-crypto` 的思路解决 `{{challenge_path}}`。

优先使用这些 skill：
- `ctf-crypto`：主技能，默认按这个做
- `solve-challenge`：用于先做总分类和调度
- `ctf-writeup`：用于最终整理 `wp.md`

这题主要按 crypto 路线推进，不要偏离主线；除非题目材料明确证明分类错误，否则 CTF 方向以 `--workflow crypto` 为准。

先读：
- `{{root_name}}/prompts/learn/crypto_learning.md`

工作要求：
1. 读取题目目录中的附件、题面、交互脚本、输出文件和源码
2. 识别密码体制、参数规模、随机数来源、padding/模式/签名细节和可交互 oracle
3. 优先写可复现的 `solve.py` 或 `exp.py`，不要只在 REPL 中手算
4. 如果涉及远程交互，脚本应支持本地文件输入和远程连接两种模式
5. 到关键里程碑时按 `{{root_name}}/prompts/cmds/checkpoint.md` 创建具体 checkpoint；crypto 常用名称例如 `rsa-modulus-factored`、`nonce-reuse-verified`、`padding-oracle-bit-working`、`aes-key-recovered`、`plaintext-blocks-recovered`
6. 如果某条路线失败，不要在脏状态上持续修补；在 `cognition.json.state` 的 rejected_branches 记录失败原因，并按公共 checkpoint 策略回退或开分支
7. 必须实际运行脚本拿到 flag，并把 flag 结果作为完成标准
8. 最终产出 `exp.py` 或 `solve.py`，以及 `wp.md`
9. 如果缺少远程信息、附件信息或验证条件，再向我询问

执行约束：
- 先做本地分析和验证，不要跳过参数检查
- 不要搜索或读取任何 WP/题解/公开 exploit
- 不要假设旧脚本一定可用，结论必须基于当前目录中的文件和验证结果
- 只把确认过的事实写进 `cognition.json.facts`
- 推测、分支路线和下一步放进 `cognition.json.state`
- 参数 dump、脚本输出、solver 日志等证据写入 `evidence/`，在 `cognition.json` 中引用相对路径
- checkpoint 和回退统一遵守 `{{root_name}}/prompts/cmds/checkpoint.md`
- 可以使用 SageMath、Python、z3、PARI/GP、fplll、RsaCtfTool 等本地工具，但要记录关键参数和验证方式

开始解决 `{{challenge_path}}` 这道 misc 题，按 `ctf-misc` 的思路做。

优先使用这些 skill：
- `ctf-misc`：主技能，默认按这个做
- `solve-challenge`：用于先做总分类和调度
- `ctf-writeup`：用于最终整理 `wp.md`

这题主要按 misc 路线推进，不要偏离主线；如果确认题目实际属于 crypto/web/reverse/pwn，再在 `STATE.md` 记录 pivot 原因并切换对应技能思路。

先读：
- `{{root_name}}/AGENTS.md`
- `{{root_name}}/prompts/learn/misc_learning.md`

工作要求：
1. 先运行 `{{root_name}}/bin/init_challenge.sh {{challenge_path}}`
2. 读取题目目录中的附件、题面、脚本、流量、图片、音频、压缩包和输出文件
3. 把已确认事实写进 `FACTS.md`
4. 把当前阶段、下一步、失败路线和开放问题写进 `STATE.md`
5. 先识别文件类型、编码链、压缩/嵌套结构、隐写、协议、约束求解、jail、游戏逻辑或交互协议
6. 优先写可复现的 `solve.py` 或 `exp.py`，不要只保留手工步骤
7. 到关键里程碑时运行 checkpoint；名称不用固定死，应根据题目实际进展命名，例如 `env-ok`、`format-confirmed`、`decode-chain-confirmed`、`oracle-confirmed`、`payload-confirmed`
8. 如果某条路线失败，不要在脏状态上持续修补；在 `attempts/` 记录失败原因，必要时用 `restore.sh` 回退到上一个 checkpoint
9. 必须实际运行脚本或复现步骤拿到 flag，并把 flag 结果作为完成标准
10. 最终产出 `exp.py` 或 `solve.py`，以及 `wp.md`
11. 如果缺少远程信息、附件信息或验证条件，再向我询问

执行约束：
- 先做本地文件识别和最小复现，不要跳过基础取证
- 不要搜索或读取任何 WP/题解/公开 exploit
- 不要假设旧脚本一定可用，结论必须基于当前目录中的文件和验证结果
- 只把确认过的事实写进 `FACTS.md`
- 推测、分支路线和下一步放进 `STATE.md`
- 分支失败后优先回退到 checkpoint，再换路线
- 可以使用 binwalk、exiftool、tshark、zsteg、steghide、ffmpeg、sox、z3 等本地工具，但要记录关键命令和验证结果

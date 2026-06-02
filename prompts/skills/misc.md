题型 workflow：misc。按 `ctf-misc` 的思路解决 `{{challenge_path}}`。

优先使用这些 skill：
- `ctf-misc`：主技能，默认按这个做
- `solve-challenge`：用于先做总分类和调度
- `ctf-writeup`：用于最终整理 `wp.md`

这题主要按 misc 路线推进，不要偏离主线；除非题目材料明确证明分类错误，否则 CTF 方向以 `--workflow misc` 为准。如果确认题目实际属于 crypto/web/reverse/pwn，先在 `cognition.json.state` 记录 pivot 原因并渲染 `COGNITION.md`，再切换对应技能思路。

先读：
- `{{root_name}}/prompts/learn/misc_learning.md`

工作要求：
1. 读取题目目录中的附件、题面、脚本、流量、图片、音频、压缩包和输出文件
2. 先识别文件类型、编码链、压缩/嵌套结构、隐写、协议、约束求解、jail、游戏逻辑或交互协议
3. 优先写可复现的 `solve.py` 或 `exp.py`，不要只保留手工步骤
4. 到关键里程碑时按 `{{root_name}}/prompts/cmds/checkpoint.md` 创建具体 checkpoint；misc 常用名称例如 `file-types-profiled`、`zip-layer-3-extracted`、`qr-grid-decoded`、`pcap-dns-channel-found`、`jail-escape-payload-working`
5. 如果某条路线失败，不要在脏状态上持续修补；在 `cognition.json.state` 的 rejected_branches 记录失败原因，并按公共 checkpoint 策略回退或开分支
6. 必须实际运行脚本或复现步骤拿到 flag，并把 flag 结果作为完成标准
7. 最终产出 `exp.py` 或 `solve.py`，以及 `wp.md`
8. 如果缺少远程信息、附件信息或验证条件，再向我询问

执行约束：
- 先做本地文件识别和最小复现，不要跳过基础取证
- 不要搜索或读取任何 WP/题解/公开 exploit
- 不要假设旧脚本一定可用，结论必须基于当前目录中的文件和验证结果
- 只把确认过的事实写进 `cognition.json.facts`
- 推测、分支路线和下一步放进 `cognition.json.state`
- 解码中间结果、工具输出、提取文件说明等证据写入 `evidence/`，在 `cognition.json` 中引用相对路径
- checkpoint 和回退统一遵守 `{{root_name}}/prompts/cmds/checkpoint.md`
- 可以使用 binwalk、exiftool、tshark、zsteg、steghide、ffmpeg、sox、z3 等本地工具，但要记录关键命令和验证结果

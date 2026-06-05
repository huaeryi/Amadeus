题型 workflow：reverse。按 `ctf-reverse` 的思路解决 `{{challenge_path}}`。

优先使用这些 skill：
- `ctf-reverse`：主技能，默认按这个做
- `solve-challenge`：用于先做总分类和调度
- `ctf-writeup`：用于最终整理 `wp.md`

这题主要按 reverse 路线推进，不要偏离主线；除非题目材料明确证明分类错误，否则 CTF 方向以 `--workflow reverse` 为准。

先读：
- `{{root_name}}/prompts/learn/reverse_learning.md`

工作要求：
1. 读取题目目录中的二进制、脚本、字节码、APK、WASM、配置、题面和附件
2. 先确认文件类型、架构、保护、打包/混淆方式、输入输出行为和 flag 校验路径
3. 优先写可复现的 `solve.py` 或 `exp.py`，用于还原算法、求解约束、patch 或自动化调试
4. 对复杂校验逻辑，优先抽取算法、符号执行、约束求解、模拟 VM 或 patch 验证，不要只靠手工猜
5. 到关键里程碑时按 `{{root_name}}/prompts/cmds/checkpoint.md` 创建具体 checkpoint；reverse 常用名称例如 `binary-arch-profiled`、`checker-function-located`、`vm-opcodes-mapped`、`z3-model-solves`、`patched-checker-accepted`
6. 如果某条路线失败，不要在脏状态上持续修补；在 `amds_state/cognition.json.state` 的 rejected_branches 记录失败原因，并按公共 checkpoint 策略回退或开分支
7. 必须实际运行脚本或目标程序验证 flag，并把 flag 结果作为完成标准
8. 最终产出 `exp.py` 或 `solve.py`，以及 `wp.md`
9. 如果缺少远程信息、附件信息或验证条件，再向我询问

执行约束：
- 先做本地静态和动态分析，不要跳过基础文件识别
- 不要搜索或读取任何 WP/题解/公开 exploit
- 不要假设旧脚本一定可用，结论必须基于当前目录中的文件和验证结果
- 只把确认过的事实写进 `amds_state/cognition.json.facts`
- 推测、分支路线和下一步放进 `amds_state/cognition.json.state`
- 反编译片段、调试输出、patch/solver 验证结果等证据写入 `amds_state/evidence/`，在 `amds_state/cognition.json` 中引用相对路径
- checkpoint 和回退统一遵守 `{{root_name}}/prompts/cmds/checkpoint.md`
- 可以使用 strings、readelf、objdump、gdb、radare2、Ghidra、angr、z3、jadx、apktool、wasm-tools 等本地工具，但要记录关键结论和验证方式

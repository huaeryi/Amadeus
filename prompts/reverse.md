开始解决 `{{challenge_path}}` 这道 reverse 题，按 `ctf-reverse` 的思路做。

优先使用这些 skill：
- `ctf-reverse`：主技能，默认按这个做
- `solve-challenge`：用于先做总分类和调度
- `ctf-writeup`：用于最终整理 `wp.md`

这题主要按 reverse 路线推进，不要偏离主线。

先读：
- `{{root_name}}/AGENTS.md`

工作要求：
1. 先运行 `{{root_name}}/bin/init_challenge.sh {{challenge_path}}`
2. 读取题目目录中的二进制、脚本、字节码、APK、WASM、配置、题面和附件
3. 把已确认事实写进 `FACTS.md`
4. 把当前阶段、下一步、失败路线和开放问题写进 `STATE.md`
5. 先确认文件类型、架构、保护、打包/混淆方式、输入输出行为和 flag 校验路径
6. 优先写可复现的 `solve.py` 或 `exp.py`，用于还原算法、求解约束、patch 或自动化调试
7. 对复杂校验逻辑，优先抽取算法、符号执行、约束求解、模拟 VM 或 patch 验证，不要只靠手工猜
8. 到关键里程碑时运行 checkpoint；名称不用固定死，应根据题目实际进展命名，例如 `env-ok`、`format-confirmed`、`checker-found`、`algorithm-recovered`、`constraints-solved`
9. 如果某条路线失败，不要在脏状态上持续修补；在 `attempts/` 记录失败原因，必要时用 `restore.sh` 回退到上一个 checkpoint
10. 必须实际运行脚本或目标程序验证 flag，并把 flag 结果作为完成标准
11. 最终产出 `exp.py` 或 `solve.py`，以及 `wp.md`
12. 如果缺少远程信息、附件信息或验证条件，再向我询问

执行约束：
- 先做本地静态和动态分析，不要跳过基础文件识别
- 不要搜索或读取任何 WP/题解/公开 exploit
- 不要假设旧脚本一定可用，结论必须基于当前目录中的文件和验证结果
- 只把确认过的事实写进 `FACTS.md`
- 推测、分支路线和下一步放进 `STATE.md`
- 分支失败后优先回退到 checkpoint，再换路线
- 可以使用 strings、readelf、objdump、gdb、radare2、Ghidra、angr、z3、jadx、apktool、wasm-tools 等本地工具，但要记录关键结论和验证方式

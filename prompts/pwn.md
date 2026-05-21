开始解决 `{{challenge_path}}` 这道 pwn 题，按 `ctf-pwn` 的思路做。

优先使用这些 skill：
- `ctf-pwn`：主技能，默认按这个做
- `solve-challenge`：用于先做总分类和调度

这题主要按 pwn 路线推进，不要偏离主线。

核心流程：
1. 在题目目录内工作
2. 如果 `STATE.md` 和 `FACTS.md` 不存在，先运行 `{{root_name}}/bin/init_challenge.sh {{challenge_path}}`
3. 先读取题目目录中的附件，并确认主程序、patched binary、libc、ld、`exp_template.py`
4. `FACTS.md` 只记录已确认事实；仍是猜测的内容写进 `STATE.md`
5. `STATE.md` 记录当前阶段、下一步、checkpoint 计划、失败路线和开放问题
6. 如果存在 `exp_template.py`，基于它生成 `exp.py`
7. 优先使用 `{{root_name}}/bin/run_pwn.sh {{challenge_path}} [local|remote|patched]` 统一执行本地、远程和 patched 运行
8. 如果使用 `run_pwn.sh`，保持 `.pwnrun` 中的 `BIN`、`PATCHED_BIN`、`LIBC`、`LD`、`HOST`、`PORT` 准确
9. 新写或更新 `exp.py` 时，优先读取 `run_pwn.sh` 导出的 `PWN_*` 环境变量，让 local、remote、patched 共享同一套入口
10. 用本地命令、`checksec`、`file`、`ldd`、`pwndbg`、`gdb`、`ROPgadget` 和目标程序本身验证假设

libc 策略：
- 如果题目提供 libc 和 ld，优先使用题目提供的版本
- 本地复现优先使用 patchelf、题目提供的 loader，或 `run_pwn.sh patched`
- 不要在 challenge-local libc 应存在但尚未确认时直接使用系统 libc
- 如果题目没有给 libc，先泄露足够符号，再根据泄露结果使用 `libc.rip` 等库匹配站

调试工具策略：
- 简单栈溢出、ret2win、基础格式化字符串题可以直接用本地命令、gdb、pwndbg 和 `run_pwn.sh` 验证
- heap、ROP、seccomp、多阶段菜单、UAF、VM/JIT、沙箱逃逸或其它复杂运行时状态题，优先使用 `pwndbg-mcp` 辅助读取寄存器、栈、堆、bins、tcache、vmmap、断点和崩溃现场
- 使用 `pwndbg-mcp` 得到的运行时结论必须写入 `FACTS.md`，推测和下一步仍写入 `STATE.md`

先读：
- `{{root_name}}/AGENTS.md`

完成标准：
- 基于 `exp_template.py` 编写 `exp.py`；没有模板时直接创建可复现的 `exp.py`
- 需要时用 pwndbg、gdb、pwndbg-mcp 验证 offset、保护、leak、堆布局、寄存器状态和利用链
- 必须实际运行 exploit 拿到 flag，并把 flag 结果作为完成标准
- 最终产出 `exp.py` 和 `wp.md`
- 如果缺少远程信息、附件信息或验证条件，再向我询问

checkpoint 策略：
- checkpoint 是回滚锚点，不是自动保存；只在有意义的里程碑创建
- 名称按已确认能力或事实命名，不按意图命名
- 常用名称包括 `env-ok`、`primitive-confirmed`、`offset-confirmed`、`pie-leaked`、`canary-leaked`、`libc-base-confirmed`、`arb-read-confirmed`、`arb-write-confirmed`、`rop-ready`、`setcontext-ready`、`fsop-ready`、`orw-working`、`flag-confirmed`
- 简单栈溢出或格式化字符串题通常 3 到 4 个 checkpoint
- 中等栈、格式化字符串或堆题通常 4 到 6 个 checkpoint
- 复杂 heap、seccomp、sandbox 或 kernel 题通常 5 到 8 个 checkpoint

推荐 checkpoint 节奏：
- stack: `env-ok` -> `offset-confirmed` -> `leak-confirmed` 或 `libc-base-confirmed` -> `rop-working` 或 `orw-working` -> `flag-confirmed`
- format string: `env-ok` -> `fmt-offset-confirmed` -> `leak-confirmed` -> `write-confirmed` -> `flag-confirmed`
- heap: `env-ok` -> `heap-layout-confirmed` -> `heap-base-confirmed` 和/或 `libc-base-confirmed` -> `arb-write-confirmed` -> `pivot-ready`、`setcontext-ready` 或 `fsop-ready` -> `orw-working` -> `flag-confirmed`
- seccomp 或 sandboxed userland: `env-ok` -> `seccomp-profile-confirmed` -> `primitive-confirmed` -> `openat-orw-working` 或 `mmap-bypass-working` -> `flag-confirmed`

必须 checkpoint 的风险点：
- 第一次大型 heap metadata corruption
- 第一次 `setcontext`、FSOP、ret2dlresolve、sigreturn 或 `house-of-*` 尝试
- 从一条利用路线切换到另一条路线
- 把本地可用 exploit 适配到远程之前

建议 pwn loop：
1. 检查保护和运行环境
2. 识别 bug class 和 exploitation primitive
3. 把确认过的 offset、leak、gadget、libc 推导写进 `FACTS.md`
4. 把候选利用路线和选择原因写进 `STATE.md`
5. 配置异常时使用 `{{root_name}}/bin/run_pwn.sh {{challenge_path}} info` 检查 binary/libc/ld/host/port 解析状态
6. 第一个稳定 primitive 后创建 `primitive-confirmed` 或同等语义 checkpoint
7. libc 未知时，把符号泄露作为独立里程碑，不要提前套 offset 或 one_gadget
8. 第一个稳定 PIE、canary、heap 或 libc leak 后创建对应 checkpoint
9. risky pivot 前和 remote adaptation 前再次 checkpoint
10. 先本地验证最终 exploit，再适配远程
11. 只有最终 exploit 稳定且跟踪文件值得保留时，才创建 `flag-confirmed`

执行约束：
- 先做本地分析和验证，不要跳过检查
- 在测试或反作弊环境中，不要用 web 搜索 writeup、公开 exploit 仓库或题目解法；本地题目文件和 workspace 材料是主要事实来源
- 不要假设旧 exp 一定可用，结论必须基于当前目录中的文件和验证结果
- 只把确认过的事实写进 `FACTS.md`
- 推测、分支路线和下一步放进 `STATE.md`
- 分支失败后优先回退到 checkpoint，再换路线
- 新写的 `exp.py` 尽量兼容 `run_pwn.sh` 导出的 `PWN_*` 环境变量
- 不要在 libc 未确认时直接套用本机 libc 的偏移

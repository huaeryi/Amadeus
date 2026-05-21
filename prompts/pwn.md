开始解决 `{{challenge_path}}` 这道 pwn 题，按 `ctf-pwn` 的思路做。

优先使用这些 skill：
- `ctf-pwn`：主技能，默认按这个做
- `solve-challenge`：用于先做总分类和调度

这题主要按 pwn 路线推进，不要偏离主线。

先读：
- `{{root_name}}/challenges/AGENTS.md`
- `{{root_name}}/AGENTS.md`

工作要求：
1. 先运行 `{{root_name}}/bin/init_challenge.sh {{challenge_path}}`
2. 按 `{{root_name}}/challenges/AGENTS.md` 的流程工作
3. 先读取题目目录中的附件，并确认主程序、patched binary、libc、ld、`exp_template.py`
4. 把已确认事实写进 `FACTS.md`
5. 把当前阶段、下一步、失败路线和开放问题写进 `STATE.md`
6. 优先使用 `{{root_name}}/bin/run_pwn.sh {{challenge_path}} [local|remote|patched]` 统一执行本地、远程和 patched 运行
7. 到关键里程碑时运行 checkpoint；名称不用固定死，应根据题目实际进展命名，例如 `env-ok`、`primitive-confirmed`、`fmt-offset-confirmed`、`heap-base-confirmed`、`leak-confirmed`
8. 如果使用 `run_pwn.sh`，保持 `.pwnrun` 与当前题目状态一致
9. libc 策略：优先使用题目提供的 libc 和 ld；本地尽量用 patchelf、提供的 loader 或 patched 模式复现；如果题目没有给 libc，则先做泄露，再根据泄露结果去 `libc.rip` 之类的库匹配
10. 如果某条利用链失败，不要在脏状态上持续修补；在 `attempts/` 记录失败原因，必要时用 `restore.sh` 回退到上一个 checkpoint
11. 基于 `exp_template.py` 编写 `exp.py`
12. 需要时用 pwndbg / gdb 验证 offset、保护、leak 和利用链
13. 必须实际运行 exploit 拿到 flag，并把 flag 结果作为完成标准
14. 最终产出 `exp.py` 和 `wp.md`
15. 如果缺少远程信息、附件信息或验证条件，再向我询问

执行约束：
- 先做本地分析和验证，不要跳过检查
- 不要假设旧 exp 一定可用，结论必须基于当前目录中的文件和验证结果
- 只把确认过的事实写进 `FACTS.md`
- 推测、分支路线和下一步放进 `STATE.md`
- 分支失败后优先回退到 checkpoint，再换路线
- 新写的 `exp.py` 尽量兼容 `run_pwn.sh` 导出的 `PWN_*` 环境变量
- 不要在 libc 未确认时直接套用本机 libc 的偏移

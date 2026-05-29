checkpoint 策略：
- `{{root_name}}/bin/init_challenge.sh {{challenge_path}}` 会在题目目录内执行 `git init`，并在首次初始化时创建 `[ckpt0 <题目名>]`
- 后续 checkpoint 必须通过 `{{root_name}}/bin/checkpoint.sh <name> {{challenge_path}}` 创建；脚本会在题目目录 git 中提交 `[ckptN <name>]`
- checkpoint 是回滚锚点，不是自动保存；只在有意义的里程碑创建，不要把每次小改动都提交成 checkpoint
- 名称按已确认能力或事实命名，不按意图命名，例如 `env-ok`、`primitive-confirmed`、`route-map-confirmed`、`params-confirmed`、`checker-found`、`decode-chain-confirmed`、`flag-confirmed`
- 创建 checkpoint 前先确认 `cognition.json`、`exp.py`/`solve.py`/`wp.md` 等关键文件已写入当前结论，并运行 `{{root_name}}/bin/state_docs.py render {{challenge_path}}`
- 创建后用 `git -C {{challenge_path}} log --oneline -3` 快速确认提交
- 路线失败或需要回退时，先查看 `git -C {{challenge_path}} log --oneline`；需要恢复文件时运行 `{{root_name}}/bin/restore.sh <commit> {{challenge_path}}`
- 需要保留失败路线时，先用 `git -C {{challenge_path}} switch -c <branch>` 开分支，再继续实验

推荐节奏：
- 简单题通常 3 到 4 个 checkpoint
- 中等题通常 4 到 6 个 checkpoint
- 复杂 heap、seccomp、sandbox、复杂 web 链、复杂约束或多阶段 reverse/misc 题通常 5 到 8 个 checkpoint
- 第一个稳定环境、第一条稳定 primitive/oracle/约束模型、关键 leak、关键写入或 payload 成功时创建 checkpoint
- 高风险 pivot、破坏性 patch、heap metadata corruption、远程适配、路线切换前必须 checkpoint

完成前：
- 最终 exploit/solve 稳定且 flag 已确认后，创建 `flag-confirmed` 或同等语义 checkpoint
- 不要在未验证的猜测状态上创建听起来像已完成的 checkpoint

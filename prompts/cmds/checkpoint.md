checkpoint 策略：
- `{{root_name}}/scripts/challenge/init_challenge.sh {{challenge_path}}` 会在题目目录内执行 `git init`，并在首次初始化时创建 `[ckpt0 <题目名>]`
- 后续 checkpoint 必须通过 `{{root_name}}/scripts/challenge/checkpoint.sh <name> {{challenge_path}}` 创建；脚本会在题目目录 `.git/` 中提交 `[ckptN <name>]`
- checkpoint 是回滚锚点，不是自动保存；只在有意义的、可回滚的验证边界创建，不要把每次小改动都提交成 checkpoint
- 名称必须具体到“已验证对象 + 结果”，避免泛化名称；不要再使用 `primitive-confirmed`、`payload-confirmed`、`flag-confirmed` 这类信息量不足的名字
- 推荐命名格式：`<area>-<fact>-<state>`，例如 `routes-auth-map-done`、`canary-offset-leaked`、`libc-base-resolved`、`tcache-poison-write-works`、`admin-cookie-required-rejected`、`x402-payment-flow-mapped`
- 如果是 finding 审计，名称用 finding 编号或风险点命名，例如 `finding-01-replay-verified`、`finding-02-recipient-mismatch-rejected`、`x402-settle-race-poc-working`
- 创建 checkpoint 前先确认 `amds_state/cognition.json`、`exp.py`/`solve.py`/`wp.md` 等关键文件已写入当前结论，并运行 `{{root_name}}/scripts/state/state_docs.py render {{challenge_path}}`
- 创建后用 `git -C {{challenge_path}} log --oneline -3` 快速确认提交
- 路线失败或需要回退时，先查看 `git -C {{challenge_path}} log --oneline`；需要恢复文件时运行 `{{root_name}}/scripts/challenge/restore.sh <commit> {{challenge_path}}`
- 需要保留失败路线时，先用 `git -C {{challenge_path}} switch -c <branch>` 开分支，再继续实验

推荐节奏：
- 通常 5 到 8 个 checkpoint：按 leak、write、oracle、约束、认证绕过、RCE、远程适配等具体事实拆分
- 复杂 heap、seccomp、sandbox、复杂 web 链、复杂约束、多阶段 reverse/misc 或审计项目通常 8 到 12 个 checkpoint
- 第一个稳定环境、入口/路由/函数图、第一条具体 oracle/约束模型、每个关键 leak、每个关键写入、每个 finding PoC 成功时创建 checkpoint
- 高风险 pivot、破坏性 patch、heap metadata corruption、支付/状态机 race PoC、远程适配、路线切换前必须 checkpoint

完成前：
- 最终 exploit/solve/finding 稳定后，checkpoint 名称必须描述最终结果，例如 `remote-shell-verified`、`flag-string-verified`、`finding-01-replay-report-ready`、`audit-no-findings-scope-documented`
- 不要在未验证的猜测状态上创建听起来像已完成的 checkpoint

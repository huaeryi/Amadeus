# Amadeus

Amadeus 是一个面向 CTF 解题的轻量级 Agent 工作流工具箱。它把 challenge 目录、状态文档、checkpoint、工作流 prompt、pwn 运行入口、抓题脚本和 Web UI 统一起来，方便 Codex / Claude 在稳定上下文中推进解题。

当前重点支持 pwn，同时提供 web、crypto、reverse、misc 和 x402 审计工作流。

## 目录结构

```text
Amadeus/
├── bin/                 # amds 主入口
├── challenges/          # 每道题的独立工作区
├── prompts/             # 项目策略、命令模式 prompt、题型 prompt、学习规则
├── scripts/
│   ├── challenge/       # challenge 初始化、checkpoint、restore
│   ├── platform/        # NSSCTF / BUUCTF 抓题脚本
│   ├── pwn/             # pwn 运行入口
│   └── state/           # cognition/capability 状态文档工具
├── templates/           # challenge 初始化模板
└── webui/               # Challenge Console 前端和 Python API 服务
```

## 快速开始

初始化题目：

```bash
scripts/challenge/init_challenge.sh challenges/baby_tcache
scripts/challenge/init_challenge.sh challenges/defcon/baby_tcache
```

启动解题：

```bash
bin/amds baby_tcache
bin/amds pwn baby_tcache
bin/amds --workflow pwn defcon/baby_tcache
```

只做前处理：

```bash
bin/amds pre pwn baby_tcache
```

训练式引导解题：

```bash
bin/amds guide pwn baby_tcache
```

解后复盘：

```bash
bin/amds learn baby_tcache
bin/amds learn baby_tcache --session latest
```

## `amds` 用法

基本格式：

```bash
bin/amds [--runner codex|claude] [--policy strict|aggressive|none] [--mode solve|guide|pre|audit|fetch|exec|learn] [--workflow pwn|web|crypto|reverse|misc|x402] [--session ID|latest] <challenge|path|url> [-- agent_args...]
```

常用模式：

| 模式 | 说明 |
| --- | --- |
| `solve` | 标准解题模式，默认 workflow 为 `pwn`。 |
| `guide` | 引导式训练模式，会在关键分叉前要求短问题和判断。 |
| `pre` | 只做题目前处理、环境识别和基础事实记录。 |
| `audit` | 审计/挖洞模式，默认 workflow 为 `x402`。 |
| `fetch` | 抓取题面、附件和 metadata，不进入解题。 |
| `exec` | 先 fetch，再进入 solve。 |
| `learn` | 解后或阶段性完成后的复盘学习。 |

题型快捷方式：

```bash
bin/amds --web web_chal
bin/amds --crypto crypto_chal
bin/amds --reverse rev_chal
bin/amds --misc misc_chal
bin/amds audit x402 audit_target
```

切换 runner：

```bash
bin/amds --runner claude audit audit_target
bin/amds --claude audit x402 audit_target
```

`--` 后面的参数会原样传给底层 runner：

```bash
bin/amds --workflow pwn baby_tcache -- --search -m gpt-5.5
```

## Policy

`bin/amds` 默认使用 `strict` policy。默认模式适合训练、比赛复盘和需要避免题解污染的本地解题：禁止搜索 WP、公开 exploit、博客复现和 GitHub 解法，但允许基于当前题目附件、远程泄露或用户给出的信息做 libc/ld 匹配。

如果目标是尽快做出题目，可以显式切到 `aggressive`：

```bash
bin/amds --policy aggressive --workflow pwn baby_tcache -- --search
AMDS_POLICY=aggressive bin/amds pwn baby_tcache -- --search
```

`--policy aggressive` 只负责切换注入的项目策略；是否真的联网搜索仍取决于传给底层 runner 的能力和参数，例如 Codex 的 `--search`。

可选值：

| Policy | Prompt | 说明 |
| --- | --- | --- |
| `strict` | `prompts/cmds/policy.md` | 默认。禁止题解/WP/公开 exploit 搜索，但允许 libc/ld 匹配。 |
| `aggressive` | `prompts/cmds/policy_aggressive.md` | 允许搜索和使用 WP、公开 exploit、题名、flag 片段等外部线索，但要求记录来源并本地/远程验证。 |
| `none` | 无 | 不注入项目 policy。 |

`exec` 模式会把当前 policy 同时传给 fetch 和后续 solve。原来的 `.rules` 已迁移到 prompt policy 文件。

## 抓题

只抓题：

```bash
bin/amds fetch https://www.nssctf.cn/problem/131
bin/amds fetch --group defcon https://www.nssctf.cn/problem/131
bin/amds fetch 'https://buuoj.cn/challenges#刮开有奖'
```

抓题后自动解题：

```bash
bin/amds exec https://www.nssctf.cn/problem/131
bin/amds exec --workflow pwn https://www.nssctf.cn/problem/131
```

也可以直接使用平台脚本：

```bash
NSSCTF_COOKIE='...' scripts/platform/fetch_nssctf.py https://www.nssctf.cn/problem/131
BUUCTF_COOKIE='...' scripts/platform/fetch_buuctf.py 'https://buuoj.cn/challenges#刮开有奖'
```

本地 `.env` 可保存平台 cookie；shell 中已经 export 的值优先级更高。不要提交 cookie、token、flag 或 session 文件。

## Challenge 工作区

题目路径从 `challenges/` 起算：

```text
challenges/<challenge-name>/
challenges/<group>/<challenge-name>/
```

初始化后常见结构：

```text
challenges/baby_tcache/
├── amds_state/
│   ├── cognition.json
│   ├── COGNITION.md
│   ├── run.env
│   ├── exp_example.py
│   └── evidence/
├── exp.py
├── wp.md
└── <attachments>
```

约定：

- `amds_state/cognition.json` 是机器可读状态源。
- `amds_state/COGNITION.md` 由 `scripts/state/state_docs.py` 生成，不建议手写。
- 命令输出、调试日志、截图和脚本结果放入 `amds_state/evidence/`。
- 每个 challenge 目录是独立 git 仓库，checkpoint 就是该目录内的 commit。
- pwn 运行配置优先读取 `amds_state/run.env`，同时兼容旧位置 `.pwnrun`。

更新状态文档：

```bash
scripts/state/state_docs.py render challenges/baby_tcache
scripts/state/capabilities.py validate challenges/baby_tcache
```

## Checkpoint

创建 checkpoint：

```bash
scripts/challenge/checkpoint.sh env-profiled challenges/baby_tcache
scripts/challenge/checkpoint.sh libc-base-resolved challenges/baby_tcache
```

恢复 checkpoint：

```bash
scripts/challenge/restore.sh latest challenges/baby_tcache
scripts/challenge/restore.sh <commit-hash> challenges/baby_tcache
```

建议只在稳定里程碑创建 checkpoint，例如环境确认、漏洞确认、泄露可复现、地址解析完成、关键 primitive 可用、远程适配成功。

## pwn 运行

`scripts/pwn/run_pwn.sh` 统一处理 local、remote、patched 和 info：

```bash
scripts/pwn/run_pwn.sh challenges/baby_tcache info
scripts/pwn/run_pwn.sh challenges/baby_tcache local
scripts/pwn/run_pwn.sh challenges/baby_tcache remote 127.0.0.1 5000
scripts/pwn/run_pwn.sh challenges/baby_tcache patched
```

它会读取 `amds_state/run.env`，自动检测 binary、patched binary、libc 和 ld，并导出：

```text
PWN_MODE, PWN_CHAL_DIR, PWN_EXP, PWN_BIN, PWN_PATCHED_BIN,
PWN_ACTIVE_BIN, PWN_LIBC, PWN_LD, PWN_HOST, PWN_PORT,
PWN_LOCAL_ARGS, PWN_REMOTE_ARGS, PWN_LIB_DIR
```

新 exploit 建议读取这些 `PWN_*` 环境变量，让 local、remote 和 patched 模式共享同一个 `exp.py`。

## Web UI

启动：

```bash
webui/start.sh
```

默认地址：

```text
http://127.0.0.1:9999/
```

Web UI 可用于浏览题目、创建并初始化 challenge、查看核心文档、预览文件、查看 `run_pwn.sh info`、创建/恢复 checkpoint 和查看 checkpoint graph。

## 推荐流程

1. `scripts/challenge/init_challenge.sh challenges/<name>` 初始化题目。
2. 放入附件，运行 `scripts/pwn/run_pwn.sh challenges/<name> info` 确认配置。
3. 使用 `bin/amds pre ...` 做前处理。
4. 使用 `bin/amds solve ...` 或 `bin/amds guide ...` 解题。
5. 在关键稳定节点运行 `scripts/challenge/checkpoint.sh <name> challenges/<name>`。
6. 将证据放入 `amds_state/evidence/`，最终 exploit 写入 `exp.py`，writeup 写入 `wp.md`。
7. 解后运行 `bin/amds learn <name>` 做复盘。

## TODO

- [ ] Plan 模式：正式 solve 前生成可审阅计划。
- [ ] 前端展示 checkpoint evidence的可视化
- [ ] 更完整的平台抓取适配

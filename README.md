# Amadeus

Amadeus 是一个封装 Codex 的轻量级 CTF 工作台, 主要负责把题目目录、状态文档、checkpoint、执行入口和前端管理面板统一起来，让 agent 解题时有稳定的上下文和可回滚的工作流。

当前重点支持 pwn，同时已经预留并接入了 web、crypto、reverse、misc 的 workflow prompt。

## 整体结构

```text
Amadeus/
├── bin/                 # 命令行入口和工作流脚本
├── prompts/             # amds 注入给 Codex 的 workflow prompt
├── templates/           # 初始化题目时复制的状态模板
├── script/              # 平台题目抓取辅助脚本
├── webui/               # Challenge Console 前端和 Python API 服务
└── challenges/          # 每道题的独立工作目录
```

核心文件：

- `bin/amds`：Codex 启动器，负责 fetch / solve / exec 三种模式和 workflow prompt 渲染。
- `bin/init_challenge.sh`：初始化题目目录，创建 `STATE.md`、`FACTS.md`、`metadata.json`、`.ctf-files`、`.pwnrun`、`checkpoints/`、`attempts/`。
- `bin/checkpoint.sh`：按 `.ctf-files` 保存一次具名 checkpoint，并写入 checkpoint graph。
- `bin/restore.sh`：从 checkpoint 恢复被跟踪文件。
- `bin/run_pwn.sh`：pwn 题统一运行入口，支持 local / remote / patched / info。
- `prompts/*.md`：不同题型的 agent 工作流约束。
- `templates/STATE.md`：当前阶段、下一步、失败分支、checkpoint 计划。
- `templates/FACTS.md`：只记录已经验证的事实。
- `webui/server.py`：零依赖 Python 后端，提供静态页面和 JSON API。

## 快速开始

初始化题目：

```bash
bin/init_challenge.sh challenges/baby_tcache
```

启动 pwn 解题工作流：

```bash
bin/amds --workflow pwn baby_tcache
```

抓题但不解题：

```bash
bin/amds fetch https://www.nssctf.cn/problem/131
bin/amds fetch 'https://buuoj.cn/challenges#刮开有奖'
```

抓题后自动进入 solve：

```bash
bin/amds exec https://www.nssctf.cn/problem/131
bin/amds exec --workflow pwn https://www.nssctf.cn/problem/131
```

本地、远程和 patched 运行 pwn exploit：

```bash
bin/run_pwn.sh challenges/baby_tcache
bin/run_pwn.sh challenges/baby_tcache remote 127.0.0.1 5000
bin/run_pwn.sh challenges/baby_tcache patched
bin/run_pwn.sh challenges/baby_tcache info
```

## amds 工作流

`bin/amds` 是对 `codex` 的薄封装，会在 Amadeus 的上级目录启动 Codex，并把题目路径、workflow prompt 和附加说明一起传入。

支持模式：

- `solve`：默认模式，解析 `challenges/<name>`，加载 `prompts/<workflow>.md`。
- `fetch`：只获取题面、附件、metadata 和环境信息，不进入解题。
- `exec`：先 fetch，再根据题目类别或显式参数进入 solve。

支持 workflow：

- `pwn`
- `web`
- `crypto`
- `reverse`
- `misc`

常用写法：

```bash
bin/amds --mode solve --workflow pwn newnote
bin/amds --web web_chal
bin/amds --crypto crypto_chal
bin/amds --reverse rev_chal
bin/amds --misc misc_chal
bin/amds --workflow pwn newnote --append "远程地址是 node4.example:30000"
bin/amds --workflow pwn newnote --dry-run
bin/amds --workflow pwn newnote -- --search -m gpt-5.5
```

兼容写法：

```bash
bin/amds pwn newnote
bin/amds newnote
```

fetch helper 会读取本地 `.env`，但 shell 中已经 export 的值优先级更高。敏感 cookie 只放本地环境，不提交到仓库。

```bash
NSSCTF_COOKIE='...' script/fetch_nssctf.py https://www.nssctf.cn/problem/131
BUUCTF_COOKIE='...' script/fetch_buuctf.py 'https://buuoj.cn/challenges#刮开有奖'
```

## Challenge 目录约定

每个题目目录都是一个独立 workspace，典型结构如下：

```text
challenges/baby_tcache/
├── STATE.md             # 解题状态和下一步
├── FACTS.md             # 已确认事实
├── metadata.json        # 平台、题目、标签、附件信息
├── .ctf-files           # checkpoint 跟踪清单
├── .pwnrun              # pwn 运行配置
├── exp.py               # 最终 exploit 或 solve 脚本
├── wp.md                # 最终 writeup
├── attempts/            # 失败分支和临时路线记录
└── checkpoints/         # checkpoint 快照和图数据
```

约定：

- `FACTS.md` 只写已经被文件、运行结果、调试器或 exploit 输出验证的事实。
- `STATE.md` 写当前判断、下一步、候选路线、失败路线和开放问题。
- `.ctf-files` 每行一个相对文件路径，checkpoint 只保存这些文件。
- `attempts/` 用于记录失败路线，避免 agent 在脏状态上反复修补。
- pwn 题优先让 `exp.py` 读取 `run_pwn.sh` 导出的 `PWN_*` 环境变量。

## Checkpoint

Checkpoint 是这次工作流的核心增量之一。它用于保存已经确认的稳定里程碑，方便在尝试高风险利用路线、切换思路或适配远程前回滚。

创建 checkpoint：

```bash
bin/checkpoint.sh env-ok challenges/baby_tcache
bin/checkpoint.sh primitive-confirmed challenges/baby_tcache
bin/checkpoint.sh libc-base-confirmed challenges/baby_tcache
```

恢复 checkpoint：

```bash
bin/restore.sh latest challenges/baby_tcache
bin/restore.sh 20260519-120000-primitive-confirmed challenges/baby_tcache
```

实现细节：

- 每个 checkpoint 位于 `checkpoints/<timestamp>-<name>/`。
- `files/` 下保存 `.ctf-files` 中列出的文件快照。
- `META.txt` 保存名称、创建时间、父 checkpoint 等元数据。
- `checkpoints/latest` 指向最新 checkpoint。
- `checkpoints/.amadeus-head` 记录当前 head。
- `checkpoints/.checkpoint-graph.json` 记录 checkpoint 节点和父子关系，供前端画图。

推荐策略：

- checkpoint 是回滚锚点，不是 autosave。
- 名称按已经确认的事实或能力命名，比如 `env-ok`、`offset-confirmed`、`canary-leaked`、`arb-write-confirmed`、`orw-working`、`flag-confirmed`。
- 简单栈溢出或格式化字符串题通常 3 到 4 个 checkpoint。
- 中等栈、格式化字符串或堆题通常 4 到 6 个 checkpoint。
- 复杂 heap、seccomp、sandbox 或 kernel 题通常 5 到 8 个 checkpoint。
- 在第一次大型 heap metadata corruption、`setcontext`、FSOP、ret2dlresolve、SROP、切换 exploit 路线、适配远程前创建 checkpoint。

## 前端显示

前端是 `webui/` 下的 Challenge Console，定位是题目管理和状态可视化，不是完整 IDE。

启动：

```bash
python3 webui/server.py
```

或：

```bash
./webui/start.sh
```

默认地址：

```text
http://127.0.0.1:9999/
```

当前前端能力：

- 题目列表、搜索和基础状态展示。
- 创建题目并自动初始化。
- 编辑 `STATE.md`、`FACTS.md`、`metadata.json`、`.ctf-files`、`.pwnrun`。
- 展示 `run_pwn.sh info` 的解析结果。
- 创建和恢复 checkpoint。
- 显示 checkpoint graph，包括 latest / head 标记。
- 预览顶层文件、`attempts/` 记录和二进制 hex dump。
- 通过文件浏览器查看题目目录中的嵌套文件。

主要 API：

- `GET /api/challenges`
- `GET /api/challenges/<name>`
- `POST /api/challenges`
- `POST /api/challenges/<name>/init`
- `GET /api/challenges/<name>/run-info`
- `PUT /api/challenges/<name>/document?name=STATE.md`
- `POST /api/challenges/<name>/checkpoints`
- `POST /api/challenges/<name>/restore`
- `GET /api/challenges/<name>/file?path=exp.py`

后台运行示例：

```bash
nohup python3 webui/server.py --host 0.0.0.0 --port 9999 >/tmp/amadeus-webui.log 2>&1 &
```

## Skills 和 MCP

Amadeus 的设计前提是和 Codex skills / MCP 配合使用。仓库本身只负责工作流和文件组织，具体解题能力由 skills、调试器和本地工具提供。

推荐 skills：

- `solve-challenge`：不确定题型时作为总入口，先做分类和调度。
- `ctf-pwn`：pwn 主技能，覆盖栈、格式化字符串、heap、ROP、ret2libc、seccomp、sandbox 等。
- `ctf-web`：web 题主技能，覆盖路由、鉴权、模板、数据库、上传、SSRF、SSTI、SQLi、XSS、JWT 等。
- `ctf-crypto`：crypto 题主技能，覆盖 RSA、ECC、格、PRNG、padding oracle、签名、ZKP 等。
- `ctf-reverse`：reverse 主技能，覆盖 ELF、APK、WASM、VM、混淆、符号执行、约束求解等。
- `ctf-misc`：misc 主技能，覆盖编码、取证、流量、音频、图片、jail、z3 等。
- `ctf-writeup`：解完后整理 `wp.md`。
- `exploit-chain-planning`：复杂利用链拆解、假设验证和分支规划。

推荐 MCP / 外部工具：

- `pwndbg-mcp`：复杂 pwn 题优先使用，适合读取寄存器、栈、堆、bins、tcache、vmmap、断点和崩溃现场。
- 本地 `gdb` / `pwndbg`：基础动态调试。
- `checksec`、`file`、`readelf`、`objdump`、`ROPgadget`：pwn / reverse 基础分析。
- `patchelf` 和题目自带 `ld` / `libc`：复现远程运行环境。
- `SageMath`、`z3`、`fplll`、`RsaCtfTool`：crypto / misc 求解。
- `tshark`、`binwalk`、`exiftool`、`ffmpeg`、`sox`：misc / forensics。

pwn 题建议流程：

1. `bin/init_challenge.sh <challenge_dir>`
2. 读取附件并确认 binary、libc、ld、patched binary、`exp_template.py`
3. 用 `FACTS.md` 固化事实，用 `STATE.md` 规划路线
4. 用 `bin/run_pwn.sh <challenge_dir> info` 检查 `.pwnrun`
5. 在稳定 primitive 或 leak 后创建 checkpoint
6. 高风险 pivot 前再创建 checkpoint
7. 最终产出 `exp.py` 和 `wp.md`

## run_pwn.sh

`run_pwn.sh` 为 pwn 题提供统一入口，并导出一组标准环境变量：

- `PWN_MODE`
- `PWN_CHAL_DIR`
- `PWN_EXP`
- `PWN_BIN`
- `PWN_PATCHED_BIN`
- `PWN_ACTIVE_BIN`
- `PWN_LIBC`
- `PWN_LD`
- `PWN_HOST`
- `PWN_PORT`
- `PWN_LOCAL_ARGS`
- `PWN_REMOTE_ARGS`

默认兼容常见 pwntools 写法：

- local：`python3 exp.py`
- remote：`python3 exp.py r <host> <port>`

新 exploit 建议读取 `PWN_*`，这样 local、remote 和 patched 模式可以共享同一个 `exp.py`。

libc 策略：

- 优先使用当前题目提供的 `libc` 和 `ld`。
- 优先用 `patchelf`、题目 loader 或 `run_pwn.sh patched` 复现环境。
- 不要在未确认时静默使用系统 libc。
- 不要从其他 challenge、历史题目、下载缓存或工具缓存复制 libc / ld。
- 没有 libc 时，先泄露符号，再根据泄露结果匹配远程 libc。

## TODO

- [ ] Plan 模式：在正式 solve 前生成可审阅计划，支持用户确认后再执行。
- [ ] subagent 集成：把 recon、动态调试、exploit 编写、writeup 整理拆成并行子任务。
- [ ] Checkpoint diff：前端展示 checkpoint 之间的文件差异。
- [ ] Checkpoint branch：更明确地支持多分支路线和非线性回滚。 (一个想法是git)
- [ ] 前端功能完善，Web日志
- [ ] 更完整的平台抓取：扩展 NSSCTF / BUUCTF 以外的平台适配。


# Amadeus

一个封装 Codex 的轻量级 CTF agent, 主要负责把题目目录、状态文档、checkpoint、执行入口和前端管理面板统一起来，让 agent 解题时有稳定的上下文和可回滚的工作流。

当前重点支持 pwn，同时已经预留并接入了 web、crypto、reverse、misc、x402 的 workflow prompt。

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

- `bin/amds`：Codex 启动器，负责 fetch / solve / exec / learn 和 workflow prompt 渲染。
- `bin/init_challenge.sh`：初始化题目目录，创建 `cognition.json`、生成的 `COGNITION.md`、`evidence/`、`.pwnrun`，并在题目目录内创建 git 初始 checkpoint。
- `bin/state_docs.py`：初始化、校验和渲染 `cognition.json`；`COGNITION.md` 只能由它生成。
- `bin/capabilities.py`：校验和渲染 `cognition.json.capabilities`；`COGNITION.md` 只能由它生成。
- `bin/checkpoint.sh`：在题目目录 git 中创建具名 checkpoint commit。
- `bin/restore.sh`：从 git checkpoint commit 恢复 tracked files。
- `bin/run_pwn.sh`：pwn 题统一运行入口，支持 local / remote / patched / info。
- `prompts/cmds/*.md`：solve / guide / fetch / learn / checkpoint 等命令入口和通用策略。
- `prompts/skills/*.md`：pwn / web / crypto / reverse / misc / x402 等题型 workflow。
- `prompts/cmds/learn.md`：post-solve 反思和学习入口。
- `prompts/learn/`：各题型的长期学习规则、反思清单和学习侧重点。
- `prompts/learn/LEARNING_LOG.md`：每次 `amds learn` 的长期学习变更日志。
- `templates/cognition.json`：统一保存题目信息、facts、state 和 capabilities。
- `webui/server.py`：零依赖 Python 后端，提供静态页面和 JSON API。

## 快速开始

初始化题目：

```bash
bin/init_challenge.sh challenges/baby_tcache
bin/init_challenge.sh challenges/defcon/baby_tcache
```

启动 pwn 解题工作流：

```bash
bin/amds --workflow pwn baby_tcache
bin/amds pwn defcon/baby_tcache
```

启动带提问和复盘的主动学习工作流：

```bash
bin/amds guide pwn baby_tcache
```

抓题但不解题：

```bash
bin/amds fetch https://www.nssctf.cn/problem/131
bin/amds fetch --group defcon https://www.nssctf.cn/problem/131
bin/amds fetch 'https://buuoj.cn/challenges#刮开有奖'
```

抓题后自动进入 solve：

```bash
bin/amds exec https://www.nssctf.cn/problem/131
bin/amds exec --workflow pwn https://www.nssctf.cn/problem/131
```

对已完成或阶段性完成的题目做反思学习：

```bash
bin/amds learn baby_tcache
bin/amds learn baby_tcache --session latest
bin/amds learn baby_tcache --session 20260522-143012-pwn
```

本地、远程和 patched 运行 pwn exploit：

```bash
bin/run_pwn.sh challenges/baby_tcache
bin/run_pwn.sh challenges/baby_tcache remote 127.0.0.1 5000
bin/run_pwn.sh challenges/baby_tcache patched
bin/run_pwn.sh challenges/baby_tcache info
```

## amds 工作流

`bin/amds` 是对 `codex` 的薄封装，会在 Amadeus 根目录启动 Codex，并把题目路径、workflow prompt 和附加说明一起传入。

基本格式：

```bash
bin/amds [--mode solve|guide|fetch|exec|learn] [--workflow pwn|web|crypto|reverse|misc|x402] [--session ID|latest] <challenge|path|url> [-- codex_args...]
```

### solve

`solve` 解析 `challenges/<name>`、`challenges/<group>/<name>` 或 challenge 路径，先加载 `prompts/cmds/solve.md`，再根据 `--workflow` 加载 `prompts/skills/<workflow>.md`，最后追加 `prompts/cmds/checkpoint.md`。默认 workflow 是 `pwn`。

```bash
bin/amds --mode solve --workflow pwn newnote
bin/amds --workflow pwn newnote
bin/amds --workflow pwn defcon/newnote
bin/amds --workflow x402 audit_target
bin/amds --group defcon --workflow pwn newnote
bin/amds pwn newnote
bin/amds newnote
```

### guide

`solve` 先读 `prompts/cmds/solve.md`，`guide` 先读 `prompts/cmds/guide.md`。CTF 方向由 `--workflow` 决定，例如 `--workflow pwn` 会再加载 `prompts/skills/pwn.md`；checkpoint 规则统一追加 `prompts/cmds/checkpoint.md`。

```bash
bin/amds guide pwn newnote
bin/amds guide pwn defcon/newnote
bin/amds guide --workflow pwn newnote
bin/amds --mode guide --workflow pwn newnote
```

题型快捷参数：

```bash
bin/amds --web web_chal
bin/amds --crypto crypto_chal
bin/amds --reverse rev_chal
bin/amds --misc misc_chal
```

常用附加参数：

```bash
bin/amds --workflow pwn newnote --append "远程地址是 node4.example:30000"
bin/amds --workflow pwn newnote --dry-run
bin/amds --workflow pwn newnote -- --search -m gpt-5.5
```

主动学习模式：

```bash
bin/amds guide pwn newnote
```

`guide` 使用 `prompts/cmds/guide.md` 作为入口：agent 在关键分叉前会先让你判断，要求解释命令输出如何改变结论，并在 `cognition.json.state` 维护 `your_turn` 问题，渲染到 `COGNITION.md`，在 `wp.md` 维护 `Learning checkpoints`。比赛冲刺时用 `solve`，训练和复盘时用 `guide`。

### fetch

`fetch` 只获取题面、附件、metadata 和环境信息，不进入解题。

```bash
bin/amds fetch https://www.nssctf.cn/problem/131
bin/amds fetch --group defcon https://www.nssctf.cn/problem/131
bin/amds --mode fetch https://www.nssctf.cn/problem/131
bin/amds fetch 'https://buuoj.cn/challenges#刮开有奖'
```

### exec

`exec` 先 fetch，再根据题目类别进入 solve；也可以显式指定 solve workflow。

```bash
bin/amds exec https://www.nssctf.cn/problem/131
bin/amds exec --group defcon https://www.nssctf.cn/problem/131
bin/amds --mode exec https://www.nssctf.cn/problem/131
bin/amds exec --workflow pwn https://www.nssctf.cn/problem/131
bin/amds --mode exec --workflow web https://example.com/challenge
```

### learn

`learn` 对已完成或阶段性完成的题目做 post-solve 学习：生成或更新 `REFLECTION.md`，维护 `prompts/learn/<category>_learning.md`，并追加 `prompts/learn/LEARNING_LOG.md`。

不指定 session 时，只从 challenge 目录文件学习：

```bash
bin/amds learn baby_tcache
bin/amds --mode learn baby_tcache
```

指定 session 时，从 challenge 文件和 session 一起学习；challenge 文件仍是事实基准，session 只作为过程证据：

```bash
bin/amds learn baby_tcache --session latest
bin/amds learn baby_tcache --session 20260522-143012-pwn
```

fetch helper 会读取本地 `.env`，但 shell 中已经 export 的值优先级更高。敏感 cookie 只放本地环境，不提交到仓库。

```bash
NSSCTF_COOKIE='...' script/fetch_nssctf.py https://www.nssctf.cn/problem/131
NSSCTF_COOKIE='...' script/fetch_nssctf.py --group defcon https://www.nssctf.cn/problem/131
BUUCTF_COOKIE='...' script/fetch_buuctf.py 'https://buuoj.cn/challenges#刮开有奖'
```

## Challenge 目录约定

每个题目目录都是一个独立 workspace，典型结构如下：

```text
challenges/baby_tcache/
├── cognition.json        # 机器可读 metadata/facts/state/capabilities source of truth
├── COGNITION.md          # 从 cognition.json 生成的人类可读视图
├── evidence/            # 命令输出、调试日志、截图、脚本结果等证据
├── .pwnrun              # pwn 运行配置
├── exp.py               # 最终 exploit 或 solve 脚本
└── wp.md                # 最终 writeup
```

也可以按比赛分组：

```text
challenges/defcon/baby_tcache/
```

分组目录只是容器，真正的 challenge 目录仍然是包含 `cognition.json` 等文件的叶子目录。

约定：

- `cognition.json.facts` 只写已经被文件、运行结果、调试器或 exploit 输出验证的事实；`COGNITION.md` 是生成视图，不要手写。
- `cognition.json.state` 写当前判断、下一步、候选路线、失败路线和开放问题；`COGNITION.md` 是生成视图，不要手写。
- `cognition.json.capabilities` 写当前已获得、观察到、猜测中、被阻塞、作为目标的能力；所有 capability 必须有 env 和 evidence。
- 后续命令输出、调试日志、截图、脚本结果等证据文件统一放进题目目录的 `evidence/`，并在 `cognition.json` 中用相对路径引用。
- `COGNITION.md` 是生成文件，不要手写；更新 JSON 后运行 `bin/state_docs.py render <challenge_dir>`。
- checkpoint 使用题目目录内的 git commit；重要解题文件清单放在 `cognition.json.metadata.tracked_files`。
- pwn 题优先让 `exp.py` 读取 `run_pwn.sh` 导出的 `PWN_*` 环境变量。

## Capabilities

`cognition.json.capabilities` 记录 exploit 过程中已经获得、观察到、猜测中、被阻塞、正在作为目标的能力，供后续 planner 选择下一步 exploit target。`cognition.json` 是 source of truth，`COGNITION.md` 只是生成视图。

```bash
bin/capabilities.py init challenges/baby_tcache
bin/capabilities.py validate challenges/baby_tcache
bin/capabilities.py render challenges/baby_tcache
```

约束：

- 每个 capability 必须有 `env`，可用值包括 `local`、`native`、`docker`、`patched`、`remote`。
- `local` verified 不等于 `remote` verified；跨环境迁移必须重新验证。
- 每个 capability 必须有 evidence，至少包含简短说明，并提供 artifact 或 command；artifact 优先指向 `evidence/` 下的相对路径。
- `verified` 必须有 evidence 和 verification。
- `blocked` 必须有 blocked_by，并在 reason 或 summary 中说明阻塞原因。
- 更新 `cognition.json` 后运行 `bin/state_docs.py render <challenge_dir>`，不要手写 `COGNITION.md`。

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
bin/restore.sh <commit-hash> challenges/baby_tcache
```

实现细节：

- 每个 checkpoint 是题目目录 git 中的一个 commit。
- `init_challenge.sh` 首次初始化时创建 `[ckpt0 <题目名>]`。
- `checkpoint.sh <name>` 后续创建 `[ckptN <name>]`。
- webui 从 `git log` 读取 checkpoint 列表和父子关系。
- `restore.sh <commit>` 使用 git 从指定 checkpoint 恢复 tracked files。

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
- 编辑 `cognition.json`、`.pwnrun`；保存 JSON 后自动渲染对应 Markdown。
- 展示 `run_pwn.sh info` 的解析结果。
- 创建和恢复 checkpoint。
- 基于 git commit 历史显示 checkpoint graph，包括 latest / head 标记。
- 预览顶层文件和二进制 hex dump。
- 通过文件浏览器查看题目目录中的嵌套文件。

主要 API：

- `GET /api/challenges`
- `GET /api/challenges/<name>` 或 URL 编码后的 `<group>/<name>`
- `POST /api/challenges`
- `POST /api/challenges/<name>/init`
- `GET /api/challenges/<name>/run-info`
- `PUT /api/challenges/<name>/document?name=cognition.json`
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
3. 用 `cognition.json.facts` 固化事实，用 `cognition.json.state` 规划路线，并渲染 `COGNITION.md`
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
- [ ] subagent 集成
- [ ] Checkpoint diff：前端展示 git checkpoint 之间的文件差异。
- [ ] Checkpoint branch：更明确地支持多分支路线和非线性回滚。
- [ ] 前端功能完善，Web日志
- [ ] 更完整的平台抓取：扩展 NSSCTF / BUUCTF 以外的平台适配。

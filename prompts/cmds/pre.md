预处理 `{{challenge_path}}` 这道 CTF 题，只完善题目环境、基础信息和初步思路，不开始完整解题。

本次 CTF 方向由 `--workflow {{workflow}}` 决定；如果题目材料明显不属于该方向，把证据和 pivot 原因写入 `amds_state/cognition.json.state`，再继续按实际材料做环境整理。

先读：
- `{{root_name}}/AGENTS.md`
- 如果存在 `{{root_name}}/prompts/learn/{{workflow}}_learning.md`，只读取其中和环境确认、常见坑有关的内容

通用入口要求：
1. 在题目目录内工作；当前工作目录应为 `{{challenge_path}}`，不要在 `{{root_name}}` 根目录创建、删除或修改题目产物
2. 如果 `amds_state/cognition.json` 不存在，先运行 `{{root_name}}/scripts/challenge/init_challenge.sh {{challenge_path}}`
3. 识别题面、附件、源码、脚本、二进制、容器文件、远程地址和运行依赖
4. 保存关键命令输出到 `{{challenge_path}}/amds_state/evidence/`，只把摘要和相对路径写入 `amds_state/cognition.json`
5. 已确认事实写入 `amds_state/cognition.json.facts`
6. 初步判断、候选方向、开放问题和下一步写入 `amds_state/cognition.json.state`
7. 更新后运行 `{{root_name}}/scripts/state/state_docs.py render {{challenge_path}}`

工作范围：
1. 补齐题目目录结构，确认附件是否已解压，保留原始压缩包
2. 记录文件类型、架构、hash、入口文件、运行方式和依赖
3. 如果是 pwn 题，运行 `file`、`checksec`，识别主 binary、libc、ld，并维护 `amds_state/run.env`
4. 如果 pwn 题提供 libc/ld，优先用当前题目目录内文件尝试 `patchelf` 生成 patched binary；不要从其他题目目录复制 libc/ld
5. 如果缺少 ld 但已有 libc，可以根据当前 libc 版本查找或反推匹配 ld；记录来源、版本和验证结果，不要搜索题解、WP、公开 exploit 或 GitHub 解法
6. 如果是 web/reverse/crypto/misc，做对应的最小环境确认：依赖安装提示、启动命令、输入输出样例、关键文件和初步观察
7. 对目标程序或服务做少量 smoke test，确认能否本地运行；不要长时间 fuzz 或进入完整 exploit/solve
8. 给出 2 到 4 条初步思路，每条写清依赖的事实、还需要验证什么、下一条建议命令
9. 如果环境缺失或验证失败，保留失败证据，并写清缺什么、如何手工补

禁止事项：
- 不要访问或搜索任何 WP、题解、公开 exploit、博客复现或 GitHub 解法
- 不要开始写完整 exploit、solve 脚本或最终 writeup；除非只是创建最小运行模板或修正运行配置
- 不要把 Cookie、token、session、Authorization 等敏感值写入文件、日志或最终输出
- 不要伪造 checksec、patch、运行结果或远程验证成功
- 不要把未确认推测写成事实

完成标准：
- `amds_state/cognition.json` 和 `amds_state/COGNITION.md` 已更新
- 关键基础信息和失败证据保存到 `amds_state/evidence/`
- pwn 题的 `amds_state/run.env` 尽量可用，`{{root_name}}/scripts/pwn/run_pwn.sh {{challenge_path}} info` 能展示合理解析结果
- 最终汇报包含：题目目录、识别出的关键文件、保护/运行环境摘要、patch 状态、初步思路和未完成事项

项目策略：aggressive

本策略目标是优先做出题目、快速拿到可验证结果。允许使用外部资料，但必须把外部来源和本地验证区分清楚。

## Allowed External Search

- 可以搜索题目名、binary 名、服务 URL、出题方、报错信息、flag 片段、附件 hash、关键函数名和其他题目特征。
- 可以阅读公开 WP、博客复现、GitHub/Gist exploit、论坛帖子、paste 内容、比赛 writeup 和平台公开解题资料。
- 可以使用互联网来源的 offset、gadget、payload、利用路线、libc/ld 匹配结果、Docker/部署线索和环境复现信息作为候选方案。
- 可以使用 `libc.rip` 等在线服务匹配 libc 版本、查询符号 offset；已知 libc 时可以查找或反推匹配 ld。

## Evidence Discipline

- 外部资料只能作为 candidate，不是最终事实；关键结论必须尽量在当前 challenge 目录、目标 binary、本地运行、调试器或远程靶机上复现。
- 使用外部 WP/exploit/offset 时，在 `amds_state/cognition.json.state` 或 `amds_state/evidence/` 记录来源 URL、采用了什么、哪些部分已本地验证。
- 不要把外部代码直接当作最终 `exp.py`；先改成当前题目目录、当前远程参数和 `run_pwn.sh`/`PWN_*` 兼容的版本。
- 如果外部方案和本地验证冲突，以本地验证为准，并记录冲突点。

## Safety And Scope

- 仍然只攻击当前授权的 CTF challenge service，不要扩展到非授权目标、真实账号、真实资金或生产系统。
- 不要提交 cookie、token、session、Authorization、真实 flag 或个人敏感信息。
- 允许快速试错，但重要阶段仍要保存 evidence 和 checkpoint，避免把一次偶然成功误判为稳定解。

## Output Rule

- 最终汇报要明确说明是否使用了 aggressive policy。
- 如果使用了外部资料，列出关键来源类别或 URL，并说明最终 exploit/解法已通过哪些本地或远程验证。

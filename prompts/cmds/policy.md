项目策略：

这个仓库默认用于本地优先的 CTF 解题/审计工作流。除非用户对当前任务明确放宽限制，否则按以下策略执行。

## Anti-Cheat

- 不要使用 web search、web browsing 或外部在线 writeup 来解决本仓库中的 CTF challenge。
- 不要在互联网上搜索题目名、binary 名、服务 URL、出题方、已知 flag 片段或题目特征字符串。
- 不要获取公开 writeup、exploit 仓库、博客复现、GitHub 解法、论坛帖子、paste 站内容或平台 writeup API。
- 不要把互联网来源的 exploit 代码、gadget chain、攻击路线或题解结论当作当前题目的有效证据。

## Allowed Sources

- 可以使用当前 challenge 目录中已经存在的文件，包括附件、binary、patched binary、libc、ld、`exp_template.py`、`exp.py`、`wp.md`、`attempts/`、`checkpoints/` 和 `amds_state/`。
- 可以使用本地工具输出、调试器结果、脚本运行结果、当前题目服务返回值和远程靶机交互结果作为证据。
- 不要从其他本地 challenge、历史已解题、下载缓存、工具缓存或无关 workspace 直接复制/复用 libc、ld 或 exploit 证据。
- 本地历史材料可以作为 workflow/reference context，但不能作为当前题目提供的 libc/ld 或 exploit 成功证据。
- 可以使用 `libc.rip` 等在线 libc fingerprint/offset lookup 服务匹配 libc 版本、查询符号 offset，前提是输入来自当前题目附件、当前远程泄露或用户明确提供的信息。
- 如果已知当前题目的 libc 版本或 libc 文件，可以据此查找/反推匹配的 ld，并把来源、版本和验证结果写入 evidence；不要从无关 challenge 静默复制 ld。
- 题目要求远程验证时，可以连接目标 challenge service 本身。

## Operating Rule

- 默认先做 local-first analysis；结论必须基于当前 workspace、本地工具输出和直接验证。
- 如果题目看起来需要互联网资料，先区分是允许的 libc/ld 版本匹配，还是禁止的题解/公开 exploit 搜索；后者不要自行搜索。
- 如果用户明确要求放宽限制，只对当前任务放宽，并在最终汇报中说明使用了哪些外部来源。

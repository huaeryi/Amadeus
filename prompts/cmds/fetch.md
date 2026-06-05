帮我把这个 CTF 题目爬取到 `{{root_name}}/challenges/{{challenge_group_prefix}}`：

`{{target_url}}`

这是 fetch-only 任务，不要开始解题。

先读：
- `{{root_name}}/AGENTS.md`

平台适配：
- 如果 URL 属于 NSSCTF，例如 `https://www.nssctf.cn/problem/<id>`，优先直接运行 `{{root_name}}/scripts/platform/fetch_nssctf.py {{group_option}}'{{target_url}}'`
- 如果 NSSCTF 附件需要登录态，使用环境变量 `NSSCTF_COOKIE` 传入 Cookie，例如 `NSSCTF_COOKIE='...' {{root_name}}/scripts/platform/fetch_nssctf.py {{group_option}}'{{target_url}}'`
- NSSCTF 脚本执行后，检查输出、challenge 目录、`description.md`、`amds_state/cognition.json`、生成的 `amds_state/COGNITION.md` 和附件文件；缺什么再手工补，不要重复实现脚本已有逻辑
- 如果 URL 属于 BUUCTF/BUUOJ，例如 `https://buuoj.cn/challenges#<title>`，优先直接运行 `{{root_name}}/scripts/platform/fetch_buuctf.py {{group_option}}'{{target_url}}'`
- BUUCTF 通常需要登录态才能读取 challenge API 和附件；使用环境变量 `BUUCTF_COOKIE` 或 `BUUOJ_COOKIE` 传入 Cookie，例如 `BUUCTF_COOKIE='...' {{root_name}}/scripts/platform/fetch_buuctf.py {{group_option}}'{{target_url}}'`
- BUUCTF 脚本执行后，检查输出、challenge 目录、`description.md`、`amds_state/cognition.json`、生成的 `amds_state/COGNITION.md` 和附件文件；如果提示缺少登录态或附件失败，把失败状态保留在文件中，不要伪造成功
- 如果不是 NSSCTF/BUUCTF URL，按下面通用流程由 agent 自己分析页面和附件下载方式

工作要求：
1. 只抓取题面、附件、公开元数据和题目运行环境信息
2. 不要访问或搜索任何 WP、题解、公开 exploit、博客复现、GitHub 解法或平台 writeup API
3. 如果平台需要登录态才能下载附件，可以使用用户在当前会话中提供的 Cookie，但只能放在临时 shell 环境或一次性命令中，不要写入任何文件、日志或最终输出
4. 根据题目标题创建 `{{root_name}}/challenges/{{challenge_group_prefix}}<title>` 目录；标题含中文、空格或符号时保留可读名称
5. 运行 `{{root_name}}/scripts/challenge/init_challenge.sh {{root_name}}/challenges/{{challenge_group_prefix}}<title>`；该步骤会在题目目录内初始化 git，并在首次初始化时创建 `[ckpt0 <题目名>]`
6. 保存题面为 `description.md`，写清来源 URL、分类、标签、环境、附件信息和下载时间
7. 下载附件到 challenge 目录，必要时解压；保留原始附件，避免覆盖同名重要文件
8. 识别附件类型；如果是 pwn 题，尽量识别主二进制、libc、ld，并更新 `amds_state/run.env`
9. 把确认过的题目信息、文件 hash、附件类型写入 `amds_state/cognition.json.facts`，再渲染 `amds_state/COGNITION.md`
10. 把当前状态、后续解题建议和开放问题写入 `amds_state/cognition.json.state`，再渲染 `amds_state/COGNITION.md`
11. 需要保留的下载日志、识别输出或错误详情放进 `amds_state/evidence/`，并在 `amds_state/cognition.json` 中引用相对路径
12. 如果下载失败，记录失败状态、HTTP 状态码、需要的凭据或手工步骤，不要伪造成功
13. 最终只汇报 challenge 目录、下载的文件、初始化结果和未完成事项

执行约束：
- 不要爬取题解或解题资料
- 不要把 Cookie、token、session、Authorization 等敏感值写入仓库或输出
- 不要因为附件看起来像已知题就开始套旧 exp
- 不要创建 `exp.py` 或 `wp.md`，除非附件中原本就包含这些文件；fetch-only 只负责落地题目

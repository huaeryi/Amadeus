题型 workflow：web。按 `ctf-web` 的思路解决 `{{challenge_path}}`。

优先使用这些 skill：
- `ctf-web`：主技能，默认按这个做
- `solve-challenge`：用于先做总分类和调度
- `ctf-writeup`：用于最终整理 `wp.md`

这题主要按 web 路线推进，不要偏离主线；除非题目材料明确证明分类错误，否则 CTF 方向以 `--workflow web` 为准。

先读：
- `{{root_name}}/prompts/learn/web_learning.md`

工作要求：
1. 读取题目目录中的源码、Dockerfile、compose、配置、题面和附件
2. 先本地搭建或确认服务入口，再做路由、鉴权、模板、数据库、文件上传、反序列化、SSRF、SSTI、SQLi、XSS、JWT、原型链等攻击面梳理
3. 优先写可复现的 `exp.py`，用 requests/httpx 等脚本化 exploit，不要只靠浏览器手点
4. 如果需要登录态、bot、admin cookie、外带服务或回连地址，先在 `amds_state/cognition.json.state` 记录依赖和验证方式
5. 到关键里程碑时按 `{{root_name}}/prompts/cmds/checkpoint.md` 创建具体 checkpoint；web 常用名称例如 `routes-auth-map-done`、`jwt-none-rejected`、`ssti-render-control-works`、`upload-path-traversal-verified`、`rce-command-output-verified`
6. 如果某条路线失败，不要在脏状态上持续修补；在 `amds_state/cognition.json.state` 的 rejected_branches 记录失败原因，并按公共 checkpoint 策略回退或开分支
7. 必须实际运行 exploit 拿到 flag，并把 flag 结果作为完成标准
8. 最终产出 `exp.py` 和 `wp.md`
9. 如果缺少远程信息、附件信息或验证条件，再向我询问

执行约束：
- 先做本地源码和服务分析，不要跳过环境复现
- 不要搜索或读取任何 WP/题解/公开 exploit
- 不要攻击非题目授权范围的目标
- 不要假设旧 exp 一定可用，结论必须基于当前目录中的文件和验证结果
- 只把确认过的事实写进 `amds_state/cognition.json.facts`
- 推测、分支路线和下一步放进 `amds_state/cognition.json.state`
- HTTP 请求响应样本、服务日志、PoC 输出等证据写入 `amds_state/evidence/`，在 `amds_state/cognition.json` 中引用相对路径
- checkpoint 和回退统一遵守 `{{root_name}}/prompts/cmds/checkpoint.md`
- 新写的 `exp.py` 尽量通过参数或环境变量配置 `BASE_URL`、账号、token、callback 等运行条件

开始解决 `{{challenge_path}}` 这道 web 题，按 `ctf-web` 的思路做。

优先使用这些 skill：
- `ctf-web`：主技能，默认按这个做
- `solve-challenge`：用于先做总分类和调度

这题主要按 web 路线推进，不要偏离主线。

先读：
- `{{root_name}}/AGENTS.md`

工作要求：
1. 先运行 `{{root_name}}/bin/init_challenge.sh {{challenge_path}}`
2. 读取题目目录中的源码、Dockerfile、compose、配置、题面和附件
3. 把已确认事实写进 `FACTS.md`
4. 把当前阶段、下一步、失败路线和开放问题写进 `STATE.md`
5. 先本地搭建或确认服务入口，再做路由、鉴权、模板、数据库、文件上传、反序列化、SSRF、SSTI、SQLi、XSS、JWT、原型链等攻击面梳理
6. 优先写可复现的 `exp.py`，用 requests/httpx 等脚本化 exploit，不要只靠浏览器手点
7. 如果需要登录态、bot、admin cookie、外带服务或回连地址，先在 `STATE.md` 记录依赖和验证方式
8. 到关键里程碑时运行 checkpoint；名称不用固定死，应根据题目实际进展命名，例如 `env-ok`、`route-map-confirmed`、`auth-bypass-confirmed`、`primitive-confirmed`、`rce-confirmed`
9. 如果某条路线失败，不要在脏状态上持续修补；在 `attempts/` 记录失败原因，必要时用 `restore.sh` 回退到上一个 checkpoint
10. 必须实际运行 exploit 拿到 flag，并把 flag 结果作为完成标准
11. 最终产出 `exp.py` 和 `wp.md`
12. 如果缺少远程信息、附件信息或验证条件，再向我询问

执行约束：
- 先做本地源码和服务分析，不要跳过环境复现
- 不要搜索或读取任何 WP/题解/公开 exploit
- 不要攻击非题目授权范围的目标
- 不要假设旧 exp 一定可用，结论必须基于当前目录中的文件和验证结果
- 只把确认过的事实写进 `FACTS.md`
- 推测、分支路线和下一步放进 `STATE.md`
- 分支失败后优先回退到 checkpoint，再换路线
- 新写的 `exp.py` 尽量通过参数或环境变量配置 `BASE_URL`、账号、token、callback 等运行条件

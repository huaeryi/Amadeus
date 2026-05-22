# Web Learning

只保留能直接减少试错的规则。

## Fast Rules

- Repro first: 先确认 Docker/依赖/数据库/secret/bot/callback 能跑。
- Map first: 先列路由、参数、鉴权边界、上传点、后台接口。
- Sink first: payload 升级前，用 harmless marker 证明输入到达 sink。
- State first: 记录 cookie、CSRF、JWT、角色、token 过期和 admin bot 条件。
- Encoding first: 确认 method、content-type、URL/JSON/form/multipart 编码和重定向。
- Script first: exploit 必须可复现，`BASE_URL`、proxy、cookie、timeout 参数化。

## Learned Rules

### Blind Payload

- Signal: payload 无回显或依赖 bot/callback。
- Action: 先验证 DNS/HTTP callback 链路和 sink reachability。
- Verify: harmless marker 能出现在日志、回连或副作用中。
- Avoid: 未确认执行链路就堆复杂 RCE payload。

### Auth Boundary

- Signal: 同一路由不同身份结果不同，或 exploit 依赖 admin/bot。
- Action: 先写脚本固定登录态和权限步骤。
- Verify: exploit 脚本从空 session 可复现到目标权限。
- Avoid: 把浏览器手工状态当成可复现 exploit。

## Anti-patterns

- 未确认 sink 可达就堆 payload。
- 未记录登录态就写 exploit。
- 忽略 content-type/encoding，payload 没进目标 parser。
- 只靠浏览器手点，不写脚本。

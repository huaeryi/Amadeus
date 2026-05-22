# Reverse Learning

只保留能直接减少试错的规则。

## Fast Rules

- Behavior first: 先运行样例输入，记录输入输出、长度、失败路径。
- Identify first: 先确认架构、壳/混淆、依赖、入口和比较函数。
- Checker first: 用字符串、断点、trace 定位 checker，再读细节。
- Extract first: 关键变换尽早抽成 Python/z3 脚本。
- Semantics first: 注意 bit width、signedness、endian、overflow。
- Verify first: candidate 必须跑原程序验证。

## Learned Rules

### Static Browsing Stop

- Signal: 已看多个函数但没有缩小 checker。
- Action: 切动态断点/trace/patch，用输入差异定位路径。
- Verify: 能稳定命中比较点或关键分支。
- Avoid: 无目标浏览反编译结果。

### Constraint Solve

- Signal: checker 是多轮算术/位运算/状态机。
- Action: 抽取约束并回代，必要时保留原始位宽。
- Verify: 解出的输入通过原程序。
- Avoid: z3 出解后不跑目标程序。

## Anti-patterns

- 未定位 checker 就写 solve。
- 忽略位宽和符号语义。
- 把壳/反调试当业务逻辑。
- candidate 不回代验证。

# Crypto Learning

只保留能直接减少试错的规则。

## Fast Rules

- Parameters first: 先结构化记录 n/e/c、曲线、modulus、维度、padding、nonce、样本数。
- Applicability first: 每条攻击路线先写数学前提，再跑工具。
- Oracle first: 远程题先测次数限制、错误类型、状态重置和输出差异。
- Randomness first: 检查 nonce 重用、低熵 seed、时间种子、线性 PRNG、重复样本。
- Tool first: 大整数/有限域用 Sage，约束用 z3，格用 fplll，不要长时间手算。
- Verify first: key/plaintext/flag candidate 必须回代原算法验证。

## Learned Rules

### RSA Template Guard

- Signal: 题面像 RSA。
- Action: 先检查参数条件，再选择 small-e/common-modulus/Wiener/Coppersmith。
- Verify: 条件满足且结果回代 `pow(m,e,n)==c`。
- Avoid: 看见 RSA 就套模板。

### Oracle Probe

- Signal: 题目可交互或错误信息不同。
- Action: 写最小脚本测同输入重复、非法输入、边界输入和状态重置。
- Verify: oracle 行为稳定后再设计攻击。
- Avoid: 未测清 oracle 就写完整 exploit。

## Anti-patterns

- 未确认 bound 就跑 Coppersmith/lattice。
- z3/Sage 出解后不回代。
- 忽略字节序、编码、分块边界。
- 把乱码直接当密码问题。

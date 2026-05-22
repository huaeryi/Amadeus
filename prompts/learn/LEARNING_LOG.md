# Learning Log

每次运行 `amds learn <challenge>` 后，在这里追加一条简短记录。
学习文件是被维护的：优先修改、合并、替换或删除旧规则，不是只追加新规则。

格式：

```md
## YYYY-MM-DD HH:MM <challenge-name>

- category:
- updated:
- changed:
- removed:
- skipped:
```

只记录长期学习文件的变化摘要，不记录 flag、token、远程地址、具体 payload 或一次性 offset。

## 2026-05-22 14:10 pwn1

- category: pwn
- updated: `Amadeus/prompts/learn/pwn_learning.md`, `Amadeus/challenges/pwn1/REFLECTION.md`
- changed: added `Ret2win Before Chains`, `Stack Offset From Frame`, `Prefer Simplest Bug`
- skipped: flag, remote endpoint, concrete payload bytes, one-time function address, exact stack offset

## 2026-05-22 14:13 bigduck

- category: pwn
- updated: `Amadeus/prompts/learn/pwn_learning.md`, `Amadeus/challenges/bigduck/REFLECTION.md`
- changed: updated `Seccomp first`; added `OOB Pointer Cursor` and `Setcontext ORW Trigger`
- removed: none
- skipped: flag, remote endpoint, concrete offsets, exact gadgets, final payload bytes

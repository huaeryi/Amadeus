# Pwn Learning

只保留能直接减少试错的规则。

## Fast Rules

- Env first: 先确认 binary/libc/ld/patched/remote 参数；`amds_state/run.env` 不准就先修。
- Primitive first: crash/leak/write/UAF/fmt offset 都先用最小 PoC 验证，再写完整 exploit。
- Libc first: 依赖 libc offset 时，先确认 libc 来源；缺 libc 就泄露至少两个符号再定版本。
- Heap first: heap 路线先画操作状态机和 chunk layout；metadata corruption 前 checkpoint。
- Seccomp first: 有沙箱先确认禁用 syscall；`execve` 被禁就直接转 ORW/openat/mmap。
- Remote last but early: 本地 shell 不是完成；远程 I/O、libc、timeout、菜单同步要尽早检查。

## Learned Rules

### Ret2win Before Chains

- Signal: No canary, no PIE, and the binary has a function that directly gives shell/flag/code execution.
- Action: Compute the saved return-address offset and overwrite return to that function before trying libc, shellcode, or ROP chains.
- Verify: Local control reaches the function, then remote reproduces with the same symbol-based target.
- Avoid: Spending time on libc identification, one_gadget, or shellcode when a fixed in-binary target is enough.

### Stack Offset From Frame

- Signal: Stack input uses `gets`/unbounded read and disassembly shows buffer address relative to `esp/rsp/rbp`.
- Action: Derive offset from the frame layout, then confirm with cyclic only if the layout is ambiguous.
- Verify: Break at function return or use a tiny payload to show the saved return address is exactly controlled.
- Avoid: Guessing padding by payload length when alignment prologue/epilogue changes the apparent buffer size.

### Prefer Simplest Bug

- Signal: Multiple bugs appear in one function, such as stack overflow plus `printf(user_input)`.
- Action: Rank paths by required primitives and protections; take direct control-flow hijack first if protections allow it.
- Verify: A minimal payload wins without needing leak/write staging.
- Avoid: Chasing format-string leaks or GOT writes just because the pattern is visible.

### Menu UAF State

- Signal: 菜单题 `ptr/size/used` 分开存，free/show/edit 检查不一致。
- Action: 列每个操作读写的元数据，用最小脚本测 freed slot 是否还能 read/write。
- Verify: `free -> show` 读旧 chunk，或 `free -> edit -> alloc` 影响同块/freelist。
- Avoid: 只看到 UAF/double free 就直接 poisoning。

### Unsorted Leak

- Signal: freed 大 chunk 仍可被 show/puts/%s 打印。
- Action: 大 chunk 后放 guard，free 后读 fd/bk 泄露 main_arena。
- Verify: libc base 页对齐，符号落在 libc mapping；收包按菜单分隔符切。
- Avoid: 大 chunk 紧贴 top chunk，或把二进制泄露按文本行解析。

### Tcache Poisoning

- Signal: glibc 2.26-2.31、无 safe-linking，且能写 freed tcache chunk next。
- Action: 先确认 size class 和 tcache 链，再改 next 指向目标。
- Verify: 两次同 size malloc 后第二次返回目标地址。
- Avoid: 未确认 glibc/safe-linking/size class 就调 offset。

### Full RELRO Target

- Signal: Full RELRO + 已有 libc base + 可写 primitive。
- Action: 不走 GOT；检查 hook、FILE、ROP/SROP/ORW 等可触发目标。
- Verify: 写入目标后用最小触发路径执行一次。
- Avoid: Full RELRO 下继续设计 GOT overwrite。

### OOB Pointer Cursor

- Signal: 菜单题只做 index 上界检查，指针数组附近有全局指针或自指针。
- Action: 先画 `.bss`/全局指针表，找一个可改指针当 cursor，再用 read/write 操作重定向它。
- Verify: cursor 指向已知 qword 后能读回，再写回无害地址做 roundtrip。
- Avoid: 把单次负下标泄露当稳定原语，或还没验证 cursor 就大块覆盖全局区。

### Setcontext ORW Trigger

- Signal: Full RELRO、NX、seccomp 禁 shell，且有 libc base、AAW 和可控参数的触发点。
- Action: 在可写内存放 fake ucontext/fpregs/ORW ROP，hook 触发点到 `setcontext`。
- Verify: 确认当前 libc 的 ucontext 字段偏移、fpregs 不和 ROP 重叠，先本地读文件。
- Avoid: 继续调 `system`/one_gadget，或使用带额外 pop/副作用的 gadget。

## Anti-patterns

- 未确认 libc 就调 one_gadget。
- 未确认 fmt offset 就写 fmt payload。
- 未确认 canary/PIE 就拼最终 ROP。
- heap 崩溃后只改 offset，不重新看堆状态。
- 没 checkpoint 就连续尝试破坏性 heap 路线。

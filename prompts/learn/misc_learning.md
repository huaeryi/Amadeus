# Misc Learning

只保留能直接减少试错的规则。

## Fast Rules

- Identify first: 先跑 file/strings/exiftool/binwalk/xxd/entropy/hash。
- Layer first: 每层解码保存输入、命令、输出和判断依据。
- Tool first: 流量用 tshark，隐写用 zsteg/steghide，音频用 ffmpeg/sox，约束用 z3。
- Repro first: 最终保留 `solve.py` 或可执行命令序列。
- Pivot first: 出现密码体制、源码服务、可执行逻辑、二进制漏洞信号就切对应 workflow。

## Learned Rules

### Encoding Chain

- Signal: 输出像乱码但有稳定字符集/长度变化。
- Action: 逐层尝试常见编码/压缩/字节序，并保存中间产物。
- Verify: 每层输出文件类型或结构更明确。
- Avoid: 用网站乱试但不记录步骤。

### Forensics Evidence

- Signal: 图片/音频/流量/压缩包疑似隐藏信息。
- Action: 先找 metadata、差异、频谱、像素、协议对象或嵌套文件证据。
- Verify: 工具输出能解释下一步，不靠猜。
- Avoid: 没证据时长期猜隐写方式。

## Anti-patterns

- 只看扩展名判断类型。
- 不保存中间层输出。
- 不写可复现步骤。
- 已经该 pivot 还按 misc 猜。

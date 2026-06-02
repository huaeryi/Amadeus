from pwn import *
import sys

context.terminal = ['tmux', 'sp', '-h']
context.update(log_level='debug', os='linux', arch='i386')

if len(sys.argv) > 1 and sys.argv[1] == "r":
    io = remote('')
else:
    io = process('')

elf = ELF('')


io.interactive()
from pwn import *
import sys

context.terminal = ['tmux', 'sp', '-h']
context.update(log_level='debug', os='linux', arch='i386')

if len(sys.argv) > 1 and sys.argv[1] == "r":
    io = remote('node5.buuoj.cn', 28917)
else:
    io = process('./ciscn_2019_n_3')

elf = ELF('./ciscn_2019_n_3')


io.interactive()
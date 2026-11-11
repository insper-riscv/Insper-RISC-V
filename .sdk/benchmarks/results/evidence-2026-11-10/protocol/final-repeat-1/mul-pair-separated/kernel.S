.global _start
.text
_start:
li s0,0x8100
li a1,0x12345678
li t2,0x01020304
li t0,1
sw t0,0(s0)
mulhu t3,a1,t2
nop
nop
nop
nop
nop
nop
nop
nop
mul t4,a1,t2
nop
nop
nop
nop
nop
nop
nop
nop
xor a0,t3,t4
nop
nop
nop
nop
nop
nop
nop
nop
sw a0,4(s0)
li t0,1
sw t0,8(s0)
2: j 2b

.global _start
.text
_start:
li s0,0x8100
li a1,0x7ffffff9
li t2,17
li t5,19
li t0,1
sw t0,0(s0)
divu t3,a1,t2
nop
nop
nop
nop
nop
nop
nop
nop
remu t4,a1,t5
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

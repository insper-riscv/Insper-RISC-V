.global _start
.text
_start:
li s0,0x8100
li a0,100
li t0,1
sw t0,0(s0)
1: addi a0,a0,-1
bnez a0,1b
sw a0,4(s0)
li t0,1
sw t0,8(s0)
2: j 2b

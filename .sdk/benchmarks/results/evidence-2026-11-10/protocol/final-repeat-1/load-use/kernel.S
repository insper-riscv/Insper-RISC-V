.global _start
.text
_start:
li s0,0x8100
li s1,0x8200
sw zero,0(s1)
li t1,64
li t0,1
sw t0,0(s0)
1: lw a0,0(s1)
addi a0,a0,1
sw a0,0(s1)
addi t1,t1,-1
bnez t1,1b
sw a0,4(s0)
li t0,1
sw t0,8(s0)
2: j 2b

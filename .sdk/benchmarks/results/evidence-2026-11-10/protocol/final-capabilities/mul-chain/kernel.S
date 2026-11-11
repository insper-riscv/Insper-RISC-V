.global _start
.text
_start:
li s0,0x8100
li a0,1
li t1,64
li t2,3
li t0,1
sw t0,0(s0)
1: mul a0,a0,t2
addi t1,t1,-1
bnez t1,1b
sw a0,4(s0)
li t0,1
sw t0,8(s0)
2: j 2b

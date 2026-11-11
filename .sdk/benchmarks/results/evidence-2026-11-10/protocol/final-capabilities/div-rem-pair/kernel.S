.global _start
.text
_start:
li s0,0x8100
li a0,0
li a1,0x7ffffff9
li t1,64
li t2,17
li t0,1
sw t0,0(s0)
1: divu t3,a1,t2
remu t4,a1,t2
xor t3,t3,t4
add a0,a0,t3
addi t1,t1,-1
bnez t1,1b
sw a0,4(s0)
li t0,1
sw t0,8(s0)
2: j 2b

.global _start
.text
_start:
li s0,0x8100
li s1,0x8200
li t1,0x01020304
sw t1,0(s1)
li t1,0x05060708
sw t1,4(s1)
li a0,0xa1b2c3d4
li t0,1
sw t0,0(s0)
sw a0,3(s1)
lw t0,0(s1)
lw t1,4(s1)
xor a0,t0,t1
sw a0,4(s0)
li t0,1
sw t0,8(s0)
2: j 2b

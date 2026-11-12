/* SPDX-License-Identifier: Apache-2.0
 * Eight retired instructions between markers: 3 compute, 2 memory,
 * 3 control transfers. The squashed ADDI must not be counted.
 */
.global main
.type main,@function
main:
    mv s0, ra
    jal ra, start_trigger
    addi t0, zero, 1
    li t1, TEST_RAM_BASE
    sw t0, 0(t1)
    lw t2, 0(t1)
    add t3, t2, t0
    bne t3, t0, 1f
    addi t3, zero, 99
1:
    jal ra, stop_trigger
    li a0, 1
    li t0, 2
    bne t3, t0, 2f
    li a0, RETURN_CODE
2:
    mv ra, s0
    ret
.size main,.-main

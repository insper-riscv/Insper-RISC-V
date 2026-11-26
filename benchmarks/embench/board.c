/* SPDX-License-Identifier: Apache-2.0
 * Simulation-only Embench board port. Markers are observed on retirement;
 * no CSR extension, peripheral, printf or host wall clock is required.
 */
#include "support.h"

void initialise_board(void) {}

__asm__(
    ".section .text.start_trigger,\"ax\",@progbits\n"
    ".balign 4\n.global start_trigger\n.type start_trigger,@function\n"
    "start_trigger:\naddi zero,zero,0\nret\n"
    ".size start_trigger,.-start_trigger\n"
    ".section .text.stop_trigger,\"ax\",@progbits\n"
    ".balign 4\n.global stop_trigger\n.type stop_trigger,@function\n"
    "stop_trigger:\naddi zero,zero,0\nret\n"
    ".size stop_trigger,.-stop_trigger\n"
    ".text\n"
);

/* boot_memory.S da plataforma de2-115: o carregador fixo gravado na BOOT_MEMORY. Todo o comportamento mora no
 * boot_core.S comum (base/src/boot); este arquivo só inclui os cabeçalhos que o riscv-tools generate-memory-map escreve
 * a partir do platform.yaml e o núcleo do carregador, que por sua vez inclui os fragmentos de boot das extensões
 * ligadas no núcleo (Core/src/<Extensão>/boot.inc). */

#include "memory_map.h"
#include "flash_banks.h"
#include "boot_config.h"

/* Esta plataforma aceita um programa deixado na RAM pelo hospedeiro pela porta de depuração: é assim que o
 * gravador da NOR chega a uma placa de FLASH vazia (ver boot_core.S, passo 4). */
#define RV32_BOOT_RAM_MAGIC 0x52414D42   // 'RAMB'

#include "../../../../base/src/boot/boot_core.S"

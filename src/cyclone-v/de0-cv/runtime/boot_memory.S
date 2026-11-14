/* boot_memory.S da plataforma de0-cv: o carregador fixo gravado na BOOT_MEMORY. Todo o comportamento mora no
 * boot_core.S comum (src/boot); este arquivo só inclui os cabeçalhos que o riscv-tools generate-memory-map escreve
 * a partir do platform.yaml e o núcleo do carregador, que por sua vez inclui os fragmentos de boot das extensões
 * ligadas no núcleo (Core/src/<Extensão>/boot.inc). */

#include "memory_map.h"
#include "flash_banks.h"
#include "boot_config.h"

#include "../../../boot/boot_core.S"

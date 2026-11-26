/* boot_memory.S da plataforma fpga-external: o carregador fixo gravado na BOOT_MEMORY. Todo o comportamento mora no
 * boot_core.S comum (base/src/boot); este arquivo só inclui os cabeçalhos que o riscv-tools generate-memory-map escreve
 * a partir do platform.yaml e o núcleo do carregador, que por sua vez inclui os fragmentos de boot das extensões
 * ligadas no núcleo (Core/src/<Extensão>/boot.inc). */

#include "memory_map.h"
#include "boot_config.h"

#include "../../../../base/src/boot/boot_core.S"

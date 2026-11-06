"""Confere que cada top declara os HAS_* do seu pacote gerado.

O ``riscv-tools platform sync`` e o ``generate`` passam ao GHDL um
generic para cada constante ``HAS_*`` do ``*_map_pkg.vhd``. Um top que
não o declara quebra a elaboração com
``cannot find in top entity generic``.
"""

import re
import sys
from pathlib import Path

# Pacote gerado de cada plataforma e os tops que recebem os generics.
PLATFORMS: dict[str, list[str]] = {
    "src/simulation/internal-mem/rtl/internal_mem_map_pkg.vhd": [
        "src/simulation/internal-mem/rtl/rv32i3stage_core_sim_test.vhd",
        "src/simulation/internal-mem/quartus/core_fpga_test.vhd",
    ],
    "src/cyclone-v/de0-cv/de0_cv_map_pkg.vhd": [
        "src/cyclone-v/de0-cv/de0-cv_sim_top.vhd",
    ],
    "src/simulation/modular/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
}

# Tops sem cache: os generics de cache só existem nos tops com cache.
CACHE = {"HAS_ICACHE", "HAS_DCACHE"}
NO_CACHE = {
    "src/simulation/internal-mem/quartus/core_fpga_test.vhd",
}

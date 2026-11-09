"""Confere que cada top declara os HAS_* do seu pacote gerado.

Um generic ``HAS_*`` que o top não declara quebra a elaboração com
``cannot find in top entity generic`` quando o teste ou a plataforma o
passa ao GHDL. As constantes de ISA ficam de fora de todos os tops,
porque o núcleo e o SoC as leem do ``config_pkg``.
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
    "src/cyclone-v/external-data/external_data_map_pkg.vhd": [
        "src/cyclone-v/external-data/external-data_sim_top.vhd",
    ],
    "src/simulation/template/rtl/template_map_pkg.vhd": [
        "src/simulation/template/rtl/template_sim_top.vhd",
    ],
    "src/simulation/modular/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/simulation/test-integrated/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/simulation/test-external-data/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/simulation/test-external-instruction/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/simulation/test-external/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/cyclone-v/fpga-integrated/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/cyclone-v/fpga-external-data/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/cyclone-v/fpga-external-instruction/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/cyclone-v/fpga-external/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/cyclone-v/fpga-uart-jtag/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
    "src/cyclone-v/fpga-uart-pins/modular_map_pkg.vhd": [
        "src/simulation/modular/modular_sim_top.vhd",
    ],
}

# Tops sem cache: os generics de cache só existem nos tops com cache.
CACHE = {"HAS_ICACHE", "HAS_DCACHE"}
NO_CACHE = {
    "src/simulation/internal-mem/quartus/core_fpga_test.vhd",
}

# Constantes de ISA: o núcleo e o SoC as leem do config_pkg da plataforma,
# então nenhum top as declara como generic.
ISA = {
    "HAS_E",
    "HAS_M",
    "HAS_ZMMUL",
    "HAS_ZICSR",
    "HAS_ZICNTR",
    "HAS_ZIHPM",
    "HAS_ZIMOP",
    "HAS_ZICOND",
    "HAS_ZIHINTNTL",
    "HAS_ZIHINTPAUSE",
    "HAS_ZIFENCEI",
    "HAS_ZICCLSM",
    "HAS_INTERRUPTS",
    "HAS_SSCOFPMF",
    "HAS_ACCESS_FAULTS",
}

CONSTANT = re.compile(r"constant\s+(HAS_\w+)\s*:", re.IGNORECASE)
GENERIC = re.compile(r"^\s*(HAS_\w+)\s*:", re.IGNORECASE | re.MULTILINE)


def names(pattern: re.Pattern[str], path: Path) -> set[str]:
    """Devolve os nomes ``HAS_*`` que o padrão acha no arquivo.

    Parameters
    ----------
    pattern : re.Pattern
        Expressão com o nome no primeiro grupo.
    path : Path
        Arquivo VHDL.

    Returns
    -------
    set of str
        Os nomes, em maiúsculas.
    """
    return {n.upper() for n in pattern.findall(path.read_text("utf-8"))}


def exempt_for(top: str) -> set[str]:
    """Devolve os generics que o top não precisa declarar.

    Parameters
    ----------
    top : str
        Caminho do top, relativo à raiz do repositório.

    Returns
    -------
    set of str
        Os nomes ``HAS_*`` dispensados nesse top.
    """
    exempt: set[str] = CACHE if top in NO_CACHE else set()
    return exempt | ISA


def missing(root: Path) -> list[str]:
    """Lista os ``HAS_*`` do pacote que o top não declara.

    Parameters
    ----------
    root : Path
        Raiz do repositório.

    Returns
    -------
    list of str
        Uma mensagem por par (top, generic) ausente.
    """
    problems: list[str] = []
    for package, tops in PLATFORMS.items():
        wanted = names(CONSTANT, root / package)
        for top in tops:
            absent = wanted - names(GENERIC, root / top) - exempt_for(top)
            problems += [f"{top}: falta o generic {n}" for n in sorted(absent)]
    return problems


def main() -> int:
    """Imprime os generics ausentes e devolve o código de saída."""
    problems = missing(Path(__file__).resolve().parents[1])
    print("\n".join(problems) or "todos os HAS_* do pacote estão nos tops")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

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
    "src/cyclone-v/external-data/external_data_map_pkg.vhd": [
        "src/cyclone-v/external-data/external-data_sim_top.vhd",
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
            exempt: set[str] = CACHE if top in NO_CACHE else set()
            absent = wanted - names(GENERIC, root / top) - exempt
            problems += [f"{top}: falta o generic {n}" for n in sorted(absent)]
    return problems


def main() -> int:
    """Imprime os generics ausentes e devolve o código de saída."""
    problems = missing(Path(__file__).resolve().parents[1])
    print("\n".join(problems) or "todos os HAS_* do pacote estão nos tops")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

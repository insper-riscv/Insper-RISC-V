"""Confere os números das fontes do PLIC contra o topo modular.

O topo modular (``modular_sim_top.vhd``) liga cada periférico a uma linha
do PLIC pelas constantes ``LINE_<NOME>``. As plataformas com PLIC listam
as mesmas fontes em ``interrupts.sources`` do ``platform.yaml`` (de onde
o ``generate-memory-map`` escreve ``IRQ_<NOME>`` e ``RV32_IRQ_<NOME>``).
Este script falha quando um número do topo difere de uma lista, ou
quando duas plataformas dão números diferentes à mesma fonte.
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOP = ROOT / "src/simulation/modular/modular_sim_top.vhd"
PLATFORMS = [
    ROOT / "src/simulation/modular/platform.yaml",
    ROOT / "src/cyclone-v/de0-cv/platform.yaml",
]
LINE = re.compile(
    r"constant\s+LINE_(\w+)\s*:\s*positive\s*:=\s*(\d+)\s*;", re.IGNORECASE
)


def main() -> int:
    """Compare as listas de fontes com o topo e entre si.

    Returns
    -------
    int
        0 quando tudo concorda, 1 com os desacordos impressos.
    """
    top = {n.upper(): int(i) for n, i in LINE.findall(TOP.read_text("utf-8"))}
    problems: list[str] = []
    for path in PLATFORMS:
        data = yaml.safe_load(path.read_text("utf-8"))
        sources = data.get("interrupts", {}).get("sources", [])
        for item in sources:
            name, ident = str(item["name"]).upper(), int(item["id"])
            if top.get(name) != ident:
                problems.append(
                    f"{path.relative_to(ROOT)}: fonte {name} id {ident}, "
                    f"o topo modular tem {top.get(name)}"
                )
    for message in problems:
        print(message)
    if not problems:
        print(f"as fontes do PLIC concordam com o topo ({len(top)} linhas)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

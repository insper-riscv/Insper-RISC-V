"""Confere os números das fontes do PLIC contra o SoC.

O SoC (``soc.vhd``), que o topo modular instancia, liga cada periférico
a uma linha do PLIC pelas constantes ``LINE_<NOME>``. As plataformas com
PLIC listam as mesmas fontes em ``interrupts.sources`` do
``platform.yaml`` (de onde o ``generate-memory-map`` escreve
``IRQ_<NOME>`` e ``RV32_IRQ_<NOME>``). Este script falha quando um
número do topo difere de uma lista, ou quando duas plataformas dão
números diferentes à mesma fonte.
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOP = ROOT / "src/soc/soc.vhd"
PLATFORMS = [
    ROOT / "src/simulation/modular/platform.yaml",
    ROOT / "src/cyclone-v/de0-cv/platform.yaml",
]
LINE = re.compile(
    r"constant\s+LINE_(\w+)\s*:\s*positive\s*:=\s*(\d+)\s*;", re.IGNORECASE
)


def timer_names(data: dict[str, object]) -> set[str]:
    """Nomeia os temporizadores de uma plataforma, em maiúsculas.

    Um temporizador não tem constante ``LINE_*`` no SoC: a linha vem
    da tabela ``TIMER_IRQ_IDS`` do pacote de mapa, gerada do
    ``platform.yaml``. Vale a entrada de ``peripherals`` com
    ``kind: timer`` e a chamada ``TIMER`` sem ``kind``.

    Parameters
    ----------
    data : dict of {str: object}
        O ``platform.yaml`` lido, com ``peripherals`` em lista ou em
        mapa por nome.

    Returns
    -------
    set of str
        Os nomes dos temporizadores.
    """
    raw = data.get("peripherals") or []
    if isinstance(raw, dict):
        items = [{"name": n, **(v or {})} for n, v in raw.items()]
    else:
        items = list(raw)
    return {
        str(p["name"]).upper()
        for p in items
        if p.get("kind") == "timer"
        or (str(p["name"]).upper() == "TIMER" and "kind" not in p)
    }


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
        timers = timer_names(data)
        for item in sources:
            name, ident = str(item["name"]).upper(), int(item["id"])
            if name in timers:
                if ident in top.values():
                    problems.append(
                        f"{path.relative_to(ROOT)}: o temporizador {name} "
                        f"usa o id {ident}, linha fixa do SoC"
                    )
            elif top.get(name) != ident:
                problems.append(
                    f"{path.relative_to(ROOT)}: fonte {name} id {ident}, "
                    f"o SoC tem {top.get(name)}"
                )
    for message in problems:
        print(message)
    if not problems:
        print(f"as fontes do PLIC concordam com o topo ({len(top)} linhas)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

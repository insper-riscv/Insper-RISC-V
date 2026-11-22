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
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOP = ROOT / "base/src/soc/soc.vhd"
PLATFORMS = [
    ROOT / "src/simulation/modular/platform.yaml",
    ROOT / "src/cyclone-v/de0-cv/platform.yaml",
]
LINE = re.compile(
    r"constant\s+LINE_(\w+)\s*:\s*positive\s*:=\s*(\d+)\s*;", re.IGNORECASE
)


def _peripherals(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Leia os periféricos de um ``platform.yaml`` como lista de mapas.

    Parameters
    ----------
    data : dict of {str: Any}
        O ``platform.yaml`` lido, com ``peripherals`` em lista ou em
        mapa por nome.

    Returns
    -------
    list of dict of {str: Any}
        Um mapa por periférico, com a chave ``name``.
    """
    raw: Any = data.get("peripherals") or []
    if isinstance(raw, dict):
        return [
            {"name": str(n), **(v or {})}
            for n, v in cast("dict[str, Any]", raw).items()
        ]
    return list(cast("list[dict[str, Any]]", raw))


def timer_names(data: dict[str, Any]) -> set[str]:
    """Nomeia os temporizadores de uma plataforma, em maiúsculas.

    Um temporizador não tem constante ``LINE_*`` no SoC: a linha vem
    da tabela ``TIMER_IRQ_IDS`` do pacote de mapa, gerada do
    ``platform.yaml``. Vale a entrada de ``peripherals`` com
    ``kind: timer`` e a chamada ``TIMER`` sem ``kind``.

    Parameters
    ----------
    data : dict of {str: Any}
        O ``platform.yaml`` lido, com ``peripherals`` em lista ou em
        mapa por nome.

    Returns
    -------
    set of str
        Os nomes dos temporizadores.
    """
    return {
        str(p["name"]).upper()
        for p in _peripherals(data)
        if p.get("kind") == "timer"
        or (str(p["name"]).upper() == "TIMER" and "kind" not in p)
    }


def _check_source(
    path: Path,
    item: dict[str, Any],
    timers: set[str],
    top: dict[str, int],
) -> str | None:
    """Confira uma fonte do PLIC de uma plataforma contra o SoC.

    Parameters
    ----------
    path : Path
        O ``platform.yaml`` da plataforma.
    item : dict of {str: Any}
        A fonte, com ``name`` e ``id``.
    timers : set of str
        Os nomes dos temporizadores da plataforma.
    top : dict of {str: int}
        As linhas ``LINE_*`` do SoC.

    Returns
    -------
    str or None
        O desacordo, ou ``None`` quando a fonte concorda.
    """
    name, ident = str(item["name"]).upper(), int(item["id"])
    where = path.relative_to(ROOT)
    if name in timers:
        if ident in top.values():
            return (
                f"{where}: o temporizador {name} "
                f"usa o id {ident}, linha fixa do SoC"
            )
        return None
    if top.get(name) != ident:
        return f"{where}: fonte {name} id {ident}, o SoC tem {top.get(name)}"
    return None


def _check_platform(path: Path, top: dict[str, int]) -> list[str]:
    """Confira todas as fontes do PLIC de uma plataforma.

    Parameters
    ----------
    path : Path
        O ``platform.yaml`` da plataforma.
    top : dict of {str: int}
        As linhas ``LINE_*`` do SoC.

    Returns
    -------
    list of str
        Os desacordos encontrados.
    """
    data: dict[str, Any] = yaml.safe_load(path.read_text("utf-8"))
    sources: list[dict[str, Any]] = data.get("interrupts", {}).get(
        "sources", []
    )
    timers = timer_names(data)
    found = (_check_source(path, item, timers, top) for item in sources)
    return [message for message in found if message is not None]


def main() -> int:
    """Compare as listas de fontes com o topo e entre si.

    Returns
    -------
    int
        0 quando tudo concorda, 1 com os desacordos impressos.
    """
    top = {n.upper(): int(i) for n, i in LINE.findall(TOP.read_text("utf-8"))}
    problems = [m for path in PLATFORMS for m in _check_platform(path, top)]
    for message in problems:
        print(message)
    if not problems:
        print(f"as fontes do PLIC concordam com o topo ({len(top)} linhas)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

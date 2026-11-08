"""Agrupa os caminhos de um relatório por par de domínios."""

import re
import sys
from pathlib import Path

_DEFAULT_COUNT = 30
_MIN_FIELDS = 7
_ARGS_WITH_COUNT = 3
_NAME_WIDTH = 62


def domain(clock: str) -> str:
    """Abrevia o relógio ``general[n]`` para ``cn``.

    Parameters
    ----------
    clock : str
        Nome completo do relógio.

    Returns
    -------
    str
        O relógio abreviado.
    """
    return re.sub(r".*general\[(\d)\].*", r"c\1", clock)


def short_name(node: str) -> str:
    """Abrevia o nome de um nó, trocando os índices por ``#``.

    Parameters
    ----------
    node : str
        Nome hierárquico do nó.

    Returns
    -------
    str
        O sufixo do nome, sem índices.
    """
    leaf = node.rsplit("|", maxsplit=1)[-1]
    return re.sub(r"\[\d+\]|~DUPLICATE|\d+", "#", leaf)[-_NAME_WIDTH:]


def worst_by_key(path: str) -> dict[tuple[str, str, str], tuple[float, float]]:
    """Guarda a menor folga de cada par de domínios e registradores.

    Parameters
    ----------
    path : str
        Arquivo de caminhos, com linhas ``PATH`` e campos separados por
        tabulação.

    Returns
    -------
    dict
        Para cada chave, a menor folga e o atraso de dados do caminho.
    """
    groups: dict[tuple[str, str, str], tuple[float, float]] = {}
    with Path(path).open(encoding="utf-8") as lines:
        for line in lines:
            fields = line.rstrip("\n").split("\t")
            if fields[0] != "PATH" or len(fields) < _MIN_FIELDS:
                continue
            clock, slack, delay, source, target, source_clock = fields[1:7]
            key = (
                f"{domain(source_clock)}>{domain(clock)}",
                short_name(source),
                short_name(target),
            )
            value = float(slack)
            if key not in groups or value < groups[key][0]:
                groups[key] = (value, float(delay))
    return groups


def main() -> None:
    """Imprime os grupos de menor folga.

    O uso é ``agrupa_caminhos.py <pares> [n]``.
    """
    count = _DEFAULT_COUNT
    if len(sys.argv) >= _ARGS_WITH_COUNT:
        count = int(sys.argv[2])
    groups = worst_by_key(sys.argv[1])
    for key, (slack, delay) in sorted(
        groups.items(), key=lambda item: item[1][0]
    )[:count]:
        print(f"{slack:7.3f} {delay:6.2f}", *key)


if __name__ == "__main__":
    main()

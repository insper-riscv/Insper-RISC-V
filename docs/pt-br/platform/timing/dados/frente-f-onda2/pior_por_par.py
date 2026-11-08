"""Resume a menor folga de cada par de domínios de um relatório."""

import re
import sys
from collections import defaultdict
from pathlib import Path

_MIN_FIELDS = 7


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


def main() -> None:
    """Imprime a menor folga por par: ``pior_por_par.py <pares>``."""
    best: dict[str, tuple[float, float]] = defaultdict(lambda: (99.0, 0.0))
    with Path(sys.argv[1]).open(encoding="utf-8") as lines:
        for line in lines:
            fields = line.rstrip("\n").split("\t")
            if fields[0] != "PATH" or len(fields) < _MIN_FIELDS:
                continue
            key = f"{domain(fields[6])}>{domain(fields[1])}"
            slack = float(fields[2])
            if slack < best[key][0]:
                best[key] = (slack, float(fields[3]))
    print(
        " ".join(
            f"{key} {slack:.3f}({delay:.1f}ns)"
            for key, (slack, delay) in sorted(best.items())
        )
    )


if __name__ == "__main__":
    main()

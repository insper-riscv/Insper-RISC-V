"""Resume os caminhos por níveis de lógica de um relatório ``LV``."""

import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

_MIN_FIELDS = 8
_TOP_PAIRS = 50
_TOP_EXTREMES = 8
_ABBREV_WIDTH = 70
_NAME_WIDTH = 20
_DOMAINS = ("c3", "c2", "sdram", "dram_clk")
_HIGH_LEVELS = 9
_LOW_LEVELS = 6
_REMOVALS = (
    r"_OTERM\d+|_NEW\d*|~DUPLICATE|_RESYN\d+|_NEW_REG\d+",
    r"gen_index:\d+:",
)
_MODULES = (
    ("hpm_counter_bank", "Zihpm banco"),
    ("csr_file", "csr_file"),
    ("reg_id_ex", "ID/EX"),
    ("reg_ex_mem", "EX/MEM"),
    ("reg_mem_wb", "MEM/WB"),
    ("reg_if_id", "IF/ID"),
    ("pc_fetch", "PC"),
    ("stage_if", "IF"),
    ("stage_ex", "EX"),
    ("stage_mem", "MEM"),
    ("misaligned", "desalinhado"),
    ("DCACHE", "dcache"),
    ("ICACHE", "icache"),
    ("dcache", "dcache"),
    ("icache", "icache"),
    ("multdiv", "muldiv"),
    ("SDRAM", "sdram"),
    ("sdram", "sdram"),
    ("reg_file", "banco de registradores"),
    ("hazard", "HDU"),
)

Row = tuple[str, int, float, float, str, str]


def read_rows(path: str) -> list[Row]:
    """Lê as linhas ``LV`` do relatório.

    Parameters
    ----------
    path : str
        Arquivo do relatório, com campos separados por tabulação.

    Returns
    -------
    list of Row
        Domínio, níveis, folga, atraso, origem e destino do caminho.
    """
    rows: list[Row] = []
    with Path(path).open(encoding="utf-8") as lines:
        for line in lines:
            fields = line.rstrip("\n").split("\t")
            if fields[0] != "LV" or len(fields) < _MIN_FIELDS:
                continue
            domain, levels, slack, delay, source, target = fields[1:7]
            try:
                rows.append(
                    (
                        domain,
                        int(levels),
                        float(slack),
                        float(delay),
                        source,
                        target,
                    )
                )
            except ValueError:
                continue
    return rows


def abbreviate(node: str) -> str:
    """Abrevia o nome hierárquico de um nó.

    Parameters
    ----------
    node : str
        Nome completo do nó.

    Returns
    -------
    str
        Os três últimos componentes, sem índices nem sufixos do Quartus.
    """
    text = node.replace("core:CORE|", "")
    text = text.replace("\\gen_csr:", "").replace("\\gen_zihpm:", "")
    text = re.sub(_REMOVALS[0], "", text)
    text = re.sub(r"\[\d+\]", "[#]", text)
    text = re.sub(_REMOVALS[1], "", text)
    text = re.sub(r"\b\w+:(\w+)", r"\1", text)
    text = re.sub(r"(?<=[a-z_])\d+\b", "#", text)
    return "/".join(text.split("|")[-3:])[-_ABBREV_WIDTH:]


def module(node: str) -> str:
    """Dá o nome do módulo a que o nó pertence.

    Parameters
    ----------
    node : str
        Nome completo do nó.

    Returns
    -------
    str
        O módulo conhecido, ou o início do primeiro componente.
    """
    text = node.replace("core:CORE|", "")
    for key, name in _MODULES:
        if key in text:
            return name
    return text.split("|")[0][:_NAME_WIDTH]


def print_top_by_levels(rows: list[Row]) -> None:
    """Imprime os pares de maior número de níveis de cada domínio.

    Parameters
    ----------
    rows : list of Row
        Os caminhos do relatório.
    """
    for domain in _DOMAINS:
        chosen = sorted(
            (row for row in rows if row[0] == domain),
            key=lambda row: (-row[1], row[2]),
        )
        print(f"\n## top por niveis: {domain} n= {len(chosen)}")
        seen: dict[tuple[str, str, str, str], tuple[Row, int]] = {}
        for row in chosen:
            key = (
                module(row[4]),
                module(row[5]),
                abbreviate(row[4]),
                abbreviate(row[5]),
            )
            first, count = seen.get(key, (row, 0))
            seen[key] = (first, count + 1)
        for key, (first, count) in list(seen.items())[:_TOP_PAIRS]:
            print(
                f"{first[1]:2d} niv {first[3]:6.2f} ns folga "
                f"{first[2]:7.3f} x{count:<4} {key[2]} -> {key[3]}"
            )


def print_by_module(rows: list[Row]) -> None:
    """Imprime o agregado por módulo de destino nos domínios c3 e c2.

    Parameters
    ----------
    rows : list of Row
        Os caminhos do relatório.
    """
    print(
        "\n## agregado por modulo de destino (c3 e c2): >6, >8, >10, max,"
        " e max de atraso"
    )
    groups: defaultdict[tuple[str, str], list[Row]] = defaultdict(list)
    for row in rows:
        if row[0] in ("c3", "c2"):
            groups[(row[0], module(row[5]))].append(row)
    ordered = sorted(
        groups.items(), key=lambda item: -max(r[1] for r in item[1])
    )
    for (domain, name), found in ordered:
        counts = [sum(r[1] >= limit for r in found) for limit in (6, 8, 10)]
        print(
            f"{domain:<3} {name:<24} n={len(found):<5} >=6:{counts[0]:<5} "
            f">=8:{counts[1]:<5} >=10:{counts[2]:<4} "
            f"max={max(r[1] for r in found):<2} "
            f"maxatraso={max(r[3] for r in found):.2f}"
        )


def print_row(row: Row) -> None:
    """Imprime um caminho com níveis, atraso, folga e extremos.

    Parameters
    ----------
    row : Row
        O caminho a imprimir.
    """
    print(
        f"{row[1]:2d} niv {row[3]:6.2f} ns folga {row[2]:7.3f} "
        f"{abbreviate(row[4])} -> {abbreviate(row[5])}"
    )


def print_extremes(rows: list[Row]) -> None:
    """Imprime os extremos de níveis contra atraso e a média por nível.

    Parameters
    ----------
    rows : list of Row
        Os caminhos do relatório.
    """
    print(
        "\n## niveis altos com atraso baixo (roteamento bom) e niveis"
        " baixos com atraso alto (roteamento ruim), c3"
    )
    c3_rows = [row for row in rows if row[0] == "c3"]
    high = sorted(
        (r for r in c3_rows if r[1] >= _HIGH_LEVELS), key=lambda r: r[3]
    )
    low = sorted(
        (r for r in c3_rows if r[1] <= _LOW_LEVELS), key=lambda r: -r[3]
    )
    for row in high[:_TOP_EXTREMES]:
        print_row(row)
    print("--")
    for row in low[:_TOP_EXTREMES]:
        print_row(row)
    by_level: defaultdict[int, list[float]] = defaultdict(list)
    for row in c3_rows:
        by_level[row[1]].append(row[3])
    means = {
        key: round(statistics.mean(value), 2)
        for key, value in sorted(by_level.items())
    }
    print("\natraso medio por nivel (c3):", means)


def main() -> None:
    """Imprime o resumo por níveis do relatório indicado."""
    rows = read_rows(sys.argv[1])
    counts = {
        d: len([r for r in rows if r[0] == d]) for d in {r[0] for r in rows}
    }
    print("DOMINIOS", counts)
    print_top_by_levels(rows)
    print_by_module(rows)
    print_extremes(rows)


if __name__ == "__main__":
    main()

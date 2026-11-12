"""Consolida os resumos do Quartus em tabelas TSV por pasta de dados.

Lê os ``*.sta.resumo.txt`` e ``<exp>-semente-<n>.resumo.txt`` (o
``.sta.summary`` do Timing Analyzer) e os ``*.fit.resumo.txt`` (o
``.fit.summary`` do Fitter) de cada pasta e escreve, na própria pasta,
``tabela-sementes.tsv`` (folgas por semente e domínio) e
``tabela-ocupacao.tsv`` (ocupação por semente).

Uso, da raiz do repositório::

    python tabelar_resumos.py gerar [PASTA ...]
    python tabelar_resumos.py --check [PASTA ...]
    python tabelar_resumos.py markdown PASTA EXPERIMENTO [--lang en]
    python tabelar_resumos.py markdown-fit PASTA EXPERIMENTO [--lang en]

Sem pasta, usa a pasta deste script e as subpastas que a contêm.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

SEEDS_NAME = "tabela-sementes.tsv"
FIT_NAME = "tabela-ocupacao.tsv"

# Modelo de referência das colunas por domínio.
REF_MODEL = "Slow 1100mV 85C Model"

# Relógio do projeto para o nome curto do domínio.
DOMAINS: tuple[tuple[str, str], ...] = (
    (r"general\[3\]", "core"),
    (r"general\[2\]", "fetch"),
    (r"general\[0\].*PLL_OUTPUT_COUNTER", "mem"),
    (r"general\[1\]", "pll_dram_clk"),
    (r"FRACTIONAL_PLL", "pll_vco"),
    (r"^DRAM_CLK_pin$", "DRAM_CLK"),
    (r"altera_reserved_tck", "jtag"),
    (r"^(CLOCK_50|i_clock_50)$", "clock_50"),
)

SEEDS_HEADER = (
    "experimento",
    "semente",
    "dominio",
    "setup_slack_ns",
    "setup_tns_ns",
    "hold_slack_ns",
    "hold_tns_ns",
    "recovery_slack_ns",
    "removal_slack_ns",
    "mpw_slack_ns",
    "setup_pior_modelo_ns",
    "hold_pior_modelo_ns",
)

FIT_FIELDS: tuple[tuple[str, str], ...] = (
    ("topo", "Top-level Entity Name"),
    ("revisao", "Revision Name"),
    ("dispositivo", "Device"),
    ("alms", "Logic utilization (in ALMs)"),
    ("registradores", "Total registers"),
    ("pinos", "Total pins"),
    ("bits_memoria", "Total block memory bits"),
    ("blocos_ram", "Total RAM Blocks"),
    ("dsp", "Total DSP Blocks"),
    ("plls", "Total PLLs"),
)

KINDS = {
    "Setup": "setup",
    "Hold": "hold",
    "Recovery": "recovery",
    "Removal": "removal",
    "Minimum Pulse Width": "mpw",
}

_BLOCK = re.compile(
    r"Type\s*:\s*(?P<model>\w+ 1100mV \d+C Model) "
    r"(?P<kind>Setup|Hold|Recovery|Removal|Minimum Pulse Width) "
    r"'(?P<clock>[^']*)'\s*\n"
    r"Slack\s*:\s*(?P<slack>\S+)\s*\n"
    r"TNS\s*:\s*(?P<tns>\S+)"
)
_OWN_PLL = re.compile(
    r"^u_pll\|pll_inst\|.*general\[(\d)\].*PLL_OUTPUT_COUNTER"
)
_NAME = re.compile(
    r"^(?P<exp>.+?)-semente-(?P<seed>\d+)"
    r"(?P<kind>\.sta|\.fit)?\.resumo\.txt$"
)
_NAME_BARE = re.compile(r"^(?P<exp>.+)\.resumo\.txt$")


def short_domain(clock: str) -> str:
    """Devolve o nome curto do domínio de um relógio do Quartus.

    Parameters
    ----------
    clock : str
        Nome do relógio como aparece no resumo.

    Returns
    -------
    str
        Nome curto (``pll_c<n>`` para a PLL do topo ``core_fpga_test``),
        ou o próprio nome se nenhum padrão casar.
    """
    own = _OWN_PLL.search(clock)
    if own:
        return f"pll_c{own[1]}"
    for pattern, name in DOMAINS:
        if re.search(pattern, clock):
            return name
    return clock


def parse_name(name: str) -> tuple[str, str, str] | None:
    """Separa experimento, semente e tipo do nome de um resumo.

    Parameters
    ----------
    name : str
        Nome do arquivo.

    Returns
    -------
    tuple[str, str, str] or None
        ``(experimento, semente, tipo)`` com tipo ``sta`` ou ``fit``, ou
        ``None`` se o nome não for de um resumo.
    """
    match = _NAME.match(name)
    if match:
        kind = "fit" if match["kind"] == ".fit" else "sta"
        return match["exp"], match["seed"], kind
    bare = _NAME_BARE.match(name)
    if bare:
        return bare["exp"], "-", "sta"
    return None


def _num(text: str) -> float:
    """Converta um valor numérico do resumo em ``float``."""
    return float(text)


def parse_sta(text: str) -> list[tuple[str, str, str, str, str]]:
    """Lê os blocos ``Type/Slack/TNS`` de um resumo do Timing Analyzer.

    Parameters
    ----------
    text : str
        Conteúdo do ``.sta.summary``.

    Returns
    -------
    list[tuple[str, str, str, str, str]]
        Tuplas ``(modelo, tipo, relogio, folga, tns)``, valores como
        escritos no arquivo.
    """
    return [
        (m["model"], KINDS[m["kind"]], m["clock"], m["slack"], m["tns"])
        for m in _BLOCK.finditer(text)
    ]


def _worst(values: list[str]) -> str:
    """Devolve o menor valor, mantendo a escrita original."""
    return min(values, key=_num) if values else ""


def seed_rows(
    exp: str, seed: str, blocks: list[tuple[str, str, str, str, str]]
) -> list[list[str]]:
    """Monte as linhas por domínio de uma semente, mais a ``pior``.

    Parameters
    ----------
    exp : str
        Nome do experimento.
    seed : str
        Semente ou ``-``.
    blocks : list[tuple[str, str, str, str, str]]
        Saída de :func:`parse_sta`.

    Returns
    -------
    list[list[str]]
        Linhas na ordem de ``SEEDS_HEADER``.
    """
    ref: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    every: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for model, kind, clock, slack, tns in blocks:
        domain = short_domain(clock)
        if model == REF_MODEL:
            ref[domain][kind] = (slack, tns)
        every[domain][kind].append(slack)
    rows = [_domain_row(exp, seed, d, ref[d], every[d]) for d in sorted(every)]
    rows.append(_worst_row(exp, seed, rows))
    return rows


def _domain_row(
    exp: str,
    seed: str,
    domain: str,
    ref: dict[str, tuple[str, str]],
    every: dict[str, list[str]],
) -> list[str]:
    """Linha de um domínio: modelo lento a 85 C e o pior modelo."""

    def get(kind: str, index: int) -> str:
        return ref.get(kind, ("", ""))[index]

    return [
        exp,
        seed,
        domain,
        get("setup", 0),
        get("setup", 1),
        get("hold", 0),
        get("hold", 1),
        get("recovery", 0),
        get("removal", 0),
        get("mpw", 0),
        _worst(every.get("setup", [])),
        _worst(every.get("hold", [])),
    ]


def _worst_row(exp: str, seed: str, rows: list[list[str]]) -> list[str]:
    """Linha ``pior``: menor folga entre os domínios, TNS em branco."""
    out = [exp, seed, "pior"]
    for col in range(3, len(SEEDS_HEADER)):
        if SEEDS_HEADER[col].endswith("tns_ns"):
            out.append("")
        else:
            out.append(_worst([r[col] for r in rows if r[col] != ""]))
    return out


def parse_fit(text: str) -> dict[str, str]:
    """Lê os campos de ocupação de um resumo do Fitter.

    Parameters
    ----------
    text : str
        Conteúdo do ``.fit.summary``.

    Returns
    -------
    dict[str, str]
        Campo do Quartus para o valor como escrito no arquivo.
    """
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition(" : ")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def fit_row(exp: str, seed: str, fields: dict[str, str]) -> list[str]:
    """Linha de ocupação de uma semente, valores como escritos."""
    return [exp, seed, *(fields.get(k, "") for _, k in FIT_FIELDS)]


def _seed_key(row: list[str]) -> tuple[str, int, int]:
    """Ordena por experimento, semente e deixa ``pior`` por último."""
    seed = int(row[1]) if row[1].isdigit() else 0
    return row[0], seed, int(row[2] == "pior")


def collect(folder: Path) -> tuple[list[list[str]], list[list[str]]]:
    """Lê todos os resumos de uma pasta (sem descer nas subpastas).

    Parameters
    ----------
    folder : pathlib.Path
        Pasta de dados.

    Returns
    -------
    tuple[list[list[str]], list[list[str]]]
        Linhas de folga e linhas de ocupação, já ordenadas.
    """
    seeds: list[list[str]] = []
    fits: list[list[str]] = []
    for path in sorted(folder.glob("*.resumo.txt")):
        parsed = parse_name(path.name)
        if parsed is None:
            continue
        exp, seed, kind = parsed
        text = path.read_text(encoding="utf-8")
        if kind == "fit":
            fits.append(fit_row(exp, seed, parse_fit(text)))
        else:
            seeds.extend(seed_rows(exp, seed, parse_sta(text)))
    seeds.sort(key=_seed_key)
    fits.sort(key=lambda r: (r[0], int(r[1]) if r[1].isdigit() else 0))
    return seeds, fits


def render(header: tuple[str, ...], rows: list[list[str]]) -> str:
    """Escreve o TSV com cabeçalho e linhas."""
    lines = ["\t".join(header)] + ["\t".join(r) for r in rows]
    return "\n".join(lines) + "\n"


def fit_header() -> tuple[str, ...]:
    """Cabeçalho da tabela de ocupação."""
    return ("experimento", "semente", *(n for n, _ in FIT_FIELDS))


def outputs(folder: Path) -> dict[Path, str]:
    """Texto esperado dos TSV de uma pasta, a partir dos resumos.

    Parameters
    ----------
    folder : pathlib.Path
        Pasta de dados.

    Returns
    -------
    dict[pathlib.Path, str]
        Caminho de cada TSV e seu conteúdo (vazio se não há resumos).
    """
    seeds, fits = collect(folder)
    result: dict[Path, str] = {}
    if seeds:
        result[folder / SEEDS_NAME] = render(SEEDS_HEADER, seeds)
    if fits:
        result[folder / FIT_NAME] = render(fit_header(), fits)
    return result


def default_folders() -> list[Path]:
    """Pasta do script e as subpastas que têm resumos."""
    found = [HERE, *(p for p in sorted(HERE.iterdir()) if p.is_dir())]
    return [p for p in found if any(p.glob("*.resumo.txt"))]


HEAD = {
    "pt": ("Semente", "Pior setup (ns)", "Domínio", "Pior hold (ns)"),
    "en": ("Seed", "Worst setup (ns)", "Domain", "Worst hold (ns)"),
}
FIT_HEAD = {
    "pt": ("Semente", "ALMs", "Registradores", "Pinos", "Blocos de RAM"),
    "en": ("Seed", "ALMs", "Registers", "Pins", "RAM blocks"),
}
DECIMAL = {"pt": ",", "en": "."}


def _fmt(value: str, lang: str) -> str:
    """Troque o ponto decimal pelo separador do idioma."""
    return value.replace(".", DECIMAL[lang])


def _read_rows(path: Path, exp: str) -> list[dict[str, str]]:
    """Linhas de um TSV que pertencem ao experimento ``exp``."""
    lines = path.read_text(encoding="utf-8").splitlines()
    cols = lines[0].split("\t")
    rows = [dict(zip(cols, ln.split("\t"), strict=True)) for ln in lines[1:]]
    return [r for r in rows if r["experimento"] == exp]


def _worst_domain(rows: list[dict[str, str]], col: str) -> dict[str, str]:
    """Linha do domínio de menor folga na coluna ``col``."""
    return min((r for r in rows if r[col]), key=lambda r: _num(r[col]))


def markdown(folder: Path, exp: str, lang: str = "pt") -> str:
    """Tabela Markdown de folgas de um experimento, lida do TSV.

    Parameters
    ----------
    folder : pathlib.Path
        Pasta com ``tabela-sementes.tsv``.
    exp : str
        Nome do experimento.
    lang : str
        ``pt`` ou ``en``.

    Returns
    -------
    str
        Uma linha por semente: pior setup e hold (modelo lento a 85 C)
        e o domínio de cada um.
    """
    rows = _read_rows(folder / SEEDS_NAME, exp)
    seed, setup, dom, hold = HEAD[lang]
    out = [
        f"| {seed} | {setup} | {dom} | {hold} | {dom} |",
        "| :--- | ---: | :--- | ---: | :--- |",
    ]
    for sd in sorted({r["semente"] for r in rows}):
        doms = [
            r for r in rows if r["semente"] == sd and r["dominio"] != "pior"
        ]
        s = _worst_domain(doms, "setup_slack_ns")
        h = _worst_domain(doms, "hold_slack_ns")
        out.append(
            f"| {sd} | {_fmt(s['setup_slack_ns'], lang)} | {s['dominio']} | "
            f"{_fmt(h['hold_slack_ns'], lang)} | {h['dominio']} |"
        )
    return "\n".join(out)


def markdown_fit(folder: Path, exp: str, lang: str = "pt") -> str:
    """Tabela Markdown de ocupação de um experimento, lida do TSV.

    Parameters
    ----------
    folder : pathlib.Path
        Pasta com ``tabela-ocupacao.tsv``.
    exp : str
        Nome do experimento.
    lang : str
        ``pt`` ou ``en``.

    Returns
    -------
    str
        Uma linha por semente: ALMs, registradores, pinos e RAM.
    """
    head = FIT_HEAD[lang]
    out = [
        "| " + " | ".join(head) + " |",
        "| :--- | ---: | ---: | ---: | ---: |",
    ]
    out.extend(
        f"| {r['semente']} | {r['alms']} | {r['registradores']} | "
        f"{r['pinos']} | {r['blocos_ram']} |"
        for r in _read_rows(folder / FIT_NAME, exp)
    )
    return "\n".join(out)


def run_check(folders: list[Path]) -> int:
    """Compara o TSV versionado com o recalculado dos resumos.

    Returns
    -------
    int
        Número de divergências.
    """
    bad = 0
    for folder in folders:
        for path, text in outputs(folder).items():
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                print(f"DIVERGE {path}")
                bad += 1
            else:
                print(f"OK {path} ({text.count(chr(10)) - 1} linhas)")
    return bad


def write_all(folders: list[Path]) -> None:
    """Escreve os TSV de cada pasta."""
    for folder in folders:
        for path, text in outputs(folder).items():
            path.write_text(text, encoding="utf-8")
            print(f"escrito {path}")


def main() -> int:
    """Ponto de entrada da linha de comando."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comando", nargs="?", default="gerar")
    parser.add_argument("args", nargs="*")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--lang", default="pt", choices=("pt", "en"))
    ns = parser.parse_args()
    if ns.comando in {"markdown", "markdown-fit"}:
        func = markdown if ns.comando == "markdown" else markdown_fit
        print(func(Path(ns.args[0]), ns.args[1], ns.lang))
        return 0
    paths = ns.args if ns.comando == "gerar" else [ns.comando, *ns.args]
    folders = [Path(p) for p in paths] or default_folders()
    if ns.check:
        return int(run_check(folders) > 0)
    write_all(folders)
    return 0


if __name__ == "__main__":
    sys.exit(main())

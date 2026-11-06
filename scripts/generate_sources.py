"""Escreve as listas de fontes dos topos a partir do ``provides``.

Cada repositório declara no ``paths.yaml`` os componentes que fornece,
as fontes de cada um em ordem de análise e o que cada um requer. O
``riscv-tools sources <componente>`` resolve essa árvore, entre
repositórios, e imprime os arquivos na ordem certa. Este script escreve
essa saída nos arquivos que listam fontes de topo (os ``config*.yaml``,
o ``tests.json`` e os ``.qsf``) e, com ``--check``, falha quando o que
está versionado difere do que o ``provides`` gera.

O que não é lista de fontes (o resto de cada arquivo) é mantido.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Aviso que encabeça cada lista gerada, nos arquivos com comentário.
AVISO = (
    "Lista gerada por `make generate-sources` "
    "(scripts/generate_sources.py) a partir do provides; "
    "não edite à mão."
)

# Fontes que o Quartus lê como VHDL mesmo havendo um .qip ao lado. O
# .qip do PLL também arrasta o pll_0002.v, que o .qsf lista à parte.
COMO_FONTE = {"src/simulation/internal-mem/pll/pll.vhd"}

# Um arquivo VHDL que um .qip inclui.
QIP_VHDL = re.compile(
    r'VHDL_FILE \[file join \$::quartus\(qip_path\) "([^"]+)"\]'
)

# Uma linha do .qsf que declara um arquivo VHDL ou um .qip.
QSF_FONTE = re.compile(r"^set_global_assignment -name (?:VHDL_FILE|QIP_FILE) ")


@dataclass(frozen=True)
class Saida:
    """Um arquivo que contém uma lista de fontes e de onde ela vem.

    Attributes
    ----------
    arquivo : str
        Caminho do arquivo, a partir da raiz do repositório.
    alvos : tuple of str
        Componentes passados ao ``riscv-tools sources``.
    chave : str
        Nome da entrada do ``tests.json``; vazio nos outros tipos.
    extras : tuple of str
        Arquivos que a entrada acrescenta ao fim da lista gerada.
    """

    arquivo: str
    alvos: tuple[str, ...]
    chave: str = ""
    extras: tuple[str, ...] = field(default=())


# Os ``vhdl_sources`` de cada configuração de simulação.
YAMLS = (
    Saida(
        "src/simulation/internal-mem/config.yaml", ("internal_mem_sim_top",)
    ),
    Saida(
        "src/simulation/internal-mem/config.fpga-sim.yaml",
        ("pll_sim", "core_fpga_test"),
    ),
    Saida("src/simulation/template/config.yaml", ("template_sim_top",)),
    Saida(
        "src/simulation/modular/config.yaml",
        ("modular_map", "modular_sim_top"),
    ),
    Saida(
        "src/simulation/test-integrated/config.yaml",
        ("test_integrated_map", "modular_sim_top"),
    ),
    Saida(
        "src/simulation/test-external-data/config.yaml",
        ("test_external_data_map", "modular_sim_top"),
    ),
    Saida(
        "src/simulation/test-external-instruction/config.yaml",
        ("test_external_instruction_map", "modular_sim_top"),
    ),
    Saida(
        "src/simulation/test-external/config.yaml",
        ("test_external_map", "modular_sim_top"),
    ),
    Saida(
        "src/cyclone-v/fpga-integrated/config.yaml",
        ("fpga_integrated_map", "modular_sim_top"),
    ),
    Saida(
        "src/cyclone-v/fpga-external-data/config.yaml",
        ("fpga_external_data_map", "modular_sim_top"),
    ),
    Saida(
        "src/cyclone-v/fpga-external-instruction/config.yaml",
        ("fpga_external_instruction_map", "modular_sim_top"),
    ),
    Saida(
        "src/cyclone-v/fpga-external/config.yaml",
        ("fpga_external_map", "modular_sim_top"),
    ),
    Saida(
        "src/cyclone-v/fpga-uart-jtag/config.yaml",
        ("fpga_uart_jtag_map", "modular_sim_top"),
    ),
    Saida(
        "src/cyclone-v/fpga-uart-pins/config.yaml",
        ("fpga_uart_pins_map", "modular_sim_top"),
    ),
    Saida("src/cyclone-v/de0-cv/config.yaml", ("de0_cv_sim_top",)),
    Saida(
        "src/cyclone-v/external-data/config.yaml", ("external_data_sim_top",)
    ),
)

# Os projetos do Quartus: o PLL de síntese em vez do comportamental.
QSFS = (
    Saida(
        "src/simulation/internal-mem/quartus/core_fpga_test.qsf",
        ("pll_ip", "core_fpga_test"),
    ),
    Saida("src/cyclone-v/de0-cv/de0-cv.qsf", ("de0_cv_top",)),
    Saida(
        "src/cyclone-v/external-data/external-data.qsf",
        ("external_data_top",),
    ),
)

TESTS_JSON = "tests/python/tests.json"

# Entradas do ``tests.json`` cujas fontes vêm do provides, com o que
# cada uma acrescenta (o topo de teste, que não é componente). O
# axi_slave_periph_bank usa a ponte de palavra, que o provides do
# axi_interconnect não requer.
ENTRADAS = (
    Saida(TESTS_JSON, ("modular_map", "modular_sim_top"), "ModularIntegrated"),
    Saida(TESTS_JSON, ("modular_map", "modular_sim_top"), "ModularInterrupts"),
    Saida(
        TESTS_JSON, ("modular_map", "modular_sim_top"), "ModularExternalData"
    ),
    Saida(
        TESTS_JSON,
        ("modular_map", "modular_sim_top"),
        "ModularExternalInstruction",
    ),
    Saida(TESTS_JSON, ("modular_map", "modular_sim_top"), "ModularExternal"),
    Saida(
        TESTS_JSON,
        ("test_integrated_map", "modular_sim_top"),
        "PlatformTestIntegrated",
    ),
    Saida(
        TESTS_JSON,
        ("test_external_data_map", "modular_sim_top"),
        "PlatformTestExternalData",
    ),
    Saida(
        TESTS_JSON,
        ("test_external_instruction_map", "modular_sim_top"),
        "PlatformTestExternalInstruction",
    ),
    Saida(
        TESTS_JSON,
        ("test_external_map", "modular_sim_top"),
        "PlatformTestExternal",
    ),
    Saida(
        TESTS_JSON,
        ("fpga_integrated_map", "modular_sim_top"),
        "PlatformFpgaIntegrated",
    ),
    Saida(
        TESTS_JSON,
        ("fpga_external_data_map", "modular_sim_top"),
        "PlatformFpgaExternalData",
    ),
    Saida(
        TESTS_JSON,
        ("fpga_external_instruction_map", "modular_sim_top"),
        "PlatformFpgaExternalInstruction",
    ),
    Saida(
        TESTS_JSON,
        ("fpga_external_map", "modular_sim_top"),
        "PlatformFpgaExternal",
    ),
    Saida(
        TESTS_JSON,
        ("fpga_uart_jtag_map", "modular_sim_top"),
        "PlatformFpgaUartJtag",
    ),
    Saida(
        TESTS_JSON,
        ("fpga_uart_pins_map", "modular_sim_top"),
        "PlatformFpgaUartPins",
    ),
    Saida(TESTS_JSON, ("de0_cv_sim_top",), "De0CvSimTop"),
    Saida(TESTS_JSON, ("external_data_sim_top",), "ExternalDataSimTop"),
    Saida(TESTS_JSON, ("template_sim_top",), "TemplateSimTop"),
    Saida(
        TESTS_JSON,
        ("Peripherals/jtag_uart", "ext_interconnect"),
        "ExtBus",
        ("tests/vhdl/ext_bus_system.vhd",),
    ),
    Saida(
        TESTS_JSON,
        (
            "Peripherals/jtag_uart",
            "Memory/axi_slave_word_bridge",
            "axi_interconnect",
        ),
        "ExtAxiBus",
        ("tests/vhdl/ext_axi_bus_system.vhd",),
    ),
    Saida(
        TESTS_JSON,
        (
            "Peripherals/jtag_uart",
            "Memory/axi_slave_word_bridge",
            "axi_interconnect",
        ),
        "ExtAxiCache",
        ("tests/vhdl/ext_axi_bus_system.vhd",),
    ),
)


class Fontes:
    """Pergunta ao ``riscv-tools sources`` e guarda as respostas."""

    def __init__(self, raiz: Path, ferramenta: str) -> None:
        """Guarda a raiz e o executável.

        Parameters
        ----------
        raiz : Path
            Raiz do repositório.
        ferramenta : str
            Nome ou caminho do ``riscv-tools``.
        """
        self.raiz = raiz
        self.ferramenta = ferramenta
        self.memoria: dict[tuple[str, ...], list[str]] = {}

    def de(self, alvos: tuple[str, ...]) -> list[str]:
        """Lista as fontes dos alvos, em ordem de análise.

        Parameters
        ----------
        alvos : tuple of str
            Componentes do ``provides``.

        Returns
        -------
        list of str
            Os arquivos, a partir da raiz, dependências primeiro.
        """
        if alvos not in self.memoria:
            exe = shutil.which(self.ferramenta)
            if exe is None:
                sys.exit(f"generate_sources: {self.ferramenta} não achado")
            fim = subprocess.run(  # noqa: S603
                [exe, "--root", str(self.raiz), "sources", *alvos],
                check=False,
                capture_output=True,
                text=True,
            )
            if fim.returncode != 0:
                sys.exit(f"generate_sources: {fim.stderr.strip()}")
            self.memoria[alvos] = fim.stdout.split()
        return self.memoria[alvos]


def reescreve_yaml(texto: str, fontes: list[str]) -> str:
    """Troca a lista ``vhdl_sources`` de uma configuração.

    Parameters
    ----------
    texto : str
        Conteúdo do ``config*.yaml``.
    fontes : list of str
        As fontes geradas.

    Returns
    -------
    str
        O conteúdo com a lista nova e o aviso acima dela.

    Raises
    ------
    ValueError
        Se o arquivo não tem uma lista ``vhdl_sources``.
    """
    padrao = re.compile(
        r"(?:^ *# Lista gerada[^\n]*\n)?"
        r"^( +)vhdl_sources:[ ]*\n((?: +- [^\n]*\n)+)",
        re.MULTILINE,
    )
    achado = padrao.search(texto)
    if achado is None:
        raise ValueError("sem lista vhdl_sources")
    recuo = achado.group(1)
    itens = "".join(f"{recuo}  - {f}\n" for f in fontes)
    novo = f"{recuo}# {AVISO}\n{recuo}vhdl_sources:\n{itens}"
    inicio, fim = achado.span()
    return texto[:inicio] + novo + texto[fim:]


def reescreve_json(texto: str, entradas: dict[str, list[str]]) -> str:
    """Troca as fontes de entradas do ``tests.json``.

    Parameters
    ----------
    texto : str
        Conteúdo do arquivo.
    entradas : dict of str to list of str
        As fontes novas de cada entrada.

    Returns
    -------
    str
        O JSON com recuo de 4 espaços e quebra de linha final.
    """
    dados = json.loads(texto)
    for nome, fontes in entradas.items():
        dados[nome]["sources"] = fontes
    return json.dumps(dados, indent=4, ensure_ascii=False) + "\n"


def cobertos_por_qip(raiz: Path, fontes: list[str]) -> dict[str, str]:
    """Acha os arquivos VHDL que um ``.qip`` vizinho já inclui.

    Parameters
    ----------
    raiz : Path
        Raiz do repositório.
    fontes : list of str
        As fontes do topo.

    Returns
    -------
    dict of str to str
        Para cada arquivo coberto, o ``.qip`` que o inclui.
    """
    cobertos: dict[str, str] = {}
    for pasta in sorted({str(Path(f).parent) for f in fontes}):
        for qip in sorted((raiz / pasta).glob("*.qip")):
            conteudo = qip.read_text("utf-8")
            for nome in QIP_VHDL.findall(conteudo):
                alvo = os.path.normpath(Path(pasta) / nome)
                chave = Path(alvo).as_posix()
                cobertos.setdefault(chave, qip.relative_to(raiz).as_posix())
    return cobertos


def linhas_qsf(raiz: Path, qsf: str, fontes: list[str]) -> list[str]:
    """Monta as linhas de fonte do projeto do Quartus.

    Os arquivos que um ``.qip`` inclui entram pelo ``.qip``, uma vez só.

    Parameters
    ----------
    raiz : Path
        Raiz do repositório.
    qsf : str
        Caminho do ``.qsf``.
    fontes : list of str
        As fontes do topo.

    Returns
    -------
    list of str
        As linhas ``set_global_assignment``, sem quebra de linha.
    """
    cobertos = cobertos_por_qip(raiz, fontes)
    pasta = Path(qsf).parent.as_posix()
    linhas: list[str] = []
    for fonte in fontes:
        qip = cobertos.get(fonte) if fonte not in COMO_FONTE else None
        tipo, caminho = ("QIP_FILE", qip) if qip else ("VHDL_FILE", fonte)
        relativo = Path(os.path.relpath(str(caminho), pasta)).as_posix()
        linha = f"set_global_assignment -name {tipo} {relativo}"
        if linha not in linhas:
            linhas.append(linha)
    return linhas


def reescreve_qsf(texto: str, linhas: list[str]) -> str:
    """Troca as linhas de fonte VHDL e ``.qip`` de um ``.qsf``.

    A lista nova ocupa o lugar da primeira linha de fonte; as demais
    somem e tudo o que não é fonte fica onde estava.

    Parameters
    ----------
    texto : str
        Conteúdo do ``.qsf``.
    linhas : list of str
        As linhas novas.

    Returns
    -------
    str
        O conteúdo com a lista nova.

    Raises
    ------
    ValueError
        Se o arquivo não tem nenhuma linha de fonte.
    """
    saida: list[str] = []
    posto = False
    for linha in texto.splitlines(keepends=True):
        if linha == f"# {AVISO}\n":
            continue
        if not QSF_FONTE.match(linha):
            saida.append(linha)
        elif not posto:
            posto = True
            saida.append(f"# {AVISO}\n")
            saida.extend(f"{nova}\n" for nova in linhas)
    if not posto:
        raise ValueError("sem linhas de fonte")
    return "".join(saida)


def gera(raiz: Path, fontes: Fontes) -> dict[str, str]:
    """Calcula o conteúdo novo de cada arquivo de lista.

    Parameters
    ----------
    raiz : Path
        Raiz do repositório.
    fontes : Fontes
        O consultor do ``riscv-tools sources``.

    Returns
    -------
    dict of str to str
        O conteúdo novo, por caminho de arquivo.
    """
    novos: dict[str, str] = {}
    for saida in YAMLS:
        texto = (raiz / saida.arquivo).read_text("utf-8")
        novos[saida.arquivo] = reescreve_yaml(texto, fontes.de(saida.alvos))
    for saida in QSFS:
        texto = (raiz / saida.arquivo).read_text("utf-8")
        linhas = linhas_qsf(raiz, saida.arquivo, fontes.de(saida.alvos))
        novos[saida.arquivo] = reescreve_qsf(texto, linhas)
    texto = (raiz / TESTS_JSON).read_text("utf-8")
    entradas = {e.chave: [*fontes.de(e.alvos), *e.extras] for e in ENTRADAS}
    novos[TESTS_JSON] = reescreve_json(texto, entradas)
    return novos


def main() -> int:
    """Escreve as listas, ou só confere com ``--check``.

    Returns
    -------
    int
        0 quando está tudo em dia ou foi escrito; 1 quando ``--check``
        acha um arquivo desatualizado.
    """
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--root", default=".", type=Path)
    analisador.add_argument("--tools", default="riscv-tools")
    analisador.add_argument("--check", action="store_true")
    args = analisador.parse_args()
    raiz = args.root.resolve()
    novos = gera(raiz, Fontes(raiz, args.tools))
    velhos = [
        arquivo
        for arquivo, texto in novos.items()
        if (raiz / arquivo).read_text("utf-8") != texto
    ]
    if args.check:
        for arquivo in velhos:
            print(f"desatualizado: {arquivo} (rode make generate-sources)")
        return 1 if velhos else 0
    for arquivo in velhos:
        (raiz / arquivo).write_text(novos[arquivo], "utf-8")
        print(f"escrito: {arquivo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

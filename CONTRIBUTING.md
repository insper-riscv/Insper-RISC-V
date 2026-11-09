# Guia de Contribuição

🌐 [Português](CONTRIBUTING.md) · [English](CONTRIBUTING.en.md)

Este documento define as regras obrigatórias de codificação (VHDL, C e Python), organização estrutural, documentação e verificação para qualquer contribuição ao repositório `Insper-RISC-V`.

## 1. Normas VHDL e Compatibilidade de Síntese

Todo código de hardware do projeto é escrito e validado sob a norma **IEEE 1076-2008 (VHDL-2008)**, compilado no GHDL com a flag `--std=08` e sintetizado no Quartus Prime.

| Regra | Especificação |
| :--- | :--- |
| Norma da linguagem | VHDL-2008 (`--std=08`) em todos os arquivos `.vhd` |
| Pacotes IEEE permitidos | Apenas `ieee.std_logic_1164.all` e `ieee.numeric_std.all` |
| Pacotes proibidos | `std_logic_arith`, `std_logic_unsigned` e `std_logic_signed` nunca devem ser utilizados |
| Instanciação de módulos | Instanciação direta de entidade (`u_nome : entity work.nome_da_entidade`) para todo código do projeto, sem exceção e sem declaração `component`. A única exceção é a lista estreita de primitivas de fabricante sem entidade visível ao VHDL, definida em `vendor_primitives.yaml` do `riscv-tools`; `altsyncram` e `sld_virtual_jtag` (exigem `library altera_mf;`) e `sdram_platform_pll` (sem biblioteca) levam `component`, porque o Quartus Lite 25.1 recusa a instanciação direta delas (erro 10481). PLL gerado e documentado entra em `tree.vhdl_style.exclude` do `paths.yaml` |
| Mapeamento de portas (`port map`) | Associar sempre por nome (`i_porta => sinal`) e utilizar sinais intermediários para expressões lógicas ou fatias dinâmicas, pois o GHDL exige expressões globalmente estáticas nos formais/atuais de porta |
| Inferência de latches | Todo sinal atribuído em processo combinacional ou atribuição condicional deve receber valor padrão explícito em todos os ramos (`else` / `when others =>`) |

A norma de referência é a [IEEE Std 1076-2008, IEEE Standard VHDL Language Reference Manual](https://standards.ieee.org/ieee/1076/3666/). Em trabalhos acadêmicos, cite-a com a entrada BibTeX abaixo:

```bibtex
@misc{ieee1076,
  title        = {IEEE Standard VHDL Language Reference Manual},
  author       = {{IEEE}},
  year         = {2008},
  note         = {IEEE Std 1076-2008},
  howpublished = {\url{https://standards.ieee.org/ieee/1076/3666/}}
}
```

A organização em blocos reutilizáveis com interfaces e parâmetros explícitos segue a [IEEE Std 1685, IEEE Standard for IP-XACT](https://standards.ieee.org/ieee/1685/10583/), cuja entrada BibTeX é:

```bibtex
@misc{ieee1685,
  title        = {IEEE Standard for IP-XACT, Standard Structure for Packaging, Integrating, and Reusing IP within Tool Flows},
  author       = {{IEEE}},
  year         = {2022},
  note         = {IEEE Std 1685-2022},
  howpublished = {\url{https://standards.ieee.org/ieee/1685/10583/}}
}
```

A metodologia de projeto para reuso de blocos de hardware segue o livro *Reuse Methodology Manual for System-on-a-Chip Designs* (3ª edição, Springer, 2002), de Keating e Bricaud, obra com direitos autorais cujo acesso depende de compra ou de biblioteca institucional:

```bibtex
@book{keating2002rmm,
  title     = {Reuse Methodology Manual for System-on-a-Chip Designs},
  author    = {Keating, Michael and Bricaud, Pierre},
  edition   = {3},
  year      = {2002},
  publisher = {Springer},
  isbn      = {978-1402071416}
}
```

## 2. Norma C e Programas de Teste

Todo código em C do projeto, onde quer que esteja (programas de teste, runtime e código de inicialização das plataformas), é escrito sob a norma **ISO/IEC 9899:2024 (C23)** e compilado com a flag `-std=c23`. O C é a linguagem dos programas que exercitam o processador, e é por meio deles que os módulos de hardware são verificados na simulação e na placa.

| Regra | Especificação |
| :--- | :--- |
| Norma da linguagem | C23 (`-std=c23`, nunca `-std=gnu23`) em todos os arquivos `.c` e `.h`; o `riscv-tools` passa a flag em toda compilação |
| Avisos | `-Wall -Wextra -Wpedantic -Werror`, passados pelo `riscv-tools`; nenhum aviso é aceito, e `-Wmissing-prototypes` vale para o runtime |
| Ambiente de execução | Hospedado, com a picolibc da imagem de toolchain do Infra: o runtime e os programas compilam com o `--specs` da plataforma, sem `-ffreestanding`; a norma garante em ambiente freestanding só dez cabeçalhos (cláusula 4), e `<stdio.h>` e `<sys/cdefs.h>` vêm da picolibc |
| Extensões do compilador | Sem extensões GNU quando há equivalente na norma: `[[noreturn]]`, `alignas` e `static_assert` no lugar de `__attribute__`; `[[gnu::weak]]`, `__strong_reference` e `__asm__` só onde a norma não tem equivalente, com um comentário que diga o motivo |
| Tipos e constantes | Tipos de `<stdint.h>` quando a largura importa, `static constexpr` tipado no lugar de `#define` numérico e `nullptr` no lugar de `NULL`; `memory_map.h` e `flash_banks.h` são gerados e lidos por arquivos `.S`, então seguem em `#define` |
| Identificadores reservados | O runtime define `stdin`, `stdout`, `stderr` e `_exit`, que a norma reserva à biblioteca (cláusulas 7.1.3 e 6.4.3); isso só vale em código da própria libc do runtime, e o arquivo diz que é implementação |
| Parâmetro não usado | Parâmetro sem nome na definição (cláusula 6.9.2), e não `(void)nome;` |
| MMIO, deslocamentos, alias e assembly | As regras da seção 1.1 do `CONTRIBUTING.md` do repositório `Testes` valem para todo C deste repositório |
| Nomenclatura e comentários | Identificadores em **inglês** com `snake_case`, tipos com sufixo `_t`; comentário em **português** acima de cada função, variável global, constante e macro |
| Biblioteca padrão | picolibc, conforme a imagem de toolchain do Infra |

A norma de referência é a [ISO/IEC 9899:2024, Programming languages: C](https://www.iso.org/standard/82075.html). Em trabalhos acadêmicos, cite-a com a entrada BibTeX abaixo:

```bibtex
@misc{iso9899,
  title        = {Programming languages --- C},
  author       = {{ISO/IEC}},
  year         = {2024},
  note         = {ISO/IEC 9899:2024},
  howpublished = {\url{https://www.iso.org/standard/82075.html}}
}
```

## 3. Nomenclatura e Prefixos Obrigatórios em VHDL

Todos os identificadores de código devem ser escritos em **inglês**, enquanto todos os comentários e cabeçalhos devem ser escritos em **português**.

| Elemento VHDL | Convenção | Exemplos |
| :--- | :--- | :--- |
| Entidades, arquiteturas e pacotes | `snake_case` | `ext_interconnect`, `axi_router`, `modular_map_pkg`, `rtl` |
| Portas de entrada (`in`) | Prefixo obrigatório `i_` + `snake_case` | `i_clk`, `i_addr`, `i_byteena`, `i_rden` |
| Portas de saída (`out`) | Prefixo obrigatório `o_` + `snake_case` | `o_m_addr`, `o_m_byteena`, `o_m_rden` |
| Generics | `snake_case` descritivo | `data_width`, `addr_width` |
| Constantes (`constant`) | `UPPER_SNAKE_CASE` | `HAS_M`, `HAS_ZMMUL` |
| Tipos e subtipos (`type`, `subtype`) | `snake_case` com sufixo `_t` | `state_t` |
| Sinais e variáveis internas | `snake_case` | `is_periph`, `sel_wb`, `wr_act` |
| Rótulos de instância | Prefixo `u_` + `snake_case` | `u_core`, `u_ext_interconnect` |
| Rótulos de generate | Prefixo `gen_` + `snake_case` | `gen_has_m`, `gen_lanes` |
| Rótulos de processo | Prefixo `p_` + `snake_case`, obrigatório em todo processo e repetido em `end process` | `p_regs`, `p_next_state`, `p_sync_done` |

## 4. Cabeçalhos (Headers) e Docstrings em VHDL

### 4.1. Cabeçalho Obrigatório de Arquivo

Todo arquivo `.vhd` deve iniciar com um bloco de cabeçalho (`-- ====...====`) em português descrevendo a responsabilidade arquitetural do pacote ou da entidade. Nenhuma linha de VHDL passa de 120 caracteres, o padrão do VSG, e nenhum arquivo passa de 2000 linhas nem processo de 500:

```vhdl
-- ============================================================================
-- <Título curto do pacote ou entidade>
-- ============================================================================
-- <Descrição clara em português da função do módulo no processador,
--  interfaces principais, invariantes de ciclo/latência ou parâmetros.>
-- ============================================================================
```

Seções internas de uma arquitetura devem utilizar separadores com hífens simples (`-- ----...----`).

### 4.2. Docstring Individual Acima de Cada Declaração

Cada declaração individual de `generic`, `port`, `constant`, `subtype`, `type`, `signal`, `alias` e `variable` deve possuir seu próprio comentário descritivo em português imediatamente na linha acima. Comentários na mesma linha (inline ao final da linha) não substituem a docstring acima da declaração:

```vhdl
entity mux_2x1 is
    generic(
        -- Largura em bits dos barramentos de entrada e saída
        data_width : natural := 32
    );
    port(
        -- Entrada selecionada quando i_sel vale '0'
        i_d0  : in  std_logic_vector(data_width - 1 downto 0);
        -- Entrada selecionada quando i_sel vale '1'
        i_d1  : in  std_logic_vector(data_width - 1 downto 0);
        -- Bit seletor entre i_d0 ('0') e i_d1 ('1')
        i_sel : in  std_logic;
        -- Saída multiplexada resultante
        o_out : out std_logic_vector(data_width - 1 downto 0)
    );
end entity mux_2x1;
```

## 5. Projeto para Reuso e Proibição de Duplicação

O projeto segue a prática de *Design for Reuse* descrita no *Reuse Methodology Manual* (Keating e Bricaud). Cada regra abaixo se traduz em um critério verificável em revisão:

| # | Regra | Critério de revisão |
| :--- | :--- | :--- |
| 1 | **Blocos de propósito único:** separar controle, caminho de dados e interface de protocolo em entidades distintas | Uma entidade com mais de uma função deve ser dividida; um topo estrutural apenas conecta instâncias |
| 2 | **Parametrização por `generic` e constantes de pacote:** nenhuma largura, profundidade ou recurso fixado dentro da arquitetura | Nenhum literal mágico na lógica; códigos, endereços e seletores residem em pacotes de constantes |
| 3 | **Interfaces padronizadas e intercambiáveis:** entidades com a mesma assinatura de portas podem ser trocadas sem alterar quem as instancia | Trocar a arquitetura de um bloco não pode mudar suas portas nem seu comportamento observável de fora |
| 4 | **Portas enxutas:** a entidade expõe somente as portas e os generics que usa | Sinais ou generics "para uso futuro" não entram em uma entidade |
| 5 | **Dependência apenas das portas:** o nível superior conhece a declaração da entidade, nunca detalhes internos de sua arquitetura | O topo nunca carrega lógica fina de implementação |
| 6 | **Composição com blocos-folha já verificados:** reaproveitar primitivos existentes | Não reimplementar com processos ou operadores redundantes o que um primitivo ou um sinal já calculado fornece |
| 7 | **O topo só conecta:** cada plataforma em `src/<família>/<plataforma>/` instancia Core, Memory e Peripherals, e a lógica de um bloco mora no repositório dono dele | Nenhum bloco reutilizável é definido numa plataforma; ele vai para o repositório dono e entra como submódulo |

## 6. Normas Python

O código Python (runner e testes em `tests/python/`) segue o [PEP 8](https://peps.python.org/pep-0008) (estilo) e o [PEP 257](https://peps.python.org/pep-0257) (docstrings); o `ruff` verifica ambos (regras `E`, `W`, `N` e `D`).

### 6.1. Estilo de Código (PEP 8)

> **Desvio do PEP 8:** O PEP 8 manda escrever comentários em inglês, e este projeto os escreve em **português**. Todas as demais recomendações do PEP 8 sobre comentários se mantêm, ou seja, frases completas, sempre atualizadas e sem repetir o que o código já diz. Identificadores continuam em inglês.

| Regra | Especificação |
| :--- | :--- |
| Indentação | 4 espaços por nível; tabulações proibidas |
| Codificação | UTF-8, sem declaração de encoding no arquivo |
| Largura de linha | Máximo de 79 caracteres para código; 72 para docstrings e comentários |
| Nomenclatura | `snake_case` para funções, métodos, variáveis e módulos; `PascalCase` para classes; `UPPER_SNAKE_CASE` para constantes; prefixo `_` para nomes internos |
| Imports | No topo do arquivo, um por linha, em três grupos separados por linha em branco (biblioteca padrão, terceiros, projeto), cada grupo em ordem alfabética; imports absolutos (relativos proibidos); `import *` proibido |
| Linhas em branco | Duas entre definições de nível de módulo; uma entre métodos |
| Espaços | Um espaço ao redor de operadores e após vírgulas; nenhum espaço antes de `(` de chamada, dentro de colchetes ou ao final da linha |
| Comparações | `is` e `is not` para `None`; `if seq:` em vez de `if len(seq):`; nunca `== True` ou `== False` |
| Exceções | `except` sempre com a exceção específica; `except:` sem tipo proibido |
| Comentários | **Em português** (desvio do PEP 8); frases completas, com inicial maiúscula, em linha própria ou após dois espaços no fim do código, iniciados por `# `; explicam o porquê, não repetem o que o código faz |
| Idioma | Identificadores em **inglês**; comentários em **português** |

### 6.2. Docstrings (PEP 257)

| Regra | Especificação |
| :--- | :--- |
| Escopo | Todo módulo, classe, função e método públicos tem docstring |
| Delimitador | Aspas triplas duplas (`"""`), inclusive em docstrings de uma linha |
| Resumo | Primeira linha na mesma linha das aspas de abertura, no modo imperativo, terminada em ponto |
| Docstring de uma linha | Aspas de fechamento na mesma linha, sem linha em branco antes ou depois do texto |
| Docstring de várias linhas | Resumo, linha em branco, descrição detalhada; aspas de fechamento sozinhas na última linha |
| Classes | Docstring na classe, não no `__init__`; linha em branco após a docstring |
| Seções | Estilo NumPy (`Parameters`, `Returns`, `Raises`, `Examples`), com o tipo repetindo a anotação |
| Idioma | Português |

```python
def fetch_user(user_id: str, include_roles: bool = False) -> User:
    """Busca um usuário pelo identificador.

    Parameters
    ----------
    user_id : str
        Identificador único do usuário.
    include_roles : bool, optional
        Inclui a lista de papéis na resposta, por padrão False.

    Returns
    -------
    User
        Dados do usuário.
    """
```

### 6.3. Ferramentas e Processo

| Regra | Especificação |
| :--- | :--- |
| Gerenciador | `uv` (`uv add`, `uv sync`, `uv run`); `pip`, `pip install` e `python -m pip` são proibidos |
| Testes | `pytest`; todo comportamento novo acompanha um teste |
| Tipagem | Anotações completas, verificadas pelo Pyright e pelo Pyrefly, ambos em modo `strict` |
| Estilo e qualidade | `ruff` para lint e formatação; `pylint` com nota mínima 10; `deptry` para dependências declaradas e usadas |
| Complexidade e duplicação | `complexipy` com máximo de 10 por função; `codeclone` para código duplicado |
| Segurança | `semgrep` para análise estática; `uv audit` para vulnerabilidades nas dependências |

## 7. Regras de Documentação Markdown

`README`, `CONTRIBUTING` e `AUTHORS` mantêm versões espelhadas em português (`*.md`) e em inglês (`*.en.md`), e a documentação em `docs/` mantém as pastas espelhadas `docs/pt-br/` e `docs/en/`, obedecendo às seguintes regras:

1. **Seletor de idioma e rodapé de licença:** todo `README.md` e `README.en.md` traz no topo o seletor `🌐 [Português](...) · [English](...)`, e todo arquivo `.md` encerra com o rodapé de copyright e link para `LICENSE`.
2. **Seções numeradas e progressivas:** todas as seções a partir de `##` devem ser numeradas (`## 1.`, `### 1.1.`, `## 2.`) em ordem lógica de leitura.
3. **Pontuação direta:**
   - **Proibido o uso de travessão** em prosa ou tabelas; utilize vírgula, parênteses, ponto e vírgula ou dois-pontos conforme a relação sintática real.
   - **Proibidos dois-pontos encadeados** (mais de um `:` na mesma frase ou célula de tabela).
4. **Explicação de comportamento:** nunca cite o nome de um arquivo, módulo ou sinal interno como se o próprio nome explicasse o que o sistema faz; descreva sempre a operação realizada.
5. **Tabelas e LaTeX sem redundância:** dados estruturados devem estar em tabelas Markdown e expressões matemáticas/lógicas em blocos LaTeX (`$$ ... $$` ou `$ ... $`), sem repetir em prosa o que a tabela ou equação já enuncia.
6. **Sem histórico ou pendências na documentação técnica:** documentos de arquitetura e contratos descrevem exclusivamente o estado atual, sem changelogs internos nem listas de tarefas futuras.
7. **Guias de uso apenas instruem:** instruções de instalação e execução dizem como fazer, sem justificar a escolha do método.
8. **Sem logs de ferramentas:** nenhum log de ferramenta (Quartus, GHDL, sby) é versionado, só os scripts que o geram e os resumos (`*.resumo.txt`) que a documentação cita.

## 8. Verificação Obrigatória Antes de Abrir Pull Request

Qualquer alteração em código, configuração ou documentação deve passar sem erros pelos comandos abaixo antes do envio:

```bash
git submodule update --init --recursive  # Inicializa todos os submódulos nas versões fixadas
make all                                 # Executa paths, verificação de integração, testes e provas formais próprios deste repositório
make generate-check                      # Confere que os arquivos gerados a partir de cada platform.yaml estão em dia
make sources-check                       # Confere que as listas de fontes dos topos são as que o provides gera
```

Cada repositório roda só as próprias verificações, os próprios testes cocotb e as próprias provas formais, no CI de cada um. O Insper-RISC-V roda só o que é dele ou de integração: os caminhos do `paths.yaml`, a construção dos topos de simulação com os submódulos fixados, a unicidade dos nomes entre repositórios, o mapa de memória, os testes cocotb das plataformas e a prova formal do interconector. Uma alteração em um submódulo é validada no repositório dele, não aqui.

Quando um `platform.yaml` muda, rode `make generate` e versione os arquivos que ele gera.

As listas de fontes dos topos (os `config*.yaml`, o `tests/python/tests.json` e os `.qsf`) não se editam à mão: `make generate-sources` as escreve a partir do `provides` do `paths.yaml` de cada repositório, pelo `riscv-tools sources`, e `make sources-check` (parte do `make check` e do `make unit-tests`) falha quando a lista versionada difere da gerada. Um arquivo novo de um submódulo entra nos topos ao ser registrado no `provides` do próprio submódulo; depois de atualizar o ponteiro do submódulo, rode `make generate-sources` e versione o resultado.

O job `formal` do CI roda as provas uma vez por engine (`formal - yices`, `formal - bitwuzla`, `formal - boolector` e `formal - abc-bmc3`) e o job agregador `formal` decide a partir dos resultados: cada prova precisa ter uma resposta e os engines que responderam precisam concordar entre si e com o esperado. O nome `formal` é o check que o ruleset da branch padrão exige, então não o renomeie; os jobs `formal - <engine>` não são exigidos.

Warning no formal é erro. O fluxo de verificação formal varre a saída do GHDL e os logs do Yosys e do SymbiYosys depois de cada passo, inclusive nos mutantes, e falha apontando o arquivo e a linha do aviso. A correção é sempre no código ou nas propriedades, nunca em uma opção que esconda o aviso (`-Wno-*`). Os detalhes estão em [docs/pt-br/interconnect/ext_interconnect.md](docs/pt-br/interconnect/ext_interconnect.md).

O job `python-static-analysis` do CI roda `ruff`, `pycodestyle`, `pydocstyle`, `pylint`, `pyright`, `pyrefly`, `deptry`, `complexipy`, `codeclone`, `semgrep` e `uv audit` sobre os arquivos Python, e o nome do job é o check que o ruleset da branch padrão exige, então não o renomeie.

O job `boot-memory-images` do CI monta de novo, na imagem `ci-elf`, as imagens de teste da boot memory (`tests/python/unittests/rtl/data/de0_cv_boot/images.json` e `external_data/boot_memory_real.hex`) a partir da `boot_memory.S` e falha se o resultado diferir do que está versionado. Depois de mudar a boot memory, regere os dois com `tests/python/gen_de0_cv_boot_images.py` e `tests/python/gen_external_data_images.py` e versione o resultado.

Ao adicionar, renomear ou remover qualquer arquivo versionado, atualize imediatamente:
- `paths.yaml`
- os ponteiros dos submódulos
- `src/*/*/platform.yaml` e os arquivos que `make generate` produz a partir dele
- `docs/`
- `README.md`, `README.en.md` e a documentação afetada

O CI roda essas verificações a cada push. Num pull request de alguém de fora do projeto, ele só começa depois que um membro que pode fazer o merge aprova a execução na página do pull request.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](LICENSE).

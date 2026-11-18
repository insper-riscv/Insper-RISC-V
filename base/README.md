# base

🌐 [Português](README.md) · [English](README.en.md)

A pasta `base/` reúne o que todo projeto gerado a partir do Insper-RISC-V compartilha, independente de placa: o SoC, o interconector externo e o código de boot. Ela fica na raiz, fora de `src/` (que guarda as plataformas) e de `templates/` (que guarda os esqueletos de software), e é a única fonte desses arquivos. Nenhuma plataforma guarda cópia deles; todas os leem por caminho relativo.

## 1. Conteúdo

| Caminho | Responsabilidade |
| :--- | :--- |
| `src/soc/soc.vhd` | O sistema em chip sem pino de placa, nome de família nem modelo de chip, que liga o núcleo, as caches, o interconector, o CLINT, o PLIC e os periféricos de E/S |
| `src/interconnect/` | O interconector externo (nativo e AXI4), que decodifica a tabela de janelas da plataforma entre a memória do barramento e os periféricos, e o pacote com os tipos e as funções de decodificação |
| `src/boot/boot_core.S` | A BOOT_MEMORY comum, incluída pelo `boot_memory.S` de cada plataforma |

## 2. Quem usa

Os componentes `soc`, `ext_interconnect`, `interconnect_pkg` e `axi_interconnect` são declarados no `provides` do `paths.yaml` da raiz, com os arquivos apontando para esta pasta. As plataformas em `src/` requerem esses componentes pelo nome e incluem o `boot_core.S` pelo caminho relativo. Os tops de simulação e os testbenches de cada plataforma ficam em `src/` e não entram aqui.

A documentação de cada parte está em [docs/pt-br/soc/soc.md](../docs/pt-br/soc/soc.md), [docs/pt-br/interconnect/ext_interconnect.md](../docs/pt-br/interconnect/ext_interconnect.md) e [docs/pt-br/platform/boot.md](../docs/pt-br/platform/boot.md).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../LICENSE).

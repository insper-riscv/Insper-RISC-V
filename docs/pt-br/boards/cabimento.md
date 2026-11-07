# Cabimento do perfil na placa

## 1. Dois estágios

O Tools verifica se o perfil escolhido, com os backends, as caches e os periféricos pedidos, cabe na placa. O estimador rápido roda sem o Quartus, e a confirmação autoritativa lê os resumos que o próprio Quartus escreve.

| Estágio | Entrada | Roda em |
| :--- | :--- | :--- |
| Estimador | `platform.yaml`, perfil resolvido e tabela de calibração da família | `check-memory-map`, `board generate` e antes de `program` e `run`; também no CI sem Quartus |
| Autoritativo | Resumos do ajuste (`*.fit.summary`) | Depois da compilação do `program`, e `check-fit` sobre uma pasta de relatórios |

## 2. Capacidades

As capacidades da placa estão em `resources` do `board.yaml`.

| Recurso | Campo | Unidade |
| :--- | :--- | :--- |
| Lógica | `resources.logic.total` | ALM (Cyclone V) ou LE de LUT4 (demais famílias); nenhuma unidade converte na outra por fator fixo |
| RAM interna | `resources.block_ram` | Blocos e bits por bloco |
| Multiplicadores | `resources.multipliers` | Elementos do dispositivo, na unidade do Quartus |
| PLLs | `resources.plls` | Contagem |
| Pinos | `resources.user_pins` | Pinos de usuário do pacote |

Uma capacidade `null` é desconhecida, e o estimador a ignora com o aviso V18.

## 3. Estimativa

O estimador soma o custo de cada bloco do perfil com a tabela de calibração da família. Com $\hat{L}$ a lógica estimada na unidade da família e $r$ a razão entre o ajuste e a síntese,

$$ \hat{L} = r \left( L_{nucleo} + \sum_{e} L_e + L_{hpm}(n, w) + \sum_{c \in \{i, d\}} L_c(s_c) + \sum_{p} L_p + \sum_{b} L_b \right) $$

| Termo | Significado | Forma do custo |
| :--- | :--- | :--- |
| $L_{nucleo}$ | Núcleo base (`rv32i` ou `rv32e`) | Constante por família e por base |
| $L_e$ | Extensão ou extra (M, Zmmul, Zicsr, Zicntr, Zifencei, Zicclsm, Zimop, Zicond, Zihintntl, Zihintpause, interrupções, Sscofpmf) | Constante por extensão |
| $L_{hpm}$ | Zihpm com $n$ contadores de $w$ bits | $a_0 + a_1 n + a_2 n w$ |
| $L_c$ | Cache de instruções ou de dados de $s_c$ kbit | $c_0 + c_1 s_c$ |
| $L_p$ | Periférico | Constante por periférico, que fica dentro do termo do núcleo quando a plataforma de medida o inclui em toda medida |
| $L_b$ | Controlador de backend de dispositivo | Constante por tipo e largura |

As implicações da ISA valem na estimativa: Zicntr e Zihpm implicam Zicsr, M implica Zmmul, e Sscofpmf exige Zihpm e interrupções. A memória emulada custa blocos, não lógica, e o número de blocos é o da seção 6 de [arquitetura.md](arquitetura.md).

A tabela de calibração é medida e não escrita à mão, e cada família tem a sua em `boards/calibration/<família>.yaml` ([calibracao.md](calibracao.md)): a unidade, os coeficientes, o erro e o Fmax por grau. Um coeficiente `null` é uma medida ainda não feita e faz o estimador emitir V18. As chaves de extensões, extras, periféricos e controladores vêm dos catálogos do Core e do `platform.yaml`, e uma chave fora deles é recusada.

## 4. Política

Seja $u$ a utilização de um recurso, o estimado sobre o total.

| Utilização | Resultado | Motivo |
| :--- | :--- | :--- |
| $u \le 0{,}85$ | Passa | Folga acima do erro esperado |
| $0{,}85 < u \le 1{,}00$ | Aviso | O estimador erra algumas unidades percentuais; só o ajuste decide |
| $u > 1{,}00$ | Erro | Excede a capacidade mesmo com erro favorável |

Os limiares são constantes do Tools e valem para blocos de RAM, lógica, multiplicadores, PLLs e pinos, nos dois estágios; não há opção de forçar o resultado. A lógica estimada só falha quando a família está validada, isto é, o erro máximo de validação da tabela é de até 10 %. Antes disso vale o aviso V18, e o ajuste decide. O aviso de frequência (V8) compara `clocks.core.mhz` com o Fmax medido da família e nunca falha.

## 5. Regras

| Regra | Origem | Gravidade |
| :--- | :--- | :--- |
| V11 | Blocos de RAM da memória emulada e das caches | Erro; aviso entre 85 % e 100 % |
| V12 | Lógica estimada acima da capacidade | Erro |
| V13 | Lógica estimada entre 85 % e 100 % | Aviso |
| V14 | Relatório do ajuste estoura recursos; todos são listados de uma vez | Erro; aviso na faixa de 85 % a 100 % |
| V18 | Família sem calibração, capacidade `null` ou coeficiente `null` | Aviso |

## 6. Comando

```bash
riscv-tools --root . check-fit --reports <pasta com *.fit.summary> --board boards/<placa>/board.yaml
```

O comando lista todos os recursos que passam da capacidade e sai com status 1 quando há erro. O módulo `fit_estimate` do [Tools](https://github.com/insper-riscv/Tools) traz as funções e os testes.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).

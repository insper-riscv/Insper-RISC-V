# O roteador podia enviar um beat de dado de escrita duas vezes

## 1. Resumo

A primeira versão do roteador AXI4-Lite oferecia W ao escravo no clock em que AW era oferecido, antes de saber se AW tinha sido aceito. Se o escravo aceitasse W e não AW nesse clock, o roteador não tinha registro do handshake de W e oferecia W de novo depois de AW ser aceito.

| | |
| :--- | :--- |
| Sintoma | Nenhum em teste algum: achado pela leitura das regras de handshake antes de o roteador ter testes |
| Causa | O dado de escrita seguia a decisão do endereço, mas o seu handshake era registrado só junto com o handshake do endereço |
| Correção | W só é oferecido no clock em que o handshake de AW termina, ou depois dele, e o handshake de W é registrado no mesmo clock do de AW, ou em estado próprio depois |
| Teste | `AxiRouter`, neste repositório: W antes de AW, W com AW e escritas em sequência. O mutante que oferece W com um AW ainda não aceito falha |

## 2. O mecanismo

Um escravo com `awready` em nível baixo e `wready` em nível alto aceita W sozinho, o que a especificação permite. Um roteador que oferece W em todo clock em que AW é oferecido termina então o handshake de W sem registro dele. Quando AW finalmente é aceito, o roteador acredita que W ainda está pendente e o oferece de novo, e o escravo recebe dois beats de dado para um endereço.

## 3. Como evitar

Todo handshake de canal que pode terminar sozinho precisa ser registrado no clock em que termina. Uma decisão tomada a partir de um canal (aqui, o endereço) não pode deixar outro canal terminar antes de a decisão ser guardada.

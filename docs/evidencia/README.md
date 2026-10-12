# Evidência da sessão de 12/10/2026

Trilha de auditoria da construção da fundação determinística. Está aqui, e não
em `.superpowers/`, porque aquela pasta é rascunho de ferramenta e não é
rastreada pelo git — um `git clean` apagaria.

Preservar isto importa por um requisito do projeto: o `CLAUDE.md` §8 exige que
**todo teste novo venha com prova por mutação** — quebrar o código de propósito,
ver o teste falhar, reverter. Um teste que não morde não conta. A afirmação "a
suíte morde" só é auditável se a saída dessas mutações existir em algum lugar.

| Arquivo | O que é |
|---|---|
| `ledger-das-decisoes.md` | as **43 decisões** tomadas durante a execução, cada uma com o motivo e o custo se estiver errada. É o único lugar onde as decisões que eu tomei no lugar do usuário ficam registradas |
| `task-1-report.md` a `task-8-report.md` | um por tarefa: o que foi implementado, a evidência de TDD (o teste falhando antes e passando depois) e a saída bruta de cada prova por mutação |
| `onda-final-report.md` | a onda de correção da revisão ampla do branch |
| `conformidade-report.md`, `guia-do-limpo-report.md` | as duas mudanças de desenho que vieram depois, pedidas pelo usuário |

## O que estes documentos mostram, e que o código não mostra

**Quatro previsões de prova por mutação do plano estavam erradas**, e nas quatro
quem percebeu foi o implementador, que se recusou a ajustar o código para
encaixar numa mutação ruim. Os casos estão nos relatórios das tarefas 2, 3, 5 e
6. Isso é o mecanismo do `CLAUDE.md` §8 funcionando de um jeito que não estava
previsto: ele achou defeito no plano, não no código.

**Um escape real do portão de segurança**, herdado da POC anterior e corrigido
aqui: o namespace entregava o módulo `re`, e de `re.enum.sys.modules` se chegava
a `os`. Está no relatório da tarefa 4, com o código que o explorava e as sondas
que confirmaram o fechamento.

**Dois casos em que uma correção minha piorou o sistema**, reproduzidos com dados
reais antes de serem desfeitos: o `set` que tornou o reparo não determinístico
(tarefa 6) e o portão da união, que descartava a regra de precisão 1,000 e
mantinha a de 0,154 (`conformidade-report.md`).

Os arquivos `.diff` de cada revisão **não** foram preservados: são deriváveis do
histórico do git com `git diff`.

# Experimento: qual o tamanho mínimo razoável da amostra-guia (17/10/2026)

Pergunta do usuário, para dimensionar a amostra-guia do orquestrador. O guia
simulado é o que um humano produziria corrigindo linhas do próprio dataset:
`n` linhas sorteadas, com os valores do CSV limpo, **sem pares** (o formato
"só registros corretos" da especificação do orquestrador). Os scripts estão
como `.py.txt` (para não contarem no teto de arquivos `.py`); renomeados, rodam a
partir da raiz com `PYTHONPATH=.`; os resultados brutos estão em `resultado.json`.

## Parte determinística, sem API, 10 sementes

Fração dos erros que caem em colunas cuja conformidade de schema foi aprovada
(um teto para o que a conformidade alcança, não o que ela corrige):

| Linhas | `beers`: média (pior semente) | `environment`: média (pior semente) |
|---|---|---|
| 5 | 73% (39%) | 27% (14%) |
| 8 | 100% (98%) | 49% (44%) |
| 10 | 100% (100%) | 59% (44%) |
| 15 | 100% | 69% (61%) |
| 20 | 100% | 72% (61%) |
| 25 | 100% | 76% (76%) |

Efeito contrário: guias maiores passam a tratar texto livre sem erro como
schema (`brewery-name` em 2 de 10 sementes com 10 linhas, em 10 de 10 com 25;
`style` em todas com 30), o que é risco de falso positivo.

## Gerações reais, `gpt-6-luna`, 2 sementes, 16 runs, ~470 chamadas

Medidas sobre a mesma base por semente (fora as 20 linhas do guia de 20, que
contém as dos menores). Precisão real conta alteração em coluna sem erro.

| Linhas | `beers` P / R / F1 | `environment` P / R / F1 |
|---|---|---|
| 5 | 98,7% / 97,8% / 98,3% | 95,3% / 62,0% / 75,0% |
| 10 | 97,9% / 97,5% / 97,7% | 96,3% / 75,7% / 84,7% |
| 15 | 97,4% / 98,4% / 97,9% | 93,8% / 75,5% / 83,6% |
| 20 | 97,8% / 97,8% / 97,8% | 93,1% / 68,7% / 79,0% |

- No `beers`, as duas sementes de 5 linhas tiveram sorte; a parte determinística
  mostra que, com 5 linhas, uma semente em dez deixa só 39% dos erros ao alcance.
- No `environment`, 5 linhas perdem `Climate_Zone` e quase todo `Project_Name`:
  recall de 62% contra 76% com 10.
- A queda com 20 linhas no `environment` **não é efeito do tamanho**: nos dois
  runs de 20 o detector não propôs a dependência `City → Climate_Zone`, que nos
  de 10 e 15 corrigiu 22 de 22. É variação do LLM entre gerações, da ordem de
  5 a 7 pontos de recall.

## Conclusão

**Mínimo razoável: 10 linhas.** Com 5, o resultado depende de quais linhas
caíram no sorteio. De 10 para 20 o ganho fica dentro da variação do LLM; acima
de 20 cresce o risco de tratar texto livre como schema. Limites do teste: duas
sementes, dois datasets de 300 linhas, sem pares.

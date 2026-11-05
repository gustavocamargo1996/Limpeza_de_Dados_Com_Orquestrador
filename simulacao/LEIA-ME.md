# Simulação: dataset e guia prontos para a interface

Dois datasets de benchmark, de 300 linhas cada, com o guia já corrigido. O guia simula o
humano que corrigiu as linhas sorteadas: os valores vêm do gabarito (o CSV limpo do
benchmark). Os arquivos foram gerados com as mesmas funções do app (`amostra.sortear` e
`amostra.template`, semente `20261017`), por isso as linhas do guia são exatamente as que
a tela vai sortear.

| Dataset | Arquivo para a ingestão | Domínio sugerido | Guia corrigido | Células que o guia corrige |
|---|---|---|---|---|
| beers | `beers_sujo.csv` | Outros | `beers_guia_corrigido.csv` | 31 |
| environment | `environment_sujo.csv` | Meio Ambiente | `environment_guia_corrigido.csv` | 24 |

## Passo a passo

1. Suba o SeaweedFS (`.\subir_seaweed.cmd`) e o app
   (`.venv\Scripts\streamlit run orquestrador\app.py`), da raiz do repositório.
2. **Ingestão:** envie `<dataset>_sujo.csv` e escolha o domínio.
3. **Esquema novo:** dê um nome, por exemplo `beers`.
4. **Amostra-guia:** mantenha **20 linhas** e **não use "Sortear de novo"**. Se mudar o
   sorteio, o app recusa o template, porque as linhas deixam de bater. Na aba
   **Template**, envie `<dataset>_guia_corrigido.csv`.
5. **Erros fora destas linhas (opcional):** dá para digitar alguns pares na grade. São
   erros reais, fora das 20 linhas:

   | Dataset | linha | coluna | limpo |
   |---|---|---|---|
   | beers | 0 | ounces | `12` |
   | beers | 12 | abv | `0.069` |
   | beers | 0 | ibu | *(em branco: o certo é vazio)* |
   | environment | 0 | Temperature | `22.2` |
   | environment | 1 | State | `KA` |
   | environment | 2 | Monitoring_Station_ID | `NewYork_001` |

6. **Confirmar guia** e, na tela seguinte, escolha a base da geração e clique
   **Iniciar geração**.

## Atenção: custo

Com `PROVEDOR=openai` no `.env`, a geração gasta API (cerca de 30 chamadas, centavos de
dólar) e manda linhas da tabela para a OpenAI. Sem gastar nada, dá para ir até a tela de
parâmetros. Com `PROVEDOR=gravado`, a geração não funciona com este guia: as respostas
gravadas são de outro guia.

Este guia não é o do MVP (`dados/guia/beers/`). As linhas são outras, então os números
podem diferir dos de `docs/CONTINUACAO.md` §7.

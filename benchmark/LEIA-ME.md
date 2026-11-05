# Benchmarks: sujo, guia e limpo

Cinco datasets clássicos de limpeza de dados, prontos para testar o gerador de
limpadores. Cada pasta tem:

| Arquivo | O que é | Quem usa |
|---|---|---|
| `sujo.csv` | a tabela com erros, a entrada do gerador | a **geração** |
| `guia/` | `guia_linhas.csv` (20 linhas já corrigidas, com a coluna `_linha`), `guia_pares.csv` (até 2 erros apontados por coluna, como `sujo → limpo`) e `guia_receita.txt` (como o guia foi sorteado) | a **geração** |
| `limpo.csv` | o **gabarito**: a mesma tabela, toda correta | só a **medição** |

**O gabarito nunca entra na geração.** Passe ao gerador só o `sujo.csv` e a pasta
`guia/`. O `limpo.csv` serve apenas para medir, depois, se o limpador gerado é bom. Se
ele entrar na geração, o número medido deixa de valer.

| Dataset | Linhas | Colunas | Células erradas | Colunas com erro | Pares no guia | Tipo de erro |
|---|---|---|---|---|---|---|
| `beers` | 300 | 11 | 495 | 5 | 10 | formato (`12.0 oz` → `12`, `0.069%` → `0.069`), ausência disfarçada (`N/A` → vazio), sigla do estado colada na cidade |
| `environment` | 300 | 11 | 334 | 7 | 14 | formato (`22.2℃` → `22.2`, `NewYork001` → `NewYork_001`, datas), estado e zona climática trocados (erro de contexto), nomes de projeto e status |
| `flights` | 300 | 7 | 728 | 4 | 8 | horários ausentes (célula vazia) e horários com a data colada (`12/02/2011 6:55 a.m.` → `6:55 a.m.`) |
| `hospital` | 300 | 20 | 153 | 17 | 34 | erros de digitação espalhados por quase todas as colunas, com letras trocadas por `x` (`birminghxm` → `birmingham`) |
| `rayyan` | 300 | 12 | 283 | 8 | 16 | metadados bibliográficos; 220 dos erros estão na data de criação do artigo; também ausências, ISSN, autores e codificação de caracteres |

**Origem.** São recortes de 300 linhas dos benchmarks usados na literatura (Raha/Baran,
HoloClean, ZeroED e outros), na versão do repositório do ZeroDC. O `beers`, o
`environment` e o `flights` usam os recortes de 300 linhas que já vinham prontos; o
`hospital` e o `rayyan`, as 300 primeiras linhas dos arquivos completos (de 1.000).

**O guia simula um humano.** Na prática, uma pessoa abriria o dataset, corrigiria
algumas linhas e apontaria alguns erros. Aqui isso foi simulado com semente fixa
(`20261011`): 20 linhas sorteadas, com os valores do gabarito, e até 2 pares por coluna
com erro. Isso equivale a 20 × número de colunas células rotuladas (220 no `beers`), mais
os pares. Reporte essa supervisão junto de qualquer número.

---

## Como testar

Pré-requisito: o ambiente preparado conforme o `README.md` da raiz (seção 1). Os
comandos rodam da raiz do repositório. Cada passo traz o comando do Windows
(PowerShell) e o do Linux ou macOS.

### 1. Sem gastar API: reproduzir o run gravado do `beers`

```powershell
$env:PROVEDOR = "gravado"
$env:RESPOSTAS_GRAVADAS = "tests/fixtures/respostas_beers_poc2.jsonl"
.venv\Scripts\python -m limpeza2.espinha --sujo benchmark/beers/sujo.csv --guia benchmark/beers/guia --nome beers
```

```bash
export PROVEDOR=gravado
export RESPOSTAS_GRAVADAS=tests/fixtures/respostas_beers_poc2.jsonl
.venv/bin/python -m limpeza2.espinha --sujo benchmark/beers/sujo.csv --guia benchmark/beers/guia --nome beers
unset PROVEDOR RESPOSTAS_GRAVADAS   # antes do passo 2, para valer o .env
```

Isso refaz, a partir das respostas gravadas do LLM, o limpador do run de 12/10/2026. Só
funciona com o `beers` e com este guia: as respostas gravadas valem para esses prompts
exatos.

### 2. Gerar com o LLM (gasta API)

Com `PROVEDOR=openai` e a sua chave no `.env` (cerca de 30 chamadas, centavos de dólar;
**as linhas da tabela vão para a OpenAI**):

```powershell
.venv\Scripts\python -m limpeza2.espinha --sujo benchmark/hospital/sujo.csv --guia benchmark/hospital/guia --nome hospital
```

```bash
.venv/bin/python -m limpeza2.espinha --sujo benchmark/hospital/sujo.csv --guia benchmark/hospital/guia --nome hospital
```

Troque `hospital` por qualquer um dos cinco. A saída vai para
`saida/<nome>_<data_hora>/`: o limpador, o raciocínio de cada regra e as respostas
gravadas. Guarde o `respostas.jsonl` de cada run: com ele, o run pode ser refeito sem API.

Para medir o efeito do guia, gere também **sem** ele (tire o `--guia`).

### 3. Medir

```powershell
.venv\Scripts\python medir.py --limpador saida\<pasta>\limpador_<...>.py --sujo benchmark/hospital/sujo.csv --limpo benchmark/hospital/limpo.csv --guia benchmark/hospital/guia
```

```bash
.venv/bin/python medir.py --limpador saida/<pasta>/limpador_<...>.py --sujo benchmark/hospital/sujo.csv --limpo benchmark/hospital/limpo.csv --guia benchmark/hospital/guia
```

Passe o `--guia` também na medição, mesmo para o limpador gerado sem guia: ele tira da
conta as linhas que o guia mostra, para a medida ser a de generalização e a mesma entre os
dois casos. A saída mostra, por coluna e no total, os erros, as alterações, os acertos,
a precisão, o recall, o F1 e as células marcadas e não corrigidas.

A precisão do `medir.py` **não conta alterações feitas em colunas sem erro**: para a
precisão real, some as alterações dessas colunas aos erros de alteração.

---

## O que já foi medido

Com `gpt-6-luna`, nas mesmas condições (guia de 20 linhas, linhas do guia fora da
medição):

| Dataset | Guia | Precisão (real) | Recall | F1 |
|---|---|---|---|---|
| beers | sim | 98,6% | 98,4% | 98,5% |
| beers | não | 82,7% | 9,7% | 17,3% |
| environment | sim | 95,2% | 74,1% | 83,3% |
| environment | não | 50,0% | 16,0% | 24,3% |

**`flights`, `hospital` e `rayyan` ainda não foram medidos.** Qualquer resultado neles é
novo. Detalhes e limites conhecidos em `docs/CONTINUACAO.md`.

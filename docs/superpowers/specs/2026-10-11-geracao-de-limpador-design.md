# Design: POC 2 — geração de limpador de dados tabulares

Data: 11/10/2026. Status: aprovado no brainstorming, seção por seção.
Decisões e justificativas em [`docs/DECISOES.md`](../../DECISOES.md). Regras de
negócio em linguagem de usuário em [`docs/REGRAS_DO_LIMPADOR.md`](../../REGRAS_DO_LIMPADOR.md).

---

## 1. Problema

A POC 1 gera limpadores precisos e tímidos: precisão de 100% e recall de 24,4%
no `beers` e 13,2% no `environment` (`HANDOFF.md` §3). O gargalo é recall, e ele
tem três causas medidas:

1. Detecção valor a valor não alcança erro que depende da linha. No
   `environment`, 21,5% dos erros são inalcançáveis por regra intra-coluna.
2. Quando o erro é inalcançável, a regra degenera em marcar a coluna inteira, o
   que envenena qualquer camada posterior que precise de linhas limpas.
3. O que a regra detecta e não repara vira flag, e flag é recall perdido.
   `Measurement_Date` teve detecção com precisão e recall de 100% e correção de
   0%.

A literatura do mapeamento confirma a causa 3 com uma medida direta: a ablação
do ZeroEC sem o passo residual dá precisão de 1,00 e recall de 0,70 no Hospital
e 0,00 no Rayyan. Com o residual, F1 de 0,99 no Beers e 0,83 no `environment`.

## 2. Objetivo e não objetivos

**Objetivo.** Gerar, a partir do CSV sujo e de um guia pequeno, um script Python
autônomo que repare mais erros que a POC 1 sem perder precisão, e medir a
qualidade desse script executando-o.

**Não objetivos**, que ficam fora desta POC e pertencem ao framework do capítulo
4 da qualificação: reuso de modelos por metadados, PostgreSQL, loop de feedback
humano, interface self-service, RAG institucional, Pandera, Ollama como padrão,
auditor e documentador como módulos institucionais, estudo de caso do SEADE,
medição de eficiência e de memória.

**Divergência declarada em relação à proposta de mestrado.** A proposta tem dois
agentes (gerador de prompt com CoT e gerador de código). Esta POC tem três:
detector e especificador juntos ocupam o lugar do gerador de prompt.

## 3. Entradas, saídas e o que nunca é lido

| Fase | Entra | Sai |
|---|---|---|
| Geração | `<ds>_dirty_300.csv` e, opcionalmente, `guia_linhas.csv` + `guia_pares.csv` | `limpador_<ds>_<carimbo>.py` e `raciocinio_<ds>_<carimbo>.md` |
| Validação | o limpador gerado, o sujo e `<ds>_clean*.csv` | precisão, recall, F1, flags e decomposição por fonte |

**O CSV limpo nunca é lido pela geração.** Garantia estrutural: `preparar_guia.py`
e `medir.py` são os únicos módulos do projeto que o abrem, e os dois ficam fora do
pacote `limpeza2/`. O teste de vazamento assevera que nenhum módulo de
`limpeza2/` importa nenhum dos dois, e que nenhum abre caminho de arquivo que não
seja o sujo ou os dois CSVs do guia.

**Os arquivos de restrição do benchmark** (`FunctionalDependency.txt`,
`TypeConstraint.txt`) e o `real_examples.txt` **não são lidos em nenhuma fase**.
As dependências são mineradas do sujo. Os arquivos do benchmark servem apenas
para conferência manual posterior, fora do código.

## 4. Datasets

Desenvolvimento e comparação com o placar: `beers_dirty_300.csv` e
`environment_dirty_300.csv` de `C:\Users\gusta\projects\Limpeza_de_Dados\ZeroDC\datasets`.
Verificado: são byte a byte idênticos às fixtures da POC 1, então a comparação
vale.

Generalização: as linhas restantes do arquivo completo — 700 no `environment` e
2.110 no `beers`. Verificado que as 300 linhas são subconjunto do arquivo
completo em ambos. No `beers`, o arquivo de 300 grafa `beer-name` e
`brewery-name` com hífen, e o completo com sublinhado; a fatia nunca vista é
renomeada para a grafia com hífen antes de rodar o limpador.

Depois, como generalização entre datasets: `hospital`, `flights` e `rayyan`.

## 5. Arquitetura

### 5.1 Árvore de módulos

```
limpeza2/
  tipos.py              # o que viaja entre etapas
  config.py             # modelo, caminhos, limiares, semente
  provedor.py           # entrega o cliente do provedor de LLM escolhido
  portao.py             # valida o Python gerado antes de deixa-lo rodar
  motor.py              # UNICA implementacao de aplicacao de regra (inclui `padrao`)
  conformidade.py       # deriva o schema de cada coluna das celulas que o guia certificou
  limites.py            # calcula os limites que o guia sustenta para uma coluna
  e1_perfil.py          # etapa 1: perfila a tabela suja, lida como texto literal
  e2_detector.py        # etapa 2: agente detector -> predicados candidatos
  e3_crivo.py           # etapa 3: reprova a regra candidata que nao se sustenta
  e4_especificador.py   # etapa 4: agente especificador -> JSON de reparo
  e5_residual.py        # etapa 5: rodada residual por entidade -> dicionario
  e6_codificador.py     # etapa 6: agente codificador -> escreve os artefatos de saida
  espinha.py            # a ordem das etapas, e nada mais
preparar_guia.py        # fora do pacote: sorteia o guia com semente fixa
medir.py                # fora do pacote: executa o limpador gerado e mede
```

Quinze arquivos (`limites.py` separa o que o guia sustenta da decisão do crivo). O `CLAUDE.md` §2 admite até quinze, com necessidade demonstrada,
e o critério que manda é outro: **todo arquivo cabe numa frase que diz o que ele
faz**. A folga de dois existe para quando `e6_codificador.py` ou `motor.py`
passarem de 200 linhas — aí separa-se a parte que tem função própria. Fracionar
pelo tamanho é proibido: um arquivo de 190 linhas com função clara é melhor que
dois de 95 com funções difusas.

A frase de cada arquivo é o comentário ao lado dele na árvore acima. Se alguma
precisar de "e", o arquivo faz duas coisas e o desenho está errado.

### 5.2 A espinha

```python
def gerar_limpador(caminho_sujo, caminho_guia, destino):
    """Etapas 1 a 6 em ordem: a unica sequencia do projeto."""
    entrada = e1_perfil.perfilar(caminho_sujo, caminho_guia)
    candidatas = e2_detector.propor(entrada)
    deteccoes = e3_crivo.crivar_deteccao(candidatas, entrada)
    propostas = e4_especificador.especificar(deteccoes, entrada)
    reparos = e3_crivo.crivar_reparo(propostas, entrada)
    residual = e5_residual.resolver(reparos, entrada)
    return e6_codificador.escrever(reparos, residual, entrada, destino)
```

O crivo aparece duas vezes de propósito: o controle por célula do guia
(`sujo == guia`) vale tanto para a regra que detecta quanto para a que repara. É o que
justifica ele ser módulo próprio.

A validação não está na espinha, porque é a outra fase:
`medir.medir(caminho_limpador, sujo, limpo, guia)`.

### 5.3 Tipos que viajam

Quatro dataclasses em `tipos.py`:

| Tipo | Campos |
|---|---|
| `Entrada` | `sujo: DataFrame`, `guia_linhas: DataFrame`, `guia_pares: DataFrame`, `perfil: Perfil` (e `coluna_sujeito: str`, pendência da parte 2: ainda não está em `tipos.py`) |
| `Candidata` | `coluna`, `tipo`, `parametros: dict`, `raciocinio: str`, `metricas: dict` |
| `Reparo` | `candidata: Candidata`, `estrategia`, `parametros: dict`, `raciocinio: str`, `codigo: str \| None` |
| `Residual` | `coluna`, `mapa: dict[str, str]`, `justificativas: dict[str, str]` |

`Perfil` é um dicionário com duas chaves: `colunas` (por coluna) e `pares` (por
par ordenado de colunas).

### 5.4 Fonte única da lógica de aplicação

`motor.py` é a única implementação de "aplicar uma regra". O crivo o importa; o
codificador copia o texto-fonte dele inteiro para dentro do limpador, porque o
limpador não pode depender deste repositório. O teste que assevera que o trecho
embutido é byte a byte igual a `motor.py` é pendência da parte 2.

Esta é a resposta à lição mais cara da POC 1 (`CLAUDE.md` §4). Não existe uma
segunda implementação mantida à mão: existem os mesmos bytes em dois lugares,
com igualdade verificada.

## 6. As etapas

### Etapa 1 — perfil (determinística)

Carga como texto literal: `pd.read_csv(p, dtype=str, keep_default_na=False, na_values=[])`.

Por coluna: número de distintos e de vazios, os 15 valores mais frequentes e os
10 mais raros com contagem, e os padrões em três níveis de generalização com
frequência (nível 1 classe por caractere, nível 2 classes com contagem de
repetição, nível 3 sequência de classes sem contagem).

Por par ordenado de colunas `(A, B)`, cinco números calculados só no sujo:

| Número | Definição |
|---|---|
| `det(A→B)` | soma, sobre os grupos de `A` com suporte ≥ 2, da contagem da moda de `B`, dividida pelo total de linhas nesses grupos |
| `n_grupos` | quantidade de grupos de `A` com suporte ≥ 2 |
| `cobertura` | fração das linhas da tabela que vivem nesses grupos — é esta, e não a contagem de grupos, que mede a evidência |
| `n_divergentes` | células de `B` que divergem da moda do seu grupo |
| `frac_ambiguos` | fração dos grupos em que a moda de `B` não atinge o limiar de dominância |

`frac_ambiguos` é o perfil que reprova a dependência ambígua de `flights`
(`flight → act_arr_time`, em que quatro horários concorrem para o mesmo voo),
sem precisar do gabarito.

**Coluna-sujeito.** O perfil propõe as três colunas com determinação alta sobre
o maior número de outras colunas; uma chamada de LLM escolhe qual nomeia a
entidade. Minerar e deixar o LLM julgar, como o Cocoon faz com dependências.

### Etapa 2 — detector (uma chamada de LLM por coluna)

O prompt leva: o schema completo; o perfil compacto daquela coluna, em uma linha
por item, no estilo do catálogo do CatDB; os pares candidatos em que a coluna é o
lado determinado, com os cinco números acima; as linhas corrigidas do guia; e os
pares `sujo → limpo` que caem naquela coluna.

Devolve candidatas de um **catálogo fechado de cinco tipos**, em ordem de
abrangência crescente (ordem do Cocoon: caractere, padrão, ausente, entre
colunas):

| Tipo | Parâmetro emitido pelo LLM |
|---|---|
| `formato` | uma regex que o valor válido casa |
| `dominio` | a lista de valores válidos |
| `faixa` | mínimo e máximo |
| `ausente_disfarcado` | a lista de sentinelas |
| `dependencia` | as colunas determinantes desta |

Nenhum parâmetro passa de vinte tokens. É o que impede o estouro de saída que
quebrou `Eco_Status` na POC 1 com `LengthFinishReasonError`. As três variantes
de cada tipo vêm **numa única chamada** por coluna, como lista, não em três
chamadas — o rephraser do ZeroEC gasta três chamadas, e aqui a saída é curta o
bastante para caber numa.

Como a tabela é carregada só como texto, `faixa` converte com tentativa de
`float`: valor não convertível **não** é marcado por `faixa`, e sim pelo tipo
`formato`, para que cada célula marcada tenha um motivo único e rastreável.

### Etapa 3 — crivo (determinística, sem LLM e sem gabarito)

Executa cada candidata sobre o sujo pelo `motor.py` e aplica cinco testes:

| # | Teste | Reprova quando | Lição que endereça |
|---|---|---|---|
| 1 | controle por célula | `marca_celula_correta`: marca célula do guia em que `sujo == guia`, na coluna da regra; `marca_valor_certificado`: nos tipos de valor, marca célula cujo valor o guia mostra como correto | `CLAUDE.md` §1 |
| 2 | não-vacuidade | marca zero células no sujo | lição 6 |
| 3 | teto de marcação | marca mais que o teto da coluna (`marca_demais`) | lição 4 |
| 4 | piso do guia | há pares na coluna e a regra não marca todos | — |
| 5 | ambiguidade (só `dependencia`) | `frac_ambiguos` acima do limiar | — |

Entre as variantes sobreviventes do mesmo tipo fica a de **menor taxa de
marcação** que ainda passa no teste 4. Tipos diferentes na mesma coluna
coexistem, mas a união das máscaras tem de caber no teto da coluna: se estourar,
descartam-se tipos, do de maior taxa para o de menor (empate: ordem alfabética
do tipo), até caber (`uniao_acima_do_teto`).

Em coluna sem par no guia, o teste 4 não se aplica, e os testes 1 a 3 decidem
sozinhos. Marcar célula do guia em que `sujo != guia` é correto e não reprova. É isso que substitui o gate de 100% da POC 1, que passava por
vacuidade.

O teto é por coluna: `max(TETO_MARCACAO, taxa_suja_no_guia + 2 * sqrt(0,25 / n))`,
com `TETO_MARCACAO = 0,30` fixado *a priori* como piso (não pode ser calibrado
com o gabarito) e `n` as linhas do guia. Sem guia, o teto é exatamente 0,30. O teto
usado vai em `metricas["teto"]`. Justificativa e limites em
`docs/DECISOES.md#teto-de-marcacao`.

### Etapa 4 — especificador (uma chamada por detecção aprovada)

Devolve JSON curto com a estratégia de reparo, de catálogo fechado:

| Estratégia | Parâmetro | Quando serve |
|---|---|---|
| `normalizar` | a transformação pedida em linguagem estruturada | formato previsível |
| `moda_condicionada` | colunas determinantes e limiar de dominância | dependência entre colunas |
| `vizinho_no_dominio` | distância máxima de edição | valor fora do domínio observado com vizinho próximo |
| `dicionario` | pares literais `{sujo: limpo}` | o que não é parametrizável |
| `esvaziar` | — | sentinela que deve virar vazio |

Mais `raciocinio` em três frases, no molde CoT do ZeroEC: padrão identificado,
análise do erro, transformação.

**Qual lado da violação está errado.** Para `moda_condicionada`, a regra padrão
repara o lado determinado. Exceção, da versão barata do BClean+: se o valor do
determinante ocorre uma única vez na coluna e existe outro valor de determinante
a distância de edição 1 com grupo de suporte ≥ 2, o erro está no determinante, e
é ele que é corrigido. Recupera erro de digitação na chave, que a dependência
orientada perderia.

A distância é **Damerau-Levenshtein restrita**, em que a transposição de
caracteres adjacentes custa uma edição. Em Levenshtein puro, `Bosotn` → `Boston`
custa 2, e a transposição — provavelmente a classe mais comum de erro de
digitação — ficaria fora do método. São quatro linhas a mais no cálculo.

Depois, `crivar_reparo` reprova a estratégia que escreva em célula do guia um valor
diferente do guia (`corrompe_celula_do_guia`; não escrever não reprova nesse
teste), que não reproduza os pares e as células sujas do guia na coluna-alvo
(`perde_par_do_guia`), ou que repare zero células
detectadas.

### Etapa 5 — residual (a aposta de recall)

Sobram células detectadas que nenhuma estratégia reparou. Na POC 1 elas viravam
flag.

1. Junta os **valores distintos** que sobraram, não as células.
2. Agrupa os lotes de prompt pela coluna-sujeito, para o LLM ver num mesmo
   prompt todas as linhas da mesma entidade e notar a redundância entre elas.
   É a peça do IterClean, cuja ablação mostra o F1 do `flights` caindo de 0,595
   para 0,164 com grupos aleatórios.
3. Devolve `{valor_sujo: valor_limpo}` com justificativa por entrada, e `null`
   onde não sabe.
4. Passa pelo mesmo crivo: nenhuma entrada pode escrever em célula do guia um valor diferente do guia.
5. É congelado como literal no limpador. Nenhuma chamada de LLM em execução.

**Limitação declarada.** O dicionário é por coluna e valor. Cobre qualquer linha
futura que repita o mesmo valor sujo, e não cobre valor sujo inédito numa tabela
nova — aí só as regras valem. Consequência: rodar a POC inteira num dataset novo
é estritamente mais poderoso que rodar o limpador congelado nele. É a troca que
o princípio de converter conhecimento do LLM em artefato reexecutável impõe, e é
por isso que a métrica mede em dois lugares (§8).

### Etapa 6 — codificador

Recebe reparos e residual e escreve dois arquivos.

`limpador_<ds>_<carimbo>.py`: cabeçalho avisando que roda sem portão; `import
pandas`; o texto-fonte de `motor.py` embutido; os parâmetros como literais
(regexes, domínios, dicionários, determinantes, limiares); as funções escalares
`corrigir_*(valor) -> str` escritas pelo LLM; `limpar(df) -> (df, mascara_flags)`;
e um `main` que lê e escreve CSV.

`raciocinio_<ds>_<carimbo>.md`: por coluna e por regra, os números do crivo
(células marcadas, taxa, `det`, `n_grupos`, `frac_ambiguos`) e o CoT de três
frases. Inclui as regras **reprovadas** e o motivo, porque é o que torna a
vacuidade visível.

O único Python escrito pelo LLM são as funções escalares de normalização. Todo o
resto é `motor.py` parametrizado. Funções escalares não precisam de pandas, o que
casa com o portão da POC 1, que mantém `pd` fora do namespace e oferece `re`.

## 7. Guia

`preparar_guia.gravar(dataset, sujo, limpo, semente, n_linhas, pares_por_coluna, destino=None)`
grava, em `dados/guia/<destino ou ds>/`:

- `guia_linhas.csv`: 20 linhas sorteadas de qualquer parte da tabela, com os valores do limpo (referência corrigida; 20 × 11 = 220 células rotuladas no `beers`).
- `guia_pares.csv`: colunas `linha, coluna, sujo, limpo`, até 2 pares por coluna
  que tem erro.
- `guia_receita.txt`: dataset, semente, linhas e pares por coluna; registro para humano, nenhum módulo o lê.

Semente fixa em `config.py`. Gerado uma vez e commitado. A geração lê os CSVs,
nunca executa o sorteio.

**Braço sem guia:** a mesma espinha com os dois CSVs vazios. Os testes 1 e 4 do
crivo não se aplicam, e sobram a não-vacuidade e o teto (0,30 exato). A diferença entre os
braços é quanto o guia vale.

## 8. Medição

Fórmula idêntica à do `avaliar_limpador.py` da POC 1, para a comparação valer:
precisão igual a alterações corretas sobre alterações, recall igual a alterações
corretas sobre erros, F1 harmônico, mais a contagem de flags.

Calculada **executando o arquivo gerado**. O holdout tira da métrica toda linha
que apareceu no guia: as 20 do guia e as linhas dos pares. O número de linhas
descontadas é publicado ao lado de cada F1.

Dois locais de medição, ambos publicados:

| Onde | O que mede | Compara com |
|---|---|---|
| as 300 linhas da geração, menos o holdout | o limpador na tabela de origem | o placar da POC 1: 24,4% e 13,2% de recall |
| as 700 (`environment`) e 2.110 (`beers`) linhas nunca vistas | o limpador como programa, não como tabela de consulta | número novo |

Mais a **decomposição do recall por fonte**: quantas correções vieram de cada
tipo de regra e quantas do dicionário residual. A diferença entre os dois locais
de medição, lida junto da decomposição, é a medida da memorização.

## 9. Resiliência e segurança

Uma fronteira de resiliência por coluna, não várias paralelas. Cada `try` tem
degradação nomeada:

| Onde | Falha | Degradação |
|---|---|---|
| etapa 2 e 4 | o LLM devolve JSON inválido ou estoura | a coluna fica sem aquela regra |
| etapa 3 | a regra lança ao ser aplicada | a candidata é reprovada e o motivo vai ao Markdown |
| etapa 6 | a função escalar não passa no portão | a regra cai, a coluna segue com as demais |
| limpador | a função lança numa célula | a célula vira flag |

Portão AST adaptado de `../POC_Limpeza_de_Dados/limpeza/sandbox.py` (142 linhas):
allowlist de builtins, proibição de `import`, dunder, `eval`, `exec`, `compile`,
`open`, `getattr` e companhia, execução em namespace descartável com `re`
disponível e `pd` fora. O limpador gerado roda **sem** o portão na máquina do
usuário, e o cabeçalho dele avisa isso.

`provedor.py` lê `PROVEDOR` do `.env`; valor desconhecido levanta exceção e
nunca cai para OpenAI, porque isso mandaria a tabela do usuário para fora da
rede. Provedor desta POC: OpenAI, modelo `gpt-5.6-luna`, nome em `.env`.

## 10. Testes

Nenhum teste gasta API: os três agentes são substituídos por um dublê de
provedor que devolve JSON fixo.

Um teste por etapa, mais quatro que são rede de segurança:

1. **Vazamento**: nenhum módulo de `limpeza2/` importa `preparar_guia` nem
   `medir`; nenhum abre caminho de arquivo fora do sujo e dos dois CSVs do guia.
2. **Portão**: código com `import`, dunder, `eval` e `open` é rejeitado sem ser
   executado.
3. **Identidade do motor**: o trecho embutido no limpador é byte a byte igual a
   `motor.py`.
4. **Invariante**: o primeiro limpador que preste é congelado em
   `tests/fixtures/` e seus números viram teste. Mudar esses números é bug, a
   menos que o usuário decida que é mudança de comportamento, com entrada nova
   em `docs/DECISOES.md` e fixture nova.

Todo teste novo vem com prova por mutação, e a mutação usada é registrada.

## 11. Riscos

| Risco | Medida |
|---|---|
| `e6_codificador.py` e `motor.py` perto de 190 linhas | primeiro simplificar; depois separar a parte com função própria, usando um dos dois arquivos de folga; nunca fracionar pelo tamanho nem espremer a formatação |
| fracionar demais e perder a noção da função de cada arquivo | cada arquivo tem de caber numa frase sem "e"; é o critério que manda sobre a contagem |
| o código gerado decora o vocabulário de erros do guia (um estudo mede F1 de 23,5 na detecção do Hospital por isso) | o crivo mede a regra na tabela suja inteira, não nos exemplos; o teste 3 pune a regra agressiva |
| `gpt-5.6-luna` é mais novo que o conhecimento do assistente | nome em `.env`; formato de saída confirmado contra a API na primeira chamada |
| o residual infla o F1 na tabela de origem | medição nos dois locais e decomposição por fonte |
| `TETO_MARCACAO` escolhido sem calibração | fixado a priori como piso; o teto sobe por coluna com a taxa suja do guia |

## 12. Como esta POC se compara, e por que a comparação favorece a POC 1

A POC 1 teve mais supervisão: cerca de 10 células rotuladas por coluna,
sorteadas do limpo completo, mais o que o oráculo rotulou em 5 iterações de
refino. Esta POC recebe no máximo o guia. **Empatar com a POC 1 usando menos
rótulo já é avanço**, e o tamanho do guia é reportado junto de cada número.

Os números dos papers não são alvo comparável. O ZeroDC reporta F1 de 1,00 em
Hospital e Beers, mas cerca de 60% do resultado dele vem de um laço de 10
anotações por coluna que, no código publicado, são simuladas lendo o
`_clean.csv`. CodeGenWrangler e CatDB validam contra splits rotulados grandes.
Nenhum desses sinais de validação está disponível aqui.

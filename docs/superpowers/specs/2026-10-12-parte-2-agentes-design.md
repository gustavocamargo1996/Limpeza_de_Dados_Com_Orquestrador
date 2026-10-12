# Design: POC 2, parte 2 — os agentes, a espinha e o limpador gerado

Data: 12/10/2026. Status: aprovado no brainstorming, seção por seção.

Este documento **complementa** a spec de 11/10
([`2026-10-11-geracao-de-limpador-design.md`](2026-10-11-geracao-de-limpador-design.md)),
não a substitui. Valem dela, sem mudança: o problema (§1), os objetivos (§2), as
entradas e o que nunca é lido (§3), os datasets (§4), a fonte única da lógica
(§5.4), o perfil (etapa 1), o crivo da detecção (etapa 3), o catálogo de
estratégias (etapa 4), o guia (§7), a medição (§8) e a comparação (§12). O que
segue é o que a parte 2 decide, e onde ela corrige a spec antiga.

---

## 1. O que a parte 2 entrega

Seis arquivos, o que leva o projeto a **16 de 16**, com folga zero:

| Arquivo | Frase |
|---|---|
| `limpeza2/provedor.py` | entrega o cliente do provedor de LLM escolhido |
| `limpeza2/e2_detector.py` | etapa 2: agente detector -> predicados candidatos |
| `limpeza2/e4_especificador.py` | etapa 4: agente especificador -> JSON de reparo |
| `limpeza2/e5_residual.py` | etapa 5: rodada residual por entidade -> dicionario |
| `limpeza2/e6_codificador.py` | etapa 6: agente codificador -> escreve os artefatos de saida |
| `limpeza2/espinha.py` | a ordem das etapas, e nada mais |

**A vaga do 16º arquivo vem do `limpeza2/__init__.py`**, vazio, cuja remoção já
foi verificada (a suíte passa sem ele). Ele é apagado **antes** de qualquer
arquivo novo, para nenhum commit intermediário estourar o teto. O `CLAUDE.md` §9
fala em "quinze arquivos" e lista dezesseis; a contagem é corrigida na mesma
tarefa.

## 2. A espinha

```python
def gerar_limpador(caminho_sujo, caminho_guia, destino):
    """Etapas 1 a 6 em ordem: a unica sequencia do projeto."""
    provedor.iniciar(destino)
    entrada = e1_perfil.perfilar(caminho_sujo, caminho_guia)
    conformes = conformidade.candidatas_de_conformidade(entrada)
    schema = e3_crivo.crivar_deteccao(conformes, entrada)
    candidatas = e2_detector.propor(entrada, conformes)
    deteccoes = e3_crivo.crivar_deteccao(schema + candidatas, entrada)
    propostas = e4_especificador.especificar(deteccoes, entrada)
    funcoes = e6_codificador.codificar(propostas, entrada)
    reparos = e3_crivo.crivar_reparo(propostas, entrada, funcoes)
    residual = e5_residual.resolver(deteccoes, reparos, funcoes, entrada)
    return e6_codificador.escrever(
        deteccoes, reparos, residual, conformes + candidatas, entrada, destino
    )
```

O que mudou em relação à espinha da spec de 11/10, e por quê:

- **Conformidade, crivo e só então o detector.** O detector precisa saber se a
  conformidade da coluna foi aprovada (§3.2). Por isso o crivo passa a ser
  chamado três vezes: sobre a conformidade, sobre todas as detecções e sobre os
  reparos.
- **O segundo `crivar_deteccao` recebe a conformidade aprovada junto com as
  candidatas do LLM**, para a `taxa_uniao` da coluna sair completa. Recrivar a
  conformidade é determinístico sobre a mesma entrada: `motivo`, `marcadas`,
  `taxa` e `teto` saem idênticos, e só a `taxa_uniao` muda, de propósito. Um teste
  trava isso, porque é a suposição que sustenta chamar o crivo duas vezes sobre
  os mesmos objetos.
- **O codificador age em dois tempos.** `crivar_reparo` precisa das funções
  `corrigir` para testar a estratégia `normalizar`, então `codificar` roda antes
  dele, e `escrever` roda no fim. Ele aparece duas vezes na espinha, como o crivo.
- **`escrever` recebe valores com nomes distintos, nunca efeito de mutação.**
  `deteccoes` é o que o limpador aplica e de onde saem as flags, inclusive das
  detecções sem reparo. `conformes + candidatas` alimenta só o `.md`, para mostrar
  as reprovadas. Filtrar as aprovadas por `metricas["motivo"]` faria as flags
  dependerem de o crivo mutar os objetos, e elas sumiriam em silêncio no dia em
  que isso mudasse.
- **`provedor.iniciar(destino)` abre a geração** (§3.1): o registro de chamadas e
  o teto valem por geração, não por processo.
- **A coluna-sujeito sai da etapa 1** e vai para dentro do `e5_residual`, seu
  único consumidor. O campo `Entrada.coluna_sujeito`, pendente desde a spec de
  11/10, deixa de existir.

### Abordagens rejeitadas

- **O laço de aplicação como texto no template do limpador.** O residual
  precisaria de uma segunda implementação para saber o que sobrou: é o defeito do
  `CLAUDE.md` §4.
- **`normalizar` aprovado sem a função.** Abriria buraco no controle por célula do
  guia justamente na única estratégia em que o LLM escreve código, que é onde o
  portão existe.

## 3. Os agentes

### 3.1 Provedor (`provedor.py`)

`cliente()` devolve o cliente da geração corrente, um objeto com um método:
`pedir_json(etapa, unidade, instrucao, conteudo, esquema) -> dict`. A geração é
aberta por `provedor.iniciar(destino)`, a primeira linha da espinha: ela zera o
registro e o contador de chamadas e define onde o `respostas.jsonl` é gravado.
Sem isso, duas gerações no mesmo processo (os testes, os dois braços) somariam
registro e teto.

| `PROVEDOR` | Como |
|---|---|
| `openai` | SDK `openai`, saída estruturada com `response_format` e esquema JSON estrito |
| `ollama` | o mesmo SDK `openai`, `base_url = http://localhost:11434/v1`; nenhuma dependência nova |
| `gravado` | reproduz as respostas de um `respostas.jsonl`, indexadas pelo hash de `(instrucao, conteudo)` |
| qualquer outro | levanta exceção; nunca cai para OpenAI (`DECISOES.md#provedor`) |

**Modelo: `gpt-6-luna`, com `reasoning_effort="none"`.** Decisão do usuário em
12/10/2026, substituindo o `gpt-5.6-luna` da spec de 11/10. É o modelo da faixa
barata na página oficial de comparação da OpenAI nesta data (US$ 0,10 / 0,50 por
milhão de tokens, saída estruturada e Chat Completions suportados); o
`gpt-5.6-luna` já não aparece nela e custa o dobro. Raciocínio em `none` por dois
motivos: sem tokens de raciocínio ocultos não há resposta vazia por
`finish_reason == "length"` causada pelo raciocínio, e só com `none` a
`temperature` é aceita. O julgamento pesado já está no crivo determinístico, e o
LLM preenche parâmetros curtos. Subir o esforço é mudança de configuração, mas
muda o limpador congelado: é decisão registrada, não ajuste.
`config.MODELO = "gpt-6-luna"`, `config.ESFORCO_RACIOCINIO = "none"`.

**Determinismo.** `config.TEMPERATURA = 0` e `seed = config.SEMENTE`. A página
oficial do modelo não diz se aceita `temperature` e `seed`; a aceitação com
`none` vem de fontes de terceiros (guia da LiteLLM, issues de SDK). A sonda do §7
confirma. Se algum for recusado, ele vira `None` em `config` e deixa de ser
enviado, com registro no `DECISOES.md`. **A geração
não é reprodutível bit a bit.** Ela é reprodutível **dadas as respostas**: o
cliente grava cada chamada em `saida/<carimbo>/respostas.jsonl`, e
`PROVEDOR=gravado` refaz o run a partir delas. Diferença entre dois runs pagos
não é regressão; mudança no limpador congelado ou na geração a partir das
respostas gravadas é.

**Registro.** O cliente anota cada chamada: etapa, unidade, status ou motivo da
falha, e tokens. É desse registro que saem a contagem de chamadas, a marca de
truncamento e as falhas por unidade no `.md`. Nenhuma lista de falhas viaja pela
espinha.

**Falhas, com degradação nomeada.**

| Falha | Tratamento |
|---|---|
| timeout, rate limit, 5xx | `max_retries` com backoff do próprio SDK |
| tentativas esgotadas | `FalhaDoLLM("rede")` |
| `finish_reason == "length"` | `FalhaDoLLM("cortada")` — o `LengthFinishReasonError` que quebrou o `Eco_Status` na POC 1, com nome próprio no relatório |
| recusa do modelo | `FalhaDoLLM("recusada")` |
| JSON que não parseia | `FalhaDoLLM("json_invalido")` |
| `TETO_CHAMADAS` atingido | `FalhaDoLLM("teto")` |
| autenticação, modelo inexistente | **não** degrada: derruba o run, porque é configuração e não acaso |

Cada agente tem **um** `except FalhaDoLLM`, e a unidade (coluna, detecção,
proposta ou lote) fica sem regra. Erro fora disso é bug e propaga.

**Plano B da saída estruturada.** Se o modelo não suportar esquema estrito,
`config.SAIDA_ESTRITA = False` faz o pedido com
`response_format={"type": "json_object"}` e o esquema descrito no prompt. O
desenho não muda: a conversão de cada agente já valida campo a campo e descarta
o que vier malformado, então ela é o validador nos dois modos. O objeto plano com
nulos (§3.2) foi escolhido para servir aos dois.

### 3.2 Detector (`e2_detector.propor(entrada, conformes)`)

Uma chamada por coluna, em todas as colunas.

**O catálogo da coluna** parte dos cinco tipos e perde:

- `formato`, **se e só se a conformidade da coluna foi aprovada pelo crivo**. A
  conformidade responde "o valor tem a forma certa?" a partir de dado
  certificado; um `formato` do LLM faz a mesma pergunta com resposta pior e, sem o
  portão da união, só pode somar falso positivo. Os outros três tipos de valor
  perguntam coisas que a forma não alcança: `dominio` (`Freedonia` tem forma de
  país e não é um), `faixa` (`12` e `9999` conformam a `9`), `ausente_disfarcado`
  (`0` conforma a `9`). O critério é a aprovação, não ter schema: a conformidade
  de `Project_Name` é reprovada (`perde_par_do_guia`), e com o critério "tem
  schema" a coluna ficaria sem nenhuma regra de forma. Não se escreve a condição
  "e não vácua": o crivo já reprova a vácua, então ela seria lógica morta.
- `dependencia`, se a coluna não é o lado determinado de nenhum par minerado. Sem
  par, o crivo a reprovaria sempre por `sem_perfil`.

**O prompt leva:** o schema da tabela; o perfil compacto da coluna, uma linha por
item; os pares minerados com os cinco números; as linhas do guia; os pares e as
células sujas do guia que caem na coluna; e a frase do caso da conformidade:

| Caso | Frase, em substância |
|---|---|
| aprovada | a forma já está coberta; procure erro de valor, de magnitude, de ausência ou contextual |
| reprovada | existe schema, mas a regra dele não passou, pelo motivo X |
| vácua | schema apertado sem violação nenhuma: o erro, se existe, é contextual |

A abstenção da conformidade orienta o LLM; quem restringe o catálogo é só a regra
acima.

**A saída** é uma lista de variantes num objeto plano: `tipo` (enum restrito ao
catálogo da coluna), `regex`, `valores`, `minimo`, `maximo`, `sentinelas`,
`determinantes`, `raciocinio`, com nulo no que não se aplica. Na conversão para
`Candidata`, a variante malformada cai sozinha e ficam no máximo
`VARIANTES_POR_TIPO` por tipo. `FalhaDoLLM` deixa a coluna sem regra do LLM.

### 3.3 Especificador (`e4_especificador.especificar(deteccoes, entrada)`)

Uma chamada por detecção aprovada, conformidade inclusive.

**O prompt leva:** a regra (tipo, parâmetros, raciocínio); os valores marcados,
distintos e com contagem, até 30; os padrões do schema, quando houver; os pares e
as células sujas do guia na coluna, como exemplos `sujo -> limpo`; os valores
certificados; os pares minerados.

**A saída:** `estrategia` (as cinco, sem restrição por tipo: quem decide é o
crivo do reparo), `transformacao` (texto, só para `normalizar`),
`determinantes`, `distancia`, `mapa` (lista de `{sujo, limpo}`) e `raciocinio`
com três campos: padrão identificado, análise do erro, transformação.

**O domínio de `vizinho_no_dominio` não vem do LLM.** O `e4` o calcula: os valores
não marcados da coluna com duas ou mais ocorrências, mais os valores
certificados. Pedir a lista ao LLM traria de volta o estouro de saída. Ele entra
no limpador como literal, e por isso é **memória** (§6).

### 3.4 Codificador, primeiro tempo (`e6_codificador.codificar(propostas, entrada)`)

Uma chamada por proposta `normalizar`. **O prompt leva** a `transformacao`, os
exemplos `sujo -> limpo` do guia na coluna, uma amostra dos valores marcados e o
contrato: `def corrigir(valor) -> str`, sem `import`, com `re` disponível.

Depois: `portao.validar`, `materializar` e `testar_fumaca` com os valores que a
regra marcou. Se o portão rejeitar, há **uma** nova tentativa, com a mensagem do
portão no prompt (as mensagens foram escritas para isso). Se falhar de novo, a
regra cai. A função aprovada entra em `funcoes` com nome único (`corrigir_<n>`),
gravado em `proposta.parametros["funcao"]`; o texto vai para `proposta.codigo`.

### 3.5 Onde ficam os prompts

Como constantes dentro de cada agente. O texto do prompt, o código que o preenche
e o que faz o parse da resposta mudam sempre na mesma edição; separá-los criaria
duas coisas que só fazem sentido lidas em par. **Ressalva registrada:** se um
prompt passar de cerca de 40 linhas, o argumento se inverte, e a decisão é
reaberta.

## 4. O motor aplica tudo: `motor.aplicar_regras`

`aplicar_regras(df, regras, residual, funcoes, dominancia) -> (df, flags, fontes)`
é a única implementação do laço que combina as regras de uma tabela:

1. As máscaras de todas as regras aprovadas são calculadas sobre o df
   **original**.
2. Cada reparo lê o **original** e escreve na saída, na ordem do catálogo; quem
   escreve primeiro numa célula vence.
3. O dicionário residual age só nas células **marcadas e ainda não reparadas**.
4. Flag é célula marcada que nenhum reparo nem o residual alterou.
5. `fontes` rotula cada célula reparada (`conformidade/normalizar`,
   `dependencia/moda_condicionada`, `residual`, ...).

Ler sempre o original é o que garante que cada reparo faz no limpador o que o
crivo aprovou; em particular, a `moda_condicionada` calcula a moda na tabela suja,
onde o crivo a calculou. A diferença possível fica nas células disputadas por
mais de um reparo.

O nome não é `aplicar` porque o contrato do arquivo gerado, de que o `medir.py`
depende e que mede os limpadores das duas POCs, é `aplicar(df) -> (df, flags)` e,
opcionalmente, `aplicar_detalhado(df) -> (df, flags, fontes)`. Os dois são
invólucros finos sobre `aplicar_regras` no limpador.

**Antes de acrescentar, simplificar.** `motor.py` tem 183 linhas. As estratégias
`vizinho_no_dominio`, `dicionario` e `esvaziar` são o mesmo laço com uma função
escalar diferente, cujo contrato é "devolve o valor novo, ou `None` para não
reparar" — isso cobre o valor fora do mapa, o vizinho distante e a célula já
vazia, que são os três ramos que hoje decidem se `reparada` vira verdadeiro. A
simplificação não muda comportamento, e a suíte atual é a guarda.

A conversão de `deteccoes + reparos` para a lista literal de regras é usada pelo
`e5` e pelo `e6.escrever`, e mora em `tipos.py` como `regras_literais(...)`. A
frase do arquivo passa a ser "o que viaja entre as etapas, até o limpador
gerado". Se ela não fechar depois de escrita, a função vai para o
`e6_codificador`.

## 5. O residual (`e5_residual.resolver(deteccoes, reparos, funcoes, entrada)`)

Devolve `list[Residual]`.

1. **O que sobrou.** Roda `motor.aplicar_regras` sobre o sujo com as regras
   aprovadas e sem residual; sobram as flags. Mesma função do limpador, sem
   segunda implementação.
2. **Coluna-sujeito.** Uma chamada escolhe, entre as até três
   `perfil.candidatas_sujeito`, a que nomeia a entidade, ou `null`. Sem candidatas
   ou com `null`, os lotes seguem a ordem das linhas.
3. **Lotes.** As linhas com flag, agrupadas pelo valor da coluna-sujeito, cada
   grupo com **todas** as linhas da entidade, inclusive as sem flag: é a
   redundância entre elas que o IterClean explora. Até `LINHAS_POR_LOTE = 40`
   linhas por lote e no máximo `MAX_LOTES_RESIDUAL = 10` lotes; o excedente vira
   flag com motivo `sem_lote` no relatório. **Ordem determinística:** grupos pelo
   menor índice de linha da entidade, linhas em ordem de índice, pares
   `(coluna, sujo)` ordenados no prompt.
4. **Pergunta por valor, não por célula.** O prompt lista os `(coluna, sujo)`
   distintos do lote, as linhas como contexto e os pares do guia como exemplo. A
   resposta: lista de `{coluna, sujo, limpo | null, justificativa}`.
5. **Consolidação.** `null` e `limpo == sujo` não entram. O mesmo `(coluna, sujo)`
   com a mesma resposta em lotes diferentes vira **uma** entrada; com respostas
   diferentes, sai como `conflitante`.
6. **Crivo, por entrada** (`e3_crivo.crivar_residual`). Cai a entrada que escreve
   em célula do guia um valor diferente do guia, que contradiz um par do guia, ou
   cujo `sujo` é valor que o guia certifica como correto na coluna.
7. **No limpador**, o dicionário age só em célula marcada e não reparada.

**O veto por valor certificado, e por que aqui ele não tem exceção.** Na
detecção, `dependencia` pode marcar valor certificado, porque o erro está no
contexto da linha (49 das 54 células erradas de `State` carregam valor
certificado). No dicionário não pode, porque **a chave não carrega contexto**. Na
tabela de origem, dois `HH` marcados que pedem correções diferentes dão
`conflitante`; numa tabela nova não há esse controle, e todo `HH` marcado viraria
`MA`, inclusive o de uma cervejaria de Nova York. **Custo, declarado:** o residual
perde o erro contextual que, na tabela de origem, tinha correção única; esse fica
só para a `moda_condicionada`.

**Braço sem guia.** As três condições do item 6 dependem do guia; sem ele, nenhuma
dispara, e o dicionário passa sem filtro. Decisão: **roda assim, e é declarado**
no relatório e no `REGRAS_DO_LIMPADOR.md` como parte do que o braço mede — o
residual sem supervisão. O limite estrutural que resta é o item 7: o dicionário só
alcança célula que uma detecção aprovada marcou, e sem guia o crivo ainda aplica a
não-vacuidade e o teto de 0,30.

## 6. O limpador gerado e o `.md` de raciocínio

### `limpador_<ds>_<carimbo>.py`

```python
"""Cabecalho: dataset, carimbo, modelo, provedor, braco e receita do guia,
chamadas, aviso de que roda SEM o portao, e as duas memorias congeladas."""
import re

# o motor traz o proprio import de pandas
# --- motor.py, copia byte a byte: inicio ---
<texto de motor.py, lido do disco>
# --- motor.py: fim ---

GERACAO_TRUNCADA = False
UNIDADES_DEGRADADAS_POR_TETO = 0
DOMINANCIA = 0.7
REGRAS = [...]      # pprint.pformat de regras_literais
RESIDUAL = {...}    # {coluna: {sujo: limpo}}

def corrigir_1(valor): ...
FUNCOES = {"corrigir_1": corrigir_1}

def aplicar_detalhado(df):
    return aplicar_regras(df, REGRAS, RESIDUAL, FUNCOES, DOMINANCIA)

def aplicar(df):
    corrigido, flags, _ = aplicar_detalhado(df)
    return corrigido, flags

def main(): ...   # le CSV como texto literal, escreve o limpo e as flags
```

- **O motor é lido do disco e concatenado**, nunca guardado como template: a
  identidade byte a byte é verdadeira por construção, e um teste a confere.
- **As funções escalares são renomeadas pela AST** (`ast.unparse`). Isso
  normaliza formatação e descarta comentários; o `.md` mostra o texto **do
  limpador**, que é o que roda, e o raciocínio do LLM fica no CoT.
- **Literais determinísticos:** `pprint.pformat` ordena as chaves.
- **O `re` inteiro, e não o proxy do portão.** O portão entrega ao LLM um proxy de
  `re` com as funções permitidas e as flags; o limpador importa o módulo inteiro.
  É intencional — o limpador roda sem portão por desenho — e vira linha no
  `DECISOES.md#portao-ast`, para não parecer inconsistência.
- **Fumaça final.** Depois de gravar, `escrever` importa o arquivo e roda `aplicar`
  sobre o sujo. Falha aqui é bug do codificador e **levanta**. Ela não é
  redundante com o teste de integração: roda sobre o artefato real com a
  combinação de regras deste run, e transforma "o F1 veio zero" em "o limpador não
  importa", perto da causa.
- **Truncamento no artefato.** `GERACAO_TRUNCADA` e `UNIDADES_DEGRADADAS_POR_TETO`
  ficam no limpador. O `medir.py` as lê com `getattr` (padrão `False`, para os
  limpadores da POC 1), imprime um aviso **antes** da tabela e devolve `truncada`
  no resultado. Um run truncado não pode ser confundido com um completo.

### `raciocinio_<ds>_<carimbo>.md`

- **Cabeçalho:** dataset, modelo, braço, orçamento de supervisão (220 células +
  n pares), chamadas e tokens, marca de truncamento, coluna-sujeito e o
  raciocínio da escolha.
- **Por coluna:** a conformidade (padrões, motivo); **todas** as candidatas, com
  as `metricas` renderizadas como tabela chave-valor genérica e o CoT; para cada
  detecção aprovada, estratégia, parâmetros, CoT de três frases e o código da
  função; as entradas do residual, aceitas com justificativa e caídas com motivo;
  as falhas de LLM da coluna, lidas do registro do provedor.

**Se o `e6` passar de 200 linhas**, a ordem é: a tabela genérica de `metricas`
(já no desenho); depois renderizar o `.md` a partir de um template de string; e só
então reabrir a conversa. Verificação não se corta.

### Memórias congeladas

Duas coisas no limpador são memória, não padrão: o **dicionário residual** e o
**domínio de `vizinho_no_dominio`**. Ambas valem para valor que já apareceu e não
cobrem valor inédito. Congelar é o certo — recalcular na tabela nova faria o
limpador divergir do que o crivo aprovou —, e a seção 7 do
`REGRAS_DO_LIMPADOR.md` passa a listar as duas.

## 7. Custo de API

As duas tabelas têm 11 colunas.

| Etapa | Fórmula | Esperado | Teto |
|---|---|---|---|
| detector | 1 por coluna | 11 | 11 |
| especificador | 1 por detecção aprovada (≤ 1 por coluna e tipo) | ~15 | 55 |
| codificador | 1 por `normalizar`, mais no máximo 1 nova tentativa | ~6–10 | 2 × especificador |
| coluna-sujeito | 1 | 1 | 1 |
| residual | 1 por lote | ~5 | 10 |
| **por geração** | | **~40** | **~187** |

`config.TETO_CHAMADAS = 80` por geração limita o teto teórico (§3.1). Dois
datasets × dois braços dão **~160 chamadas esperadas**. O braço sem guia não tem
conformidade, então o detector usa o catálogo completo em toda coluna, e o
especificador tende a receber mais detecções.

**O primeiro run, em degraus**, cada um anunciado e aprovado pelo usuário antes:

1. **Sonda:** uma chamada que confirma, no `gpt-6-luna` com
   `reasoning_effort="none"`, o esquema estrito, `temperature` e `seed`, e mede
   os tokens de uma resposta curta.
2. **`beers` com guia**, ~40 chamadas. Medir; olhar o destino das 31 marcações da
   `brewery-name` (§8); se o limpador prestar, congelar o invariante.
3. **`environment` com guia e os dois braços sem guia**, ~120 chamadas.
4. **Linhas nunca vistas** (700 e 2.110), sem API.

## 8. Decisões do usuário registradas nesta rodada

- **Corte de schema: fica um terço.** Mudar para um quarto seria o primeiro
  limiar do projeto escolhido olhando a resposta, e contaminaria a defesa dos
  outros (`TETO_MARCACAO`, `DET_MINIMO`, a margem do teto). O custo conhecido —
  `brewery-name` com 31 marcações de precisão 0 na detecção — vai para o
  `DECISOES.md`. A métrica é de **reparo**: marcação não reparada vira flag e não
  entra na precisão. No primeiro run mede-se o **destino** das 31 (quantas
  reescritas, quantas flag), pela decomposição por fonte. Se forem reescritas
  erradas, há argumento empírico do comportamento do sistema, não do gabarito.
- **Ideia registrada, não implementada:** o que distingue `brewery-name` de
  `ounces` é a forma dos padrões (`Aa Aa Aa` contra `9`), não a quantidade.
  Schema com espaço ou muitas alternâncias de classe é texto livre, observável sem
  gabarito. Só se propõe depois de o primeiro run mostrar que o problema é real.

- **Modelo: `gpt-6-luna` com `reasoning_effort="none"`** (§3.1). **Ressalva de
  método, obrigatória ao reportar:** a POC 1 rodou com `gpt-4o-mini`, e ela é
  somente leitura, então não pode ser rodada de novo com o modelo atual. Toda
  comparação com o placar da POC 1 (24,4% e 13,2% de recall) muda **método e
  modelo ao mesmo tempo**, e a diferença não se atribui só ao método. A ressalva
  vai ao lado de cada número, como a do teto de dois terços.

## 9. Testes

Nenhum gasta API; todos vêm com prova por mutação registrada.

| Teste | Trava |
|---|---|
| `provedor` | `PROVEDOR` desconhecido levanta; `length` vira `cortada`; JSON inválido vira `json_invalido`; o teto vira `teto`; autenticação não vira `FalhaDoLLM`; `gravado` reproduz um run, e resposta ausente **levanta** em vez de degradar |
| `motor.aplicar_regras` | o reparo lê o original; quem escreve primeiro vence; o residual age só em célula marcada e não reparada; flag é marcada e não reparada |
| `e3_crivo` | o segundo crivo mantém `motivo`, `marcadas`, `taxa`, `teto` e só muda `taxa_uniao`; `crivar_residual` aplica os três vetos; sem guia, tudo passa |
| `e2_detector` | `formato` sai se e só se a conformidade foi aprovada; `dependencia` sai se e só se não há par minerado; variante malformada cai sozinha; teto de variantes; `FalhaDoLLM` deixa a coluna sem regra |
| `e4_especificador` | o domínio de `vizinho_no_dominio` é determinístico e não vem do LLM; a conversão valida campo a campo |
| `e6.codificar` | portão rejeita, uma nova tentativa com a mensagem, depois a regra cai; nomes únicos |
| `e5_residual` | lotes com ordem e composição determinísticas; resposta igual vira uma entrada, divergente vira `conflitante`; `null` e `limpo == sujo` ficam fora; `MAX_LOTES_RESIDUAL` vale |
| `e6.escrever` | o bloco embutido é byte a byte `motor.py`; duas escritas da mesma entrada dão o mesmo texto; as constantes de truncamento são gravadas; o `.md` lista as reprovadas |
| `medir` | o aviso de truncamento aparece; os limpadores da POC 1 seguem com os números exatos |
| vazamento em execução | durante `gerar_limpador`, `pd.read_csv` e `open` só abrem o sujo, os dois CSVs do guia e o `motor.py` |
| ponta a ponta | `gerar_limpador` sobre o `beers` com o dublê, e `medir.avaliar` sobre o arquivo gerado |

**O invariante**, depois do primeiro run pago que prestar: congelam-se em
`tests/fixtures/` o limpador **e** o `respostas.jsonl`. Dois testes: os números do
limpador congelado, medidos pelo `medir.py`; e a geração com `PROVEDOR=gravado` a
partir das respostas congeladas reproduz o limpador **byte a byte**. O segundo dá
sentido a "reprodutível dadas as respostas" e morde toda mudança de código que
altere o artefato.

## 10. Orçamento de linhas

| | Linhas (estimativa) |
|---|---|
| `provedor.py` | ~70 |
| `e2_detector.py` | ~140 |
| `e4_especificador.py` | ~120 |
| `e5_residual.py` | ~150 |
| `e6_codificador.py` | ~195 |
| `espinha.py` (com CLI) | ~45 |
| `motor.py` | 183 → ~198 (−15 da simplificação, +30 de `aplicar_regras`) |
| `e3_crivo.py` | 175 → ~190 (`crivar_residual` entra, a conta `sujo != guia` repetida três vezes se consolida) |
| `tipos.py`, `config.py`, `medir.py` | +28 |
| **total** | **~1.720 de 1.800** |

16 arquivos de 16. `motor`, `e3_crivo` e `e6` fecham perto de 200: é o ponto mais
apertado do plano, medido antes de cada commit (`CLAUDE.md` §2).

## 11. Ordem de implementação

Num branch próprio, cada passo com TDD e prova por mutação:

0. Apagar `limpeza2/__init__.py`; corrigir a contagem do `CLAUDE.md` §9.
1. `motor`: simplificar `reparar` sem mudar comportamento; acrescentar
   `aplicar_regras`.
2. `tipos.regras_literais`; `e3_crivo`: consolidar a conta repetida,
   `crivar_residual`, teste de idempotência.
3. `provedor` e `config`.
4. `e2_detector`.
5. `e4_especificador`.
6. `e6.codificar`.
7. `e5_residual`.
8. `e6.escrever`, aviso de truncamento no `medir.py`, teste de identidade do
   motor.
9. `espinha` com CLI, teste de vazamento em execução, teste de ponta a ponta.
10. Documentos: `DECISOES.md` (modelo e ressalva de método em `#provedor`,
    determinismo, falha de API, residual sem guia, veto
    no dicionário, domínio como memória, `re` proxy contra `re` inteiro, custo do
    corte de um terço); `REGRAS_DO_LIMPADOR.md` §7; `CLAUDE.md` §9 (espinha,
    tipos, contagem); `CONTINUACAO.md`.

O run pago (§7) vem depois, e só com aprovação.

## 12. Riscos

| Risco | Medida |
|---|---|
| `gpt-6-luna` recusa esquema estrito, `temperature` ou `seed` | a sonda do §7 descobre com uma chamada; `SAIDA_ESTRITA` e `TEMPERATURA = None` são o plano B, já no desenho |
| raciocínio em `none` dá regras fracas | subir `ESFORCO_RACIOCINIO` é uma linha de `config`, mas muda o limpador congelado: decisão registrada, com fixture nova |
| `motor`, `e3_crivo` ou `e6` passam de 200 linhas sem vaga de arquivo | simplificar primeiro, na ordem do §6; nunca espremer formatação nem cortar verificação; reabrir a conversa se nada bastar |
| um prompt passa de ~40 linhas | reabrir a decisão do §3.5 |
| o residual infla o F1 na tabela de origem | medição nos dois locais e decomposição por fonte (spec de 11/10, §8) |
| o residual sem guia degrada o limpador | é o que o braço sem guia mede; declarado |
| run truncado comparado com run completo | a marca vai no artefato, no `.md` e na saída do `medir.py` |

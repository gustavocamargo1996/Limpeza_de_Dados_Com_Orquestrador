# CLAUDE.md — POC de Limpeza de Dados 2

Leia este arquivo antes de tocar em qualquer coisa. Na primeira sessão, leia
também o `HANDOFF.md`: ele conta o que a POC 1 ensinou e o que o usuário quer
desta.

Este arquivo tem duas partes. As **seções 1 a 8** são requisitos do usuário e
valem desde o primeiro commit. A **seção 9** (arquitetura) está vazia de
propósito: a estratégia de detecção ainda vai ser escolhida no brainstorming.
Quando ela for decidida, preencha a seção 9. Quando este arquivo divergir do
código, **o código ganha**, e corrigir este arquivo faz parte da tarefa que
causou a divergência.

---

## 1. O que é

São duas fases, com entradas diferentes:

| Fase | Entra | Sai |
|---|---|---|
| **Geração** | o CSV **sujo** e, opcionalmente, um **guia** pequeno (seção "Guia e gabarito") | `limpador_<dataset>_<carimbo>.py`, um script Python autônomo, sem dependência deste repositório e aplicável a qualquer tabela da mesma origem; e a **cadeia de raciocínio** de cada regra, em Markdown legível |
| **Validação** | o limpador gerado, o sujo e o **gabarito** (o CSV limpo completo) | a **qualidade** do limpador: precisão, recall e F1 de reparo |

**O produto é o PROGRAMA de limpeza, não a tabela limpa.** A tabela corrigida
serve só para medir. Uma mudança que melhora a tabela mas piora o limpador
gerado é regressão.

### Três agentes: requisito do usuário, não detalhe de implementação

| Agente | Faz | Não faz |
|---|---|---|
| **detector** | decide onde estão os erros | não corrige |
| **especificador** | escreve a regra de correção em linguagem estruturada, com o raciocínio | não escreve Python |
| **codificador** | traduz a especificação em Python | não decide o que é erro |

A **estratégia** de cada agente é livre e pode ser totalmente diferente da POC
1. A **separação** em três papéis não é livre.

### Alinhamento com a dissertação

Esta POC é um passo rumo ao framework do capítulo 4 da qualificação
(`HANDOFF.md` §5). Dois princípios de lá valem aqui como requisito: o
conhecimento do LLM é **convertido em código reexecutável**, e não chamado a
cada execução; e **execução, auditoria e medição são determinísticas**, sem
LLM. Os agentes só atuam na geração.

### Guia e gabarito: o limpo são dois conceitos, e não se misturam

Requisito do usuário e coração metodológico desta POC. Na POC 1, a geração
sorteava células do limpo **inteiro** e um oráculo rotulava mais a cada
iteração, o que nenhum humano faria numa base real. Aqui o limpo se divide em
dois artefatos, com donos e momentos diferentes:

| | **Guia** | **Gabarito** |
|---|---|---|
| Quando entra | na **geração** | só na **validação** |
| Obrigatório? | **não**: o limpador tem de ser gerado mesmo só com o sujo | sim, para medir |
| Tamanho | pequeno: **20 linhas corrigidas** e **poucos pares `sujo → limpo`** | a tabela limpa inteira |
| Quem produz, num caso real | um humano que abre o dataset e, por inspeção visual, pega algumas linhas, deixa-as corretas e aponta alguns erros grosseiros com a correção | já existe (benchmark) ou é construído à parte |
| Para que serve | um few-shot: mostrar ao LLM o schema, o formato de cada campo, o relacionamento entre campos e exemplos de erro | medir se o limpador é bom |

As 20 linhas são sorteadas de **qualquer** parte da tabela, com os valores do
CSV limpo, e há sempre 20, em qualquer dataset. O guia é uma referência
corrigida: o humano pegou algumas linhas e as deixou corretas. **Orçamento de
supervisão:** 20 linhas inteiramente corretas, isto é, 20 × 11 = **220 células
rotuladas** num dataset de 11 colunas, mais até 2 pares por coluna com erro. O
crivo usa essas células como oráculo de correção (não só como "não mexa"), e
isso é mais supervisão que a do critério antigo: ela é reportada ao lado de
cada número. Ver `docs/DECISOES.md#guia-sorteado`.

**O gabarito nunca é lido pela geração**, nem para amostrar, nem para validar
regra, nem para escolher parâmetro. A geração lê o sujo e o guia, e só. Se o
gabarito vazar para a geração, a POC mede memorização e todo número publicado
vira ficção. O teste que trava isso tem de existir desde a primeira etapa.

**As linhas que aparecem no guia ficam fora da métrica** (holdout). Medir
nelas mede o que o LLM viu, não o que ele generalizou.

Consequências para o desenho:

- Com guia pequeno, **não dá para aprovar uma regra por "acertar 100% dos
  rotulados"** como na POC 1: há poucos pares, escolhidos por serem erros
  grosseiros, e o gate passaria por vacuidade na maioria das colunas
  (`HANDOFF.md` §4, lição 6). As linhas do guia, porém, servem de
  **oráculo por célula**: uma regra que marca ou altera uma célula que o sujo
  já tinha certa está errada, e um reparo que escreve numa célula do guia um
  valor diferente do guia também.
- Nos benchmarks, o guia precisa ser **reprodutível**: fixado em arquivo,
  versionado e igual entre runs. O jeito de produzi-lo (escolhido à mão pelo
  usuário ou simulado por um procedimento com semente fixa) é decisão do
  usuário (`HANDOFF.md` §8).

---

## 2. Teto de tamanho: dois terços da POC 1

A POC 1 tinha **26 arquivos `.py` e 2.810 linhas** de código de produção (fora
`tests/`). Esta POC tem de caber em:

| Medida | Teto | Fração da POC 1 |
|---|---|---|
| arquivos `.py` fora de `tests/` | **16** | 62% |
| linhas nesses arquivos | **1.800** | 64% |
| maior arquivo | **200 linhas** | — |

**O requisito original era metade: 13 arquivos e 1.400 linhas.** O usuário o
elevou em 12/10/2026, com a parte 1 em 911 linhas e a parte 2 projetada em mais
700. A causa é rastreável e não foi desleixo: a parte 1 foi estimada em cerca de
700 linhas e entregou 911, e as 211 a mais são o controle negativo por célula, o
teto informado pelo guia, o veto por valor certificado, a correção do
determinismo do reparo e a simetria do piso do guia — cada uma aprovada
separadamente, e cada uma consertando um defeito achado por revisão ou por prova
por mutação.

**Isto tem de ser declarado ao reportar**, na dissertação inclusive: a POC 2 não
cumpre o "metade da POC 1" que o usuário pediu no começo. Ela cumpre dois terços,
e a diferença comprou os cinco mecanismos acima. Omitir isso seria apresentar um
número que o projeto não alcançou.

**A reserva foi usada.** `limpeza2/__init__.py` estava vazio e foi apagado na
parte 2 (12/10/2026), abrindo a vaga do 16º arquivo. O projeto fecha em 16 de 16,
sem folga.

**O que o teto de arquivos protege não é a contagem, é a legibilidade.** O risco
que o usuário quer evitar é se perder na função de cada `.py` por estarem muito
fracionados. Então valem duas regras, e a segunda manda mais que o número:

- Todo arquivo cabe numa frase que diz o que ele faz. Se a frase tiver "e",
  o arquivo faz duas coisas.
- **Nunca fracione para caber no teto de linhas.** Se um arquivo passa de 200
  linhas, primeiro procure o que simplificar; só então separe — e separe pela
  função, nunca pelo tamanho. Um arquivo de 190 linhas com uma função clara é
  melhor que dois de 95 com funções difusas.

A folga de arquivos existe para esse caso, não para acomodar desenho novo.

**O teto vale só para o gerador, desde 17/10/2026.** Com o orquestrador no mesmo
repositório (`docs/superpowers/specs/2026-10-17-orquestrador-design.md`), o usuário
decidiu que a medida conta só `limpeza2/`, `preparar_guia.py` e `medir.py`, e elevou
o teto de linhas do gerador para **1.850**, para caber as adaptações que o
orquestrador exige (decisões do usuário e reaproveitamento de respostas). Ele
decidiu também que **não corromper o código que funciona vale mais que o teto**: as
adaptações são inserções, sem refatorar para caber, e um estouro pequeno é aceito e
declarado aqui. O orquestrador tem orçamento próprio: **14 arquivos, 1.400 linhas,
maior arquivo com 200**, com as mesmas regras de legibilidade.

**O estouro, declarado (17/10/2026):** as inserções levaram o gerador a **1.875
linhas** (25 acima de 1.850) e `limpeza2/e3_crivo.py` a **211** (11 acima de 200).
O crivo ganhou o motivo `rejeitada_pelo_usuario`, a prioridade da regra aprovada e
o veto do residual; o provedor ganhou o modo `reaproveitar` e suas duas travas.
Nada foi refatorado para caber, por decisão do usuário.

Meça antes de todo commit que acrescenta código:

```bash
git ls-files "limpeza2/*.py" preparar_guia.py medir.py | wc -l
git ls-files "limpeza2/*.py" preparar_guia.py medir.py | xargs wc -l | tail -1
git ls-files "orquestrador/*.py" | xargs wc -l | tail -1
```

Estourar o teto é defeito, não detalhe. A saída é simplificar o desenho, não
espremer a formatação.

---

## 3. A espinha: etapas em ordem, num só lugar

- Existe **uma** função que chama as etapas em ordem, e ela é a primeira coisa
  que alguém lê. Nenhum outro lugar guarda a sequência.
- Cada módulo corresponde a uma etapa, e o docstring do módulo diz o número
  dela. A ordem dos arquivos no diretório ajuda a ler a ordem dos
  acontecimentos.
- Tudo o que viaja entre etapas está num único módulo de tipos.
- Configuração ajustável (modelo, caminhos do guia, limiares) fica num único módulo
  de config.

## 4. Uma fonte só: o que se mede é o arquivo gerado

Lição mais cara da POC 1. Lá, a lógica de detecção e correção existia **duas
vezes**, uma na POC e uma cópia congelada dentro do limpador gerado, e as
duas divergiram. O run publicava F1 = 100% numa coluna em que o limpador
entregue marcava zero células. Consertar isso custou um projeto inteiro.

Regra: **a métrica é calculada executando o limpador gerado**, nunca uma
implementação paralela. Se a POC precisa aplicar regras para medir, ela
escreve o limpador e o executa. Não pode existir uma segunda cópia da lógica
de aplicação.

## 5. Código não verboso

- **Docstring de 1 linha.** Se não cabe em uma linha, o raciocínio vai para
  `docs/DECISOES.md` e o código guarda um link para a âncora.
- **Comentário inline: no máximo 2 linhas.** Descreve a mecânica do que está
  ali. Não comente histórico ("antes era..."), medição ("reduz 40%"),
  comparação com outros sistemas nem planos ("aqui poderíamos...").
- **Exceção só com degradação nomeada.** Todo `try` existe porque a falha tem
  um comportamento definido (a coluna fica sem regra, a célula vira flag),
  nunca como rede genérica. Uma coluna ruim não derruba o run, e existe **uma**
  fronteira de resiliência por coluna, não várias paralelas.
- **Loops:** junte loops paralelos (dois `for` sobre a mesma sequência viram
  um). Mantenha separados os que carregam estado entre iterações.
- Sem abstração especulativa: nada de classe, parâmetro ou camada para um uso
  que ainda não existe.

## 6. Código gerado por LLM passa por um portão

Todo Python escrito por LLM é validado antes de rodar: análise da AST com
allowlist de builtins, proibição de `import`, dunder, `eval`/`exec`/`open`/
`getattr`, e execução em namespace descartável, nunca `globals()`. Afrouxar o
portão é decisão de segurança, não conveniência.

A POC 1 tem uma implementação em `../POC_Limpeza_de_Dados/limpeza/sandbox.py`,
que foi copiada e adaptada. **Ela tem um escape**, confirmado por execução em
12/10/2026: ela entrega o módulo `re` ao namespace, e dele se alcança
`re.enum.sys.modules["os"]`. O portão desta POC entrega um **proxy** de `re`,
barra leitura de `.format` e `.format_map`, barra escrita e remoção de atributo,
e constrói um proxy novo por materialização. Detalhe e evidência em
`docs/DECISOES.md#portao-ast`. Não copie mais nada de lá sem sondar primeiro.

O limpador gerado roda **sem** o portão na máquina do usuário. O cabeçalho
dele avisa isso.

## 7. Provedores de LLM e privacidade

- Um único módulo sabe que existe mais de um provedor (OpenAI e Ollama). Os
  agentes pedem um cliente a ele e não importam SDK nenhum.
- **`PROVEDOR` desconhecido falha alto.** Os dados do usuário não podem sair
  da rede quando o provedor local é o escolhido. Um typo que caísse
  silenciosamente para OpenAI mandaria a tabela para fora.
- Chave e modelo vêm do `.env`, que nunca é commitado.

## 8. Testes, invariante e processo

- **Nenhum teste gasta API.** Os agentes são substituídos por dublês.
- **Invariante desde cedo.** Assim que existir um limpador gerado que preste,
  congele-o em `tests/fixtures/` e trave os números dele num teste. Os números
  não são meta: são a assinatura do comportamento. **Mudar esses números é
  bug, não melhoria**, a menos que o usuário decida que é mudança de
  comportamento, com entrada nova em `docs/DECISOES.md` e fixture nova.
- **Todo teste novo vem com prova por mutação:** quebre o código de propósito,
  veja o teste falhar, reverta. Um teste que não morde não conta.
- **Skip não é cobertura.** Se um teste pula por falta de recurso local, diga.
- Um run que gasta API é decisão do usuário. Anuncie antes de disparar.

### Idioma e ambiente

- **Português do Brasil em tudo:** identificadores, docstrings, comentários,
  logs, documentos, commits e respostas ao usuário. As exceções são nomes de
  bibliotecas externas (`pd.Series`, `random_state`) e colunas dos datasets.
- **Sem acento em identificadores e em strings de log.** O stdout do Windows
  abre em cp1252. Os documentos usam acentuação normal.
- O `.venv` é criado com **uv**, que não instala `pip` dentro dele. Instale
  com `uv pip install -r requirements.txt`. Rode Python com
  `.venv/Scripts/python`.
- Os dados são carregados como texto literal:
  `pd.read_csv(..., dtype=str, keep_default_na=False, na_values=[])`. Senão
  `'N/A'` vira NaN e a medida mente.

---

## 9. A arquitetura

Decidida no brainstorming de 11/10/2026. Design completo em
`docs/superpowers/specs/2026-10-11-geracao-de-limpador-design.md`; regras em
linguagem de usuário em `docs/REGRAS_DO_LIMPADOR.md`.

### Árvore de módulos

```
limpeza2/
  tipos.py              # o que viaja entre etapas
  config.py             # modelo, caminhos, limiares, semente
  provedor.py           # entrega o cliente do provedor de LLM escolhido
  portao.py             # valida o Python gerado antes de deixa-lo rodar
  motor.py              # UNICA implementacao de aplicacao de regra (inclui padrao e aplicar_regras)
  conformidade.py       # deriva o schema de cada coluna das celulas que o guia certificou
  limites.py            # calcula os limites que o guia sustenta para uma coluna
  e1_perfil.py          # etapa 1: perfila a tabela suja, lida como texto literal
  e2_detector.py        # etapa 2: agente detector -> predicados candidatos
  e3_crivo.py           # etapa 3: reprova a regra candidata que nao se sustenta
  e4_especificador.py   # etapa 4: agente especificador -> JSON de reparo
  e5_residual.py        # etapa 5: rodada residual por entidade -> dicionario
  e6_codificador.py     # etapa 6: agente codificador -> escreve os artefatos de saida
  espinha.py            # a ordem das etapas, e nada mais; o CLI so a chama
preparar_guia.py        # fora do pacote: sorteia o guia com semente fixa
medir.py                # fora do pacote: executa o limpador gerado e mede
```

Dezesseis arquivos, cada um com uma função que cabe numa frase. É o teto da
seção 2, e não resta folga: a vaga do 16º veio do `limpeza2/__init__.py`, que
estava vazio e foi apagado. Se `e6_codificador.py`, `motor.py` ou `e3_crivo.py`
passarem de 200 linhas, a saída é simplificar, nunca fracionar.

Os dois módulos fora do pacote são os únicos que abrem o CSV limpo, e é isso que
torna o §1 verificável: nenhum módulo de `limpeza2/` importa `preparar_guia` nem
`medir`, e o teste de vazamento assevera isso.

### A espinha

```python
def gerar_limpador(caminho_sujo, caminho_guia, destino):
    """Etapas 1 a 6 em ordem: a unica sequencia do projeto."""
    provedor.iniciar(destino)
    entrada = e1_perfil.perfilar(caminho_sujo, caminho_guia)
    conformes = conformidade.candidatas_de_conformidade(entrada)
    schema = e3_crivo.crivar_deteccao(conformes, entrada)
    candidatas = e2_detector.propor(entrada, schema, conformes)
    deteccoes = e3_crivo.crivar_deteccao(schema + candidatas, entrada)
    propostas = e4_especificador.especificar(deteccoes, entrada)
    codificadas, funcoes = e6_codificador.codificar(propostas, entrada)
    reparos = e3_crivo.crivar_reparo(codificadas, entrada, funcoes)
    sugestoes = e5_residual.resolver(deteccoes, reparos, funcoes, entrada)
    residual = e3_crivo.crivar_residual(sugestoes, entrada)
    return e6_codificador.escrever(
        deteccoes, reparos, residual, conformes + candidatas, entrada, destino
    )
```

O crivo aparece quatro vezes: sobre a conformidade, para o detector saber onde ela
já cobre a forma; sobre todas as detecções; sobre os reparos; e sobre o dicionário
residual. O codificador aparece duas: escreve as funções `corrigir` antes do crivo
do reparo, que precisa delas, e monta os arquivos no fim. A validação não está na
espinha: é a outra fase, `medir.avaliar(...)`. Detalhe na spec da parte 2.

### Tipos que viajam (`tipos.py`)

`Entrada` (sujo, guia_linhas, guia_pares, perfil) ·
`Candidata` (coluna, tipo, parametros, raciocinio, metricas) ·
`Reparo` (candidata, estrategia, parametros, raciocinio, codigo) ·
`Residual` (coluna, mapa, justificativas, caidas) ·
`regras_literais(deteccoes, reparos)`, a forma em que as regras viajam até o limpador.

### A estratégia de cada agente

| Agente | Estratégia | Por quê | Âncora |
|---|---|---|---|
| **detector** | emite parâmetros de um catálogo fechado de 5 tipos (`formato`, `dominio`, `faixa`, `ausente_disfarcado`, `dependencia`), sempre avaliados sobre a linha; 3 variantes por tipo | saída de 5 a 20 tokens evita o estouro que quebrou `Eco_Status`; a dependência alcança os 21,5% de erros invisíveis a regra intra-coluna. Ordem dos tipos e mineração-antes-do-veredito vêm do **Cocoon**; perfil de frequências do **ZeroED**; as 3 variantes do **ZeroEC** | `#catalogo-fechado`, `#regra-sobre-a-linha` |
| **especificador** | emite JSON curto com uma de 5 estratégias (`normalizar`, `moda_condicionada`, `vizinho_no_dominio`, `dicionario`, `esvaziar`) mais CoT de 3 frases | formato intermediário e CoT do **ZeroEC**; `moda_condicionada` é o que corrigiu 54/54 e 26/26 na POC 1 quando não envenenada; o lado errado da violação vem da versão barata do **BClean+** | `#catalogo-fechado`, `#lado-errado-da-dependencia` |
| **codificador** | escreve apenas as funções escalares `corrigir(valor) -> str`; todo o resto do limpador é `motor.py` parametrizado, copiado byte a byte | funções escalares passam no portão sem pandas no namespace; uma só implementação da aplicação impede a divergência que custou um projeto na POC 1. `try/except` com sentinela do **CodeGenWrangler** | `#motor-unico`, `#portao-ast` |

Fora dos três agentes, duas chamadas de LLM auxiliares: escolher a
coluna-sujeito entre as candidatas mineradas, e a rodada residual.

A aposta de recall está na **etapa 5**: a ablação do **ZeroEC** sem o passo
residual dá precisão de 1,00 e recall de 0,70 no Hospital e 0,00 no Rayyan, que
é o perfil da POC 1. O agrupamento do lote por entidade vem do **IterClean**
(F1 do `flights` cai de 0,595 para 0,164 sem ele). O residual é congelado como
dicionário, nunca chamado em execução — e isso custa generalização, medida pela
dupla medição.

### O que foi recusado

Loop evolutivo de regras Python livres (variância contra o teste de invariante);
grafo bayesiano completo do BClean+ (reduz os três agentes a quase nada e
congela tabelas grandes no limpador); laço de anotação ativa do ZeroDC (no
código publicado ele lê o `_clean.csv`); arquivos de restrição do benchmark
(`FunctionalDependency.txt`, `TypeConstraint.txt`, `real_examples.txt`) em
qualquer fase.

### As decisões do usuário e o reaproveitamento (17/10/2026)

Duas entradas opcionais, acrescentadas para o orquestrador, que deixam o gerador
idêntico ao de antes quando ausentes:

- **`decisoes.json` na pasta do guia:** `rejeitar` e `aprovar` por regra, com
  instrução opcional ao especificador. Aprovar nunca dispensa os testes contra o
  guia. `docs/DECISOES.md#decisoes-do-usuario`.
- **`PROVEDOR=reaproveitar`** com `RESPOSTAS_GRAVADAS` e `PROVEDOR_VIVO`: responde
  do gravado e só chama a API para o prompt que mudou.
  `docs/DECISOES.md#reaproveitar`.

---

## 10. Onde não mexer

**`../POC_Limpeza_de_Dados/`** é a POC 1. É **somente leitura** para esta
POC: pode ler, citar e copiar código dela, mas nunca editar, commitar ou
rodar comando que escreva lá.

**`orquestrador/`** é outro componente, com spec própria
(`docs/superpowers/specs/2026-10-17-orquestrador-design.md`). Ele usa o gerador só
por subprocesso, chamando `limpeza2.espinha.gerar_limpador`, e nenhum módulo de
`limpeza2/` pode importar algo de `orquestrador/`. O gerador continua funcionando
sozinho, pela linha de comando de sempre.

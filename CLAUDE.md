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
| Tamanho | pequeno: cerca de **20 linhas limpas** e **poucos pares `sujo → limpo`** | a tabela limpa inteira |
| Quem produz, num caso real | um humano que abre o dataset e, por inspeção visual, separa algumas linhas certas e alguns erros grosseiros com a correção | já existe (benchmark) ou é construído à parte |
| Para que serve | um few-shot: mostrar ao LLM o schema, o formato de cada campo, o relacionamento entre campos e exemplos de erro | medir se o limpador é bom |

As 20 linhas são um **teto, não uma garantia**. Medido em 12/10/2026: o
`beers_dirty_300` tem apenas **5 linhas sem nenhum erro**, porque a coluna
`ounces` está errada em 295 das 300 linhas; o `environment_dirty_300` tem 85.
Onde não houver 20 linhas totalmente limpas, o guia sai menor, e o tamanho real
dele é reportado ao lado de cada número. A consequência é que no `beers` o
controle negativo fica fraco — 5 linhas vezes 11 colunas, 55 células — e isso
precisa ser dito ao reportar o resultado desse dataset.

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
  (`HANDOFF.md` §4, lição 6). As linhas limpas do guia, porém, servem de
  **controle negativo**: uma regra que altera ou marca uma célula que o humano
  disse estar certa está errada.
- Nos benchmarks, o guia precisa ser **reprodutível**: fixado em arquivo,
  versionado e igual entre runs. O jeito de produzi-lo (escolhido à mão pelo
  usuário ou simulado por um procedimento com semente fixa) é decisão do
  usuário (`HANDOFF.md` §8).

---

## 2. Teto de tamanho: metade da POC 1

Requisito explícito do usuário. A POC 1 tinha **26 arquivos `.py` e 2.810
linhas** de código de produção (fora `tests/`). Esta POC tem de caber em:

| Medida | Teto |
|---|---|
| arquivos `.py` fora de `tests/` | **13**, e **15** no limite, só com necessidade demonstrada |
| linhas nesses arquivos | **1.400** |
| maior arquivo | **200 linhas** |

**O que o teto de arquivos protege não é a contagem, é a legibilidade.** O risco
que o usuário quer evitar é se perder na função de cada `.py` por estarem muito
fracionados. Então valem duas regras, e a segunda manda mais que o número:

- Todo arquivo cabe numa frase que diz o que ele faz. Se a frase tiver "e",
  o arquivo faz duas coisas.
- **Nunca fracione para caber no teto de linhas.** Se um arquivo passa de 200
  linhas, primeiro procure o que simplificar; só então separe — e separe pela
  função, nunca pelo tamanho. Um arquivo de 190 linhas com uma função clara é
  melhor que dois de 95 com funções difusas.

Os dois arquivos de folga existem para esse caso, não para acomodar desenho
novo.

Meça antes de todo commit que acrescenta código:

```bash
git ls-files "*.py" ":!tests/" | wc -l
git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1
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
  motor.py              # UNICA implementacao de aplicacao de regra
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

Quatorze arquivos, cada um com uma função que cabe numa frase. A seção 2 admite até
quinze, e a folga é para quando `e6_codificador.py` ou `motor.py` passarem de 200
linhas: aí separa-se a parte que tem função própria, nunca se fraciona pelo
tamanho.

Os dois módulos fora do pacote são os únicos que abrem o CSV limpo, e é isso que
torna o §1 verificável: nenhum módulo de `limpeza2/` importa `preparar_guia` nem
`medir`, e o teste de vazamento assevera isso.

### A espinha

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

O crivo aparece duas vezes porque o controle negativo do guia vale para a regra
que detecta e para a que repara. A validação não está na espinha: é a outra
fase, `medir.medir(...)`.

### Tipos que viajam (`tipos.py`)

`Entrada` (sujo, guia_linhas, guia_pares, perfil, coluna_sujeito) ·
`Candidata` (coluna, tipo, parametros, raciocinio, metricas_crivo) ·
`Reparo` (candidata, estrategia, parametros, raciocinio, codigo) ·
`Residual` (coluna, mapa, justificativas).

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

---

## 10. Onde não mexer

**`../POC_Limpeza_de_Dados/`** é a POC 1. É **somente leitura** para esta
POC: pode ler, citar e copiar código dela, mas nunca editar, commitar ou
rodar comando que escreva lá.

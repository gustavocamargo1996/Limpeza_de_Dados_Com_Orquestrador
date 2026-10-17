# Handoff: do gerador de limpadores para o orquestrador

> **Comece por aqui.** Você vai construir o orquestrador descrito em
> `docs/especificacoes_do_humano/especificacao_orquestrador_limpeza_dados.md`.
> Este documento diz o que você precisa saber do **gerador de limpadores** (o
> pacote `limpeza2/`), que é o componente central do orquestrador. Leia nesta
> ordem: este arquivo, a especificação do humano, o `CLAUDE.md` (as regras que
> valem para o gerador) e o `docs/CONTINUACAO.md` (o estado do gerador e os
> resultados medidos). Escrito em 17/10/2026, com o repositório em `c1df3b1`.

---

## 1. O gerador em um parágrafo

A partir de um CSV **sujo** e, opcionalmente, de um **guia** (algumas linhas
corrigidas por um humano), o gerador escreve um **limpador**: um script Python
autônomo, sem dependência deste repositório, que corrige tabelas da mesma origem.
Três agentes de LLM atuam só na geração (detector, especificador, codificador), e
um crivo determinístico reprova as regras que o guia desmente. O limpador gerado
roda **sem LLM**. O produto é o programa, não a tabela limpa.

Resultados medidos em 12/10/2026, com `gpt-6-luna`, em tabelas de 300 linhas
(`docs/CONTINUACAO.md` §7):

| Braço | Precisão real | Recall | Chamadas de API |
|---|---|---|---|
| `beers` com guia de 20 linhas | 98,6% | 98,4% | 31 |
| `beers` sem guia | 82,7% | 9,7% | 27 |
| `environment` com guia de 20 linhas | 95,2% | 74,1% | 28 |
| `environment` sem guia | 50,0% | 16,0% | 13 |

**A lição que mais importa para o orquestrador: quem carrega o resultado é o
guia.** A tela em que o usuário fornece a amostra-guia decide a qualidade do
limpador mais do que qualquer outra parte do sistema (seção 5.2).

## 2. A fronteira: o que o orquestrador usa e o que não toca

A especificação do humano exige (§4.3 e §4.4) que o gerador continue funcionando
sozinho e que os dois componentes fiquem separados. A forma de cumprir isso é o
orquestrador falar com o gerador por **três pontos de contato**, e nada mais:

| Ponto de contato | O que é | Onde está |
|---|---|---|
| **Gerar** | `gerar_limpador(caminho_sujo, caminho_guia, destino) -> Path` | `limpeza2/espinha.py` |
| **Arquivos de saída** | o limpador, o raciocínio e as respostas gravadas, em `destino` | seção 4 |
| **Aplicar** | o contrato do limpador gerado: `aplicar`, `aplicar_detalhado`, `REGRAS`, `main` | seção 6 |

Não importe os módulos internos (`e3_crivo`, `motor`, `e2_detector` …) no
orquestrador. Eles mudam, e a espinha é, por requisito, o único lugar que guarda a
ordem das etapas (`CLAUDE.md` §3).

## 3. Como gerar

```python
from limpeza2.espinha import gerar_limpador

caminho = gerar_limpador("dados/sujo.csv", "dados/guia/meu_esquema", Path("saida/meu_esquema_v1"))
```

Ou pela linha de comando, a partir da raiz do repositório:

```
.venv/Scripts/python -m limpeza2.espinha --sujo <csv> [--guia <pasta>] --nome <nome>
```

A linha de comando grava em `saida/<nome>_<AAAA-MM-DD_HHMM>/`. Pela função, você
escolhe o `destino`, o que é melhor para o versionamento do orquestrador.

- **`caminho_guia=None`** é o braço sem guia: funciona, mas com o recall da tabela
  acima.
- **`destino.name`** entra no nome dos arquivos e no cabeçalho do limpador. Use um
  nome de versão estável, por exemplo `<esquema>_<data>`.
- **Duração e custo:** cerca de 1 min 40 s e 30 chamadas para 300 linhas e 11
  colunas, com custo de centavos de dólar. Há um teto rígido de 80 chamadas por
  geração (`config.TETO_CHAMADAS`). Tabelas maiores **não foram testadas**: o perfil
  compara todos os pares de colunas, e os prompts levam o guia inteiro.
- **Erros:** falhas transitórias de API degradam por unidade (a coluna fica sem
  aquela regra, e o motivo vai ao raciocínio). Chave errada, modelo inexistente ou
  limpador gerado que não importa **levantam exceção**: trate como falha da etapa.
- **Uma geração por processo.** O cliente do provedor é um global do módulo
  (`provedor._atual`), aberto por `provedor.iniciar(destino)`. Rode cada geração
  num **subprocesso** (a linha de comando serve): isola o global, permite medir o
  tempo e não trava a interface.
- **Configuração:** `.env` na raiz do repositório com `PROVEDOR` (`openai`,
  `ollama` ou `gravado`), `MODELO` (`gpt-6-luna`) e `OPENAI_API_KEY`. `PROVEDOR`
  desconhecido falha alto, de propósito: os dados não podem sair da rede por um
  erro de digitação. Com `openai`, **as linhas da tabela vão para a API da
  OpenAI**. O caminho `ollama` existe, mas nunca rodou de verdade.

## 4. Entradas e saídas, no formato exato

### Entrada: o CSV sujo

Lido sempre como texto literal (`config.LER_CSV`:
`dtype=str, keep_default_na=False, na_values=[]`). As linhas são indexadas de 0 em
diante, na ordem do arquivo, sem contar o cabeçalho.

### Entrada: a pasta do guia

Uma pasta com até dois arquivos. Os dois são opcionais, e o formato de referência é
o que `preparar_guia.py` grava (`dados/guia/beers/` é um exemplo real):

| Arquivo | Colunas | Significado |
|---|---|---|
| `guia_linhas.csv` | `_linha` + todas as colunas do sujo | linhas **corrigidas** por um humano; `_linha` é o índice dessa linha no CSV sujo |
| `guia_pares.csv` | `linha, coluna, sujo, limpo` | erros apontados um a um, fora das linhas acima |

`preparar_guia.py` **não serve ao orquestrador**: ele sorteia o guia lendo o CSV
limpo do benchmark, que numa base real não existe. O orquestrador monta esses dois
arquivos a partir do que o usuário fornece.

### Saída: a pasta `destino`

| Arquivo | Conteúdo |
|---|---|
| `limpador_<destino.name>.py` | o limpador autônomo (seção 6) |
| `raciocinio_<destino.name>.md` | cada regra proposta, aprovada ou não, com motivo e métricas (seção 5.4) |
| `respostas.jsonl` | a primeira linha é a origem (provedor, modelo, esforço); cada linha seguinte é uma chamada ao LLM, com `etapa`, `unidade` e a resposta crua |

O `respostas.jsonl` permite **regenerar o mesmo limpador sem gastar API**
(`PROVEDOR=gravado` e `RESPOSTAS_GRAVADAS=<caminho>`). Guarde-o junto de cada
versão do limpador.

## 5. A especificação do humano, item por item, contra o que o gerador faz

### 5.1 Identificação do esquema (1.2.a, 1.2.h)

O gerador não tem registro de esquemas. O limpador gerado depende dos **nomes das
colunas**: cada regra em `REGRAS` cita sua `coluna`, e aplicá-lo a uma tabela sem
essa coluna lança `KeyError`. Colunas a mais não atrapalham. Então "esquema
conhecido" pode ser decidido pelo conjunto de nomes de colunas, e essa decisão é
do orquestrador.

### 5.2 A amostra-guia (1.2.c): a decisão mais importante

A especificação diz que a amostra-guia é uma "pequena amostra de registros
considerados corretos" e sugere um formulário com "por exemplo, cinco" linhas.
Isso tem dois efeitos que você precisa conhecer.

**O número de linhas muda o que o gerador consegue fazer.** A conformidade de
schema, que responde pela maior parte do recall, só reconhece que uma coluna tem
schema se os padrões distintos no guia forem no máximo um terço das linhas do
guia (`config.FRACAO_PADROES_SCHEMA`). Com 20 linhas, cabem até 6 padrões; com 5,
só 1. Medido em 17/10/2026, sem API:

| Dataset | Conformidade aprovada com 20 linhas | Com 5 linhas |
|---|---|---|
| `beers` | `ounces`, `abv`, `ibu`, `brewery-name`, `city`, `state` | `ounces`, `abv`, `state` |
| `environment` | `Monitoring_Station_ID`, `Temperature`, `Measurement_Date` (e `Project_Name`, sem os pares) | `City`, `Monitoring_Station_ID`, `Measurement_Date` |

Só a perda de `ibu` custa 101 dos 445 erros do `beers`. O desenho do gerador
assume 20 linhas (`config.LINHAS_GUIA = 20`; `CLAUDE.md` §1).

**De onde vêm as linhas também importa.** O crivo usa o guia de dois jeitos:

- **pelos valores**: o schema de cada coluna e os valores certificados. Funciona
  com quaisquer linhas corretas;
- **por célula**: compara, na mesma linha, o valor sujo com o corrigido. Isso só
  funciona se `_linha` aponta para uma linha que existe no CSV sujo. É o que
  reprova a regra que marca ou escreve errado numa célula que o humano conferiu, e
  é a principal defesa de precisão.

Linhas digitadas do zero pelo usuário mantêm o primeiro uso e perdem o segundo.
Por isso a recomendação é que o **template e o formulário venham pré-preenchidos
com cerca de 20 linhas sorteadas do próprio dataset enviado**. O usuário corrige o
que estiver errado, e o orquestrador grava `guia_linhas.csv` com `_linha`
preservado. Os erros que ele quiser apontar fora dessas linhas vão para
`guia_pares.csv`. Isso também casa com a restrição da especificação (§1.2.g) de que
o guia é a "verdade estabelecida" pelo usuário. Confirme essa escolha com o usuário
antes de construir a tela (seção 9).

### 5.3 Acompanhamento da geração (1.2.d)

A espinha é uma única função, sem callbacks. Mas o `respostas.jsonl` recebe uma
linha **a cada chamada**, já gravada em disco, com o campo `etapa`. Acompanhando
esse arquivo enquanto o subprocesso roda, o painel mostra a etapa sem mudar nada
no gerador:

| `etapa` no arquivo | Rótulo da especificação |
|---|---|
| `detector` | Detecção |
| `especificador` | Geração de regras |
| `codificador` | Geração de código |
| `residual` | (rodada final; sugere-se "Geração de regras") |

As etapas determinísticas (perfil, crivo, escrita dos arquivos) não gravam linhas,
mas levam segundos.

### 5.4 Relatório de geração (1.2.f)

Tudo está no `raciocinio_<nome>.md`. Para cada coluna, ele traz cada candidata com:

- o **tipo**: `conformidade`, `formato`, `dominio`, `faixa`, `ausente_disfarcado` ou
  `dependencia`;
- os **parâmetros** e o **raciocínio** do LLM;
- as **métricas**, entre elas `motivo` (o veredito da detecção) e `motivo_reparo`;
- a **estratégia de reparo**, com o código da função quando há;
- as entradas do dicionário residual, inclusive as que caíram.

**Limitação:** esses dados só existem em Markdown. A função `gerar_limpador`
devolve apenas o caminho do limpador, e as regras reprovadas não são expostas de
forma estruturada. Para um relatório amigável há dois caminhos:

- ler o Markdown, que tem formato regular, mas é frágil;
- uma pequena adaptação para o gerador gravar também um JSON. Ela esbarra no teto
  de linhas (seção 7).

As regras **aprovadas**, porém, estão estruturadas na lista `REGRAS` do próprio
limpador (seção 6).

O glossário de motivos, que o relatório precisa traduzir para linguagem de usuário:

| `motivo` (detecção) | Significado | Contradiz o guia? |
|---|---|---|
| `aprovada` | passou em todos os testes e está no limpador | — |
| `superada` | passou, mas outra variante do mesmo tipo marcou menos | não |
| `vacua` | não marcou nenhuma célula | não |
| `marca_demais` | marcou mais que o teto da coluna (30% ou mais, conforme o guia) | não, é estatístico |
| `ambigua` | dependência em que a determinante não decide o valor | não |
| `sem_perfil` | dependência sem par minerado, ou com mais de uma coluna determinante | não |
| `lancou` | a regra quebrou ao rodar | não |
| `marca_celula_correta` | marcou como erro uma célula que o guia mostra correta | **sim** |
| `marca_valor_certificado` | marcou um valor que o guia mostra como correto | **sim** |
| `perde_par_do_guia` | não marcou um erro que o guia aponta | **sim** |

| `motivo_reparo` | Significado | Contradiz o guia? |
|---|---|---|
| `aprovada` | o reparo está no limpador | — |
| `nao_repara` | não mudou nenhuma célula | não |
| `sem_especificacao` / `especificacao_invalida` | o especificador falhou ou respondeu fora do catálogo | não |
| `codigo_rejeitado` | a função escrita pelo LLM não passou no portão | não |
| `lancou` | o reparo quebrou ao rodar | não |
| `corrompe_celula_do_guia` | escreveria numa célula do guia um valor diferente do guia | **sim** |
| `perde_par_do_guia` | não reproduz a correção que o guia mostra | **sim** |

No dicionário residual, as entradas que caem vêm com motivo:
`contradiz_o_guia` e `valor_certificado` contradizem o guia; `conflitante` não
contradiz.

### 5.5 Relatório de limpeza (1.2.f)

Este relatório o orquestrador consegue montar sozinho, executando o limpador
(seção 6). Ele não depende do gabarito, que o orquestrador nunca terá: `medir.py`
**não serve aqui**, porque mede contra o CSV limpo do benchmark.

- **Antes e depois de cada célula:** compare o DataFrame de entrada com o corrigido.
- **Regra responsável:** `fontes[coluna][linha]` diz qual regra escreveu a célula,
  como `"<tipo>/<estrategia>"` ou `"residual"`. Com a coluna, identifica a regra em
  `REGRAS`.
- **Células impactadas por regra:** conte as fontes por coluna.
- **Células marcadas e não corrigidas:** a máscara `flags` (vale mostrar).

### 5.6 Aprovação e aperfeiçoamento (1.2.g, 1.2.h)

**O gerador não tem hoje entrada para instruções do usuário** nem para "regras
já aprovadas em versões anteriores". Isso exige uma adaptação, que a
especificação prevê ("principalmente no especificador").

A restrição de que o usuário não pode contradizer o guia tem tradução direta: os
motivos marcados "sim" nas tabelas da seção 5.4 **são** as contradições ao guia.

- Uma regra reprovada por um desses motivos **não pode** ser aprovada pelo usuário.
- Uma reprovada pelos outros motivos (`marca_demais`, `superada`, `vacua` …) pode
  ser reconsiderada.
- Rejeitar uma regra aprovada nunca contradiz o guia. Basta tirá-la de `REGRAS`.

**Cuidado com a reprodutibilidade.** O teste
`tests/test_invariante.py::test_geracao_a_partir_das_respostas_reproduz_o_limpador`
regenera o limpador congelado a partir das respostas gravadas, e cada chamada é
reconhecida pelo hash do prompt. **Qualquer mudança de texto num prompt quebra esse
teste**, de propósito. A adaptação de realimentação tem de acrescentar texto ao
prompt **só quando houver instrução do usuário**, deixando o prompt sem instrução
idêntico ao de hoje.

**Memória congelada.** Ao reaplicar um limpador a dados novos (1.2.h), lembre que
duas partes dele são memória da tabela de geração: o dicionário `RESIDUAL` e o
domínio da estratégia `vizinho_no_dominio`. Elas não cobrem valores inéditos. A
medição nas linhas nunca vistas ainda não foi feita (`docs/CONTINUACAO.md` §7).

## 6. O contrato do limpador gerado

```python
import importlib.util
spec = importlib.util.spec_from_file_location("limpador", caminho)
limpador = importlib.util.module_from_spec(spec); spec.loader.exec_module(limpador)

corrigido, flags, fontes = limpador.aplicar_detalhado(df)   # df lido com config.LER_CSV
corrigido, flags = limpador.aplicar(df)
```

| Nome | O que é |
|---|---|
| `aplicar(df) -> (df, flags)` | o contrato que `medir.py` usa; também mede os limpadores da POC 1 |
| `aplicar_detalhado(df) -> (df, flags, fontes)` | `flags` é um DataFrame booleano (célula marcada e não corrigida); `fontes` é um DataFrame de strings (`""` onde nada escreveu) |
| `REGRAS` | lista de dicts `{coluna, tipo, deteccao, estrategia, reparo}`, na ordem em que se aplicam. `estrategia=None` quer dizer que a regra só marca |
| `RESIDUAL` | `{coluna: {valor_sujo: valor_limpo}}` |
| `FUNCOES` | as funções `corrigir_<n>` escritas pelo LLM |
| `GERACAO_TRUNCADA`, `UNIDADES_DEGRADADAS_POR_TETO` | se a geração bateu no teto de chamadas. Uma versão truncada não deve ser aprovada como se fosse completa |
| `main()` | `python limpador.py entrada.csv saida.csv [--flags flags.csv]` |

**Segurança:** as funções `corrigir_*` foram escritas pelo LLM. Elas passaram pelo
portão AST na geração, mas o limpador entregue roda **sem** portão (o cabeçalho
avisa). Execute-o num **subprocesso**, de preferência pela linha de comando acima.
Em tabela nova, uma célula em que a função lança vira flag, em vez de derrubar a
execução (`docs/DECISOES.md#funcao-que-lanca`).

## 7. Restrições que você herda

1. **Teto de tamanho, e uma pergunta antes de tudo.** O `CLAUDE.md` §2 limita o
   projeto a 16 arquivos `.py` e 1.800 linhas, contados por
   `git ls-files "*.py" ":!tests/"`. O gerador está em **16 de 16 e 1.798 de
   1.800**. Do jeito que a medida está escrita, qualquer `.py` do orquestrador neste
   repositório estoura o teto. **Pergunte ao usuário** se o teto vale só para o
   gerador, com um orçamento próprio para o orquestrador e a medida restrita a
   `limpeza2/`, `preparar_guia.py` e `medir.py`. Pergunte também como ele quer
   tratar as adaptações no gerador, que hoje não têm folga nenhuma.
   `e6_codificador.py` está em 200 linhas, o máximo por arquivo.
2. **O gerador continua funcionando sozinho.** A suíte (`.venv/Scripts/python -m
   pytest`, 295 testes, nenhum gasta API) tem de continuar verde.
   `tests/test_invariante.py` trava os números do limpador congelado. Mudá-los, ou
   mudar `motor.py` ou um prompt, só com decisão do usuário, entrada em
   `docs/DECISOES.md` e fixture nova (`CLAUDE.md` §8).
3. **O gabarito nunca entra na geração.** Isso já é natural para o orquestrador, que
   não tem gabarito. Mas não importe `medir` nem `preparar_guia` de dentro de
   `limpeza2/`: o teste de vazamento falha.
4. **Separação de diretórios** (especificação §4.4). Sugestão: um diretório de topo
   próprio, como `orquestrador/`, ao lado de `limpeza2/`, que continua sendo
   importável a partir da raiz (é um pacote de namespace, sem `__init__.py`).
5. **Regras de código do projeto** (`CLAUDE.md` §5): docstring de 1 linha,
   comentário de no máximo 2 linhas, `try` só com degradação nomeada, português em
   tudo e sem acento em identificadores e logs.
6. **Run pago é decisão do usuário, anunciada antes** (`CLAUDE.md` §8). Para testar
   o orquestrador sem gastar API, use `PROVEDOR=gravado` com
   `RESPOSTAS_GRAVADAS=tests/fixtures/respostas_beers_poc2.jsonl`, o sujo
   `tests/fixtures/beers_dirty_300.csv` e o guia `dados/guia/beers/`. Isso reproduz
   o limpador do MVP inteiro, offline. O destino precisa ter o nome
   `beers_2026-10-12_2152` para os bytes baterem.

## 8. Limites conhecidos do gerador, para o relatório não prometer demais

- **Valor deslocado entre colunas não é corrigido.** No `beers`, a sigla do estado
  foi parar dentro da cidade (`'San Francisco CA'` com `state` vazio). Nenhuma
  estratégia move um valor de uma coluna para outra (`docs/CONTINUACAO.md` §7).
- **`Project_Name` (environment) fica com zero de recall**, porque a conformidade
  dela é reprovada pelo guia.
- **Sem guia, a moda condicionada pode estragar uma coluna limpa.** No
  `environment` sem guia, ela alterou 47 células corretas de `City`.
- **`medir.py` esconde falsos positivos em colunas sem erro**, porque a fórmula é a
  da POC 1. O relatório de limpeza do orquestrador conta todas as alterações, então
  ele não herda esse problema.
- **Só testado em tabelas de 300 linhas e 11 colunas**, em inglês.

## 9. Perguntas para fazer ao usuário antes de construir

1. **Teto de tamanho:** como ele vale com o orquestrador no mesmo repositório?
   Pode-se adaptar o gerador sem folga de linhas? (seção 7.1)
2. **Amostra-guia:** pode ser pré-preenchida com cerca de 20 linhas sorteadas do
   dataset para o usuário corrigir, em vez de 5 linhas digitadas? Os números da
   seção 5.2 mostram o custo de 5 linhas.
3. **Relatório de geração:** ler o Markdown do raciocínio, ou adaptar o gerador para
   gravar também um JSON?
4. **Aperfeiçoamento:** a tradução da restrição "não contradizer o guia" pelos
   motivos da seção 5.4 é a que ele quer? E "regras já aprovadas" entram na nova
   geração como instrução ao especificador, ou como regras fixas somadas ao
   limpador novo?
5. **Infraestrutura:** confirmar o SeaweedFS já instalado (a especificação pede para
   verificar antes de instalar) e onde o SQLite deve morar.

# Orquestrador do framework de limpeza: design

Decidido no brainstorming de 17/10/2026, sobre
`docs/especificacoes_do_humano/especificacao_orquestrador_limpeza_dados.md` (aqui
chamada **especificação**) e `docs/HANDOFF_ORQUESTRADOR.md` (o **handoff**). O
gerador de limpadores é o pacote `limpeza2/`; o orquestrador é o invólucro que o usa
como componente central, com interface, fluxo, armazenamento, versionamento,
relatórios e o ciclo de aprovação.

---

## 1. Decisões do brainstorming

| # | Pergunta | Decisão |
|---|---|---|
| 1 | Teto de tamanho | O teto do `CLAUDE.md` §2 passa a valer **só para o gerador** (`limpeza2/`, `preparar_guia.py`, `medir.py`), elevado para **1.850 linhas** para caber as adaptações. O orquestrador tem **orçamento próprio**: 14 arquivos `.py`, 1.400 linhas, maior arquivo com 200. **Não corromper o gerador vale mais que o teto**: as adaptações são só inserções, sem refatorar código que funciona para caber; um estouro pequeno é aceito e declarado (seção 8.3). |
| 2 | Origem da amostra-guia | Linhas **sorteadas do próprio dataset** com semente gravada, as mesmas no template e no formulário; **20 por padrão, mínimo 10**; `_linha` travada; pares avulsos opcionais; botão **"sortear de novo" por linha**, com cada troca registrada e declarada nos relatórios. |
| 3 | Relatório de geração | O orquestrador **lê o `raciocinio_<nome>.md`**; o gerador não grava JSON. Um teste de contrato sobre o raciocínio congelado do MVP trava o formato. |
| 4a | Decisões do usuário | Um `decisoes.json` **na pasta do guia**. `rejeitar` vira motivo do crivo; `aprovar` dispensa os testes estatísticos, nunca os testes contra o guia; instrução livre vai ao prompt do especificador. O ciclo **reaproveita as respostas gravadas** da versão anterior e só chama a API para prompts novos. |
| 4b | Nova versão de esquema conhecido | A entrada da geração é **as linhas sujas antigas citadas pelo guia, mais o sujo novo, renumeradas**. As regras aprovadas antes entram pelo **mesmo `decisoes.json`, acumulado**, como candidatas herdadas que passam pelo crivo de novo. O `RESIDUAL` antigo não é herdado. |
| 5 | Infraestrutura | **SeaweedFS já instalado** (`C:\Users\gusta\tools\seaweedfs\weed.exe`, 4.21-enterprise), confirmado pela sonda da seção 11. SQLite em `var/controle.sqlite`, caminho configurável. |
| 6 | Tecnologia (§4.1 da especificação) | **Streamlit + subprocesso + SQLite como controlador.** Sem fila, sem agendador. Recusados: FastAPI + HTMX (mais código para o mesmo resultado) e Prefect/Airflow (servidor a mais e segunda fonte de verdade sobre o estado). |
| 7 | Tamanho da tabela na geração | **Parametrizável na interface**: amostra (padrão 300 linhas, mínimo 100) ou tabela inteira, com aviso quando sair do regime testado. O limpador é sempre aplicado à tabela inteira. |

## 2. Estrutura e módulos

```
limpeza2/              o gerador (adaptações na seção 8)
preparar_guia.py, medir.py
orquestrador/
  app.py               ponto de entrada do Streamlit: escolhe a tela pelo estado do processo
  tela_ingestao.py     upload, dominio e nome do esquema novo
  tela_guia.py         formulario e template da amostra-guia, com "sortear de novo"
  tela_painel.py       acompanha a geracao: etapa, indicador e cronometro
  tela_resultado.py    mostra os relatorios e recolhe aprovar ou aperfeicoar
  fluxo.py             a ordem das etapas do processo e as transicoes entre elas
  controle.py          le e grava os metadados no SQLite
  lago.py              le e grava artefatos no bucket, no layout da especificacao
  amostra.py           sorteia, valida e renumera a amostra-guia e a amostra de geracao
  geracao.py           roda o gerador em subprocesso e informa a etapa corrente
  relatorio_geracao.py le o raciocinio do gerador e o traduz em linguagem de usuario
  relatorio_limpeza.py executa o limpador em subprocesso e resume o que ele mudou
  decisoes.py          monta o decisoes.json e recusa o que contradiz o guia
  config.py            endpoint, bucket, caminho do SQLite, tamanhos padrao
subir_seaweed.sh       sobe o SeaweedFS com os argumentos certos (nao e Python)
var/                   SQLite e pastas de trabalho; ignorada pelo git
```

As regras de código do `CLAUDE.md` §5 valem para o orquestrador: docstring de uma
linha, comentário de no máximo duas, `try` só com degradação nomeada, português em
tudo, sem acento em identificadores e logs. Cada arquivo cabe numa frase; nunca
fracionar para caber no teto.

`orquestrador/` é um pacote de namespace, como `limpeza2/`. O app sobe da raiz:
`.venv/Scripts/streamlit run orquestrador/app.py`.

### 2.1 A fronteira com o gerador

O orquestrador fala com o gerador pelos três pontos de contato do handoff §2, e por
nenhum outro:

| Ponto | Como o orquestrador o usa |
|---|---|
| Gerar | subprocesso filho que importa **só** `limpeza2.espinha.gerar_limpador` e o chama com o `destino` escolhido pelo orquestrador |
| Arquivos de saída | lê `limpador_*.py`, `raciocinio_*.md` e `respostas.jsonl` da pasta `destino` |
| Aplicar | subprocesso filho (`relatorio_limpeza.py` executado como script) que importa o limpador gerado, chama `aplicar_detalhado` e grava `corrigido`, `flags` e `fontes` em CSV |

O processo do Streamlit nunca importa `limpeza2` nem o limpador gerado. Isso isola o
global `provedor._atual` (uma geração por processo), não trava a interface e executa
as funções `corrigir_*` escritas por LLM, que rodam sem o portão, fora do processo
da interface. O orquestrador também não importa `medir` nem `preparar_guia`: os dois
leem o CSV limpo do benchmark, que numa base real não existe.

A configuração do gerador vai pelo ambiente do subprocesso (`PROVEDOR`,
`RESPOSTAS_GRAVADAS`, `PROVEDOR_VIVO`). O `load_dotenv` do gerador não sobrescreve
variável já definida, então o ambiente do filho prevalece sobre o `.env`.

## 3. O data lake

Um bucket, `limpeza`, no S3 do SeaweedFS em `http://127.0.0.1:8333`, acessado por
`boto3`. O SeaweedFS sem configuração de IAM aceita acesso anônimo; o `boto3` recebe
credenciais fictícias. O servidor escuta só em `127.0.0.1`.

```
<Dominio>/<Esquema>/
  Original/<Extraido_em>/      dados.csv
  Amostra_Guia/<Importada_em>/ guia_linhas.csv, guia_pares.csv, linhas_sujas.csv, sorteio.json
  Limpador/<Gerado_em>/        limpador_<versao>.py, raciocinio_<versao>.md, respostas.jsonl,
                               decisoes.json, parametros.json, relatorio_geracao.md, erro.log
  Corrigido/<Gerado_em>/       dados.csv, flags.csv, relatorio_limpeza.md
```

- `<Dominio>` e `<Esquema>` são o domínio e o nome dados pelo usuário, reduzidos a
  ASCII com `_` no lugar de espaço (`Meio Ambiente` → `Meio_Ambiente`). Os carimbos
  são `AAAA-MM-DD_HHMMSS`.
- `<versao>` é `<Esquema>_<Gerado_em>`: é o `destino.name` passado ao gerador, que
  entra no nome dos arquivos e no cabeçalho do limpador.
- `dados.csv` em `Original` leva o sha256 dos bytes na metadado do objeto e no
  SQLite.
- `linhas_sujas.csv` guarda as linhas **sujas** que o guia e os pares citam, com o
  índice original. É o que permite montar a entrada de uma nova versão quando chega
  um dataset novo do mesmo esquema (seção 6.4). Não está na especificação; é
  necessário.
- `sorteio.json` guarda a semente, os índices sorteados e cada troca de "sortear de
  novo" (`{"posicao", "saiu", "entrou"}`).
- `parametros.json` guarda a base da geração (amostra ou tabela inteira), o tamanho,
  a semente e o mapa de índices da entrada da geração para a tabela original.
- `erro.log` só existe quando a geração falhou.

**Pasta de trabalho local.** O gerador escreve em disco local; o orquestrador monta a
entrada e recebe a saída em `var/trabalho/<ID_PROCESSO>/<versao>/` e depois envia os
arquivos ao bucket. O bucket é a fonte de verdade dos artefatos **publicados**; a
pasta de trabalho é o estado vivo dos processos abertos (o original, o
`respostas.jsonl` que o aperfeiçoamento reaproveita, os relatórios da tela) e **não
pode ser apagada enquanto houver processo aberto**. Corrigido em 18/10/2026, achado da
revisão de código.

## 4. O banco de controle (SQLite)

As cinco tabelas da especificação §3, com os campos dela. Datas em ISO 8601, texto.

| Tabela | Campos | Escolhas |
|---|---|---|
| `ESQUEMAS` | `ID_ESQUEMA`, `DOMINIO`, `NOME_ESQUEMA`, `CAMPOS_ESQUEMA`, `DIRETORIO_BUCKET`, `DATA_CRIACAO` | `CAMPOS_ESQUEMA` é a lista JSON **ordenada** dos nomes das colunas |
| `LIMPADORES` | `ID_LIMPADOR`, `DOMINIO`, `NOME_ESQUEMA`, `DATA_CRIACAO`, `STATUS_APROVACAO` | `STATUS_APROVACAO` ∈ {`pendente`, `aprovado`, `reprovado`}; acrescenta `DIRETORIO_BUCKET` e `ID_LIMPADOR_ORIGEM` (a versão de que esta reaproveitou respostas e decisões) |
| `ETAPAS` | `ID_ETAPA`, `NOME_ETAPA`, `DESCRICAO_ETAPA` | povoada uma vez com as dez etapas da seção 5 |
| `PROCESSOS` | `ID_PROCESSO`, `ID_ESQUEMA`, `NOME_ESQUEMA`, `HASH_DADO`, `ID_ETAPA`, `DATA_INICIO_ETAPA`, `STATUS`, `DATA_HORA_INICIO_PROCESSO`, `DATA_HORA_CONCLUSAO`, `TEMPO_PROCESSAMENTO` | **uma linha por etapa executada**; `ID_PROCESSO` agrupa. `STATUS` ∈ {`em andamento`, `concluido com sucesso`, `concluido com erro`}. `TEMPO_PROCESSAMENTO` em segundos. Acrescenta `PID` (do subprocesso, quando há) e `DETALHE` (motivo do erro ou da espera) |
| `DADOS` | `ID_CONTROLE_DADO`, `HASH`, `DOMINIO`, `NOME_ESQUEMA`, `DIRETORIO_ORIGINAL`, `DIRETORIO_CORRIGIDO`, `LIMPADOR_UTILIZADO`, `DATA_HORA_INGESTAO` | `DIRETORIO_CORRIGIDO` e `LIMPADOR_UTILIZADO` ficam vazios até a aprovação |

O estado do fluxo **mora só no SQLite**. O Streamlit reexecuta o script a cada
interação; a tela é escolhida pela última linha de `PROCESSOS` do processo aberto.
F5, fechar e reabrir o navegador ou reiniciar o app voltam à tela certa.

## 5. O fluxo

`fluxo.py` guarda a ordem das etapas e as transições, e é o único lugar que as
guarda. As telas chamam funções de `fluxo.py`; nenhuma tela decide a próxima etapa.

| ID | Etapa | Quem age |
|---|---|---|
| 1 | Identificação do esquema | sistema |
| 2 | Armazenamento do original | sistema |
| 3 | Amostra-guia | usuário |
| 4 | Detecção | gerador |
| 5 | Geração de regras | gerador |
| 6 | Geração de código | gerador |
| 7 | Versionamento do limpador | sistema |
| 8 | Aplicação e relatórios | sistema |
| 9 | Decisão do usuário | usuário |
| 10 | Armazenamento do corrigido | sistema |

**Esquema novo.** 1 → (o usuário dá o nome) → 2 → 3 → 4, 5, 6 → 7 → 8 → 9.
Na 9, *aprovar* leva à 10 e encerra; *aperfeiçoar* grava o `decisoes.json` e volta à
4, reaproveitando as respostas da versão anterior.

**Esquema conhecido.** 1 → 2 → 8, com o limpador **aprovado** mais recente do esquema
→ 9. Na 9, *aprovar* leva à 10; *gerar nova versão* monta a entrada da seção 6.4,
herda as decisões da versão aprovada e volta à 4.

**Esquema conhecido** quer dizer: mesmo domínio e mesmo **conjunto** de nomes de
colunas, em qualquer ordem. Tabela com coluna a mais ou a menos é esquema novo. Se o
esquema é conhecido mas não tem limpador aprovado, o fluxo pula a etapa 3,
reaproveita a amostra-guia gravada, monta a entrada da seção 6.4 e segue da 4, sem
decisões herdadas.

**Aprovar** marca o limpador como `aprovado`, grava o corrigido, preenche
`DIRETORIO_CORRIGIDO` e `LIMPADOR_UTILIZADO` em `DADOS` e fecha o processo.
**Aperfeiçoar** marca a versão corrente como `reprovado`.

**Uma geração de cada vez.** Enquanto uma etapa 4–6 está `em andamento`, o app não
abre outro processo; mostra o painel do que está rodando.

## 6. A amostra-guia e a entrada da geração (`amostra.py`)

### 6.1 Sorteio

Na etapa 3, o orquestrador sorteia `N` linhas do sujo com `random_state` igual à
semente (`config.SEMENTE_GUIA`, gravada no `sorteio.json`). `N` vem do topo da tela,
padrão 20, mínimo 10 (handoff §5.2). Sem linha repetida.

**"Sortear de novo"** troca uma linha por outra ainda não sorteada, tirada da mesma
sequência pseudoaleatória, e grava a troca. O relatório de geração declara quantas
trocas houve: o sorteio deixa de ser puramente aleatório quando o usuário troca as
linhas que não sabe corrigir, e isso tem de ser dito.

### 6.2 Formulário e template

Os dois caminhos mostram **as mesmas linhas**:

- **Formulário:** `st.data_editor` com as colunas do dataset e as linhas sorteadas,
  pré-preenchidas com os valores sujos. `_linha` aparece e não é editável. O usuário
  corrige o que estiver errado.
- **Template:** `st.download_button` entrega `guia_template.csv` com `_linha` e as
  colunas, pré-preenchido; `st.file_uploader` recebe o arquivo corrigido. O upload é
  **recusado** se as colunas ou o conjunto de `_linha` divergirem do sorteio, com a
  lista do que diverge.
- **Pares avulsos (opcional):** uma segunda grade com `linha, coluna, sujo, limpo`,
  para erros fora das linhas sorteadas. `linha` tem de existir no sujo, `coluna` tem
  de ser do esquema e `sujo` tem de ser o valor daquela célula; o orquestrador
  preenche `sujo` sozinho a partir de `linha` e `coluna`.

Ao confirmar, o orquestrador grava no bucket `guia_linhas.csv` e `guia_pares.csv` no
formato do handoff §4, `linhas_sujas.csv` e `sorteio.json`.

### 6.3 A entrada da geração (parâmetros)

Logo antes de "Iniciar geração", um quadro **Parâmetros da geração**:

- **Base:** `Amostra` (padrão) ou `Tabela inteira`.
- **Tamanho da amostra:** padrão 300, mínimo 100 e nunca menos que as linhas do guia e
  dos pares; máximo, o total de linhas, mostrado ao lado.
- **Aviso fixo**, não bloqueante, quando a base passa de 300 linhas: "fora do regime
  testado (até 300 linhas e 11 colunas); tempo e custo de API podem crescer".
- **Provedor e modelo** em uso; com `openai`, o aviso "as linhas da tabela vão para a
  API da OpenAI"; e o teto de chamadas: "cerca de 30 chamadas numa geração nova, no
  máximo 80; no aperfeiçoamento, as chamadas com resposta gravada não são cobradas".
  A contagem real de chamadas novas sai no relatório de geração.

A amostra **sempre contém** as linhas citadas pelo guia e pelos pares; o resto é
sorteado com semente. As linhas entram **na ordem original** e são renumeradas de 0 em
diante, e `_linha` e `linha` do guia são reescritos para os índices novos. O mapa
`índice novo → índice original` fica no `parametros.json`. Com a base igual à tabela
inteira, o mapa é a identidade e o sujo da geração é o sujo original, byte a byte.

### 6.4 A entrada de uma nova versão de esquema conhecido

O guia tem `_linha` apontando para o sujo **da primeira ingestão**. Dar ao gerador só o
sujo novo faria a comparação por célula do crivo comparar linhas erradas, em silêncio.
Então a entrada é:

1. as linhas de `linhas_sujas.csv` (as linhas sujas antigas citadas pelo guia e pelos
   pares), seguidas de
2. o sujo novo, inteiro ou amostrado conforme a seção 6.3,

renumeradas de 0 em diante, com `_linha` e `linha` do guia reescritos para as
posições das linhas antigas. A comparação por célula continua válida, e o schema
derivado do guia vale para a tabela nova.

## 7. A geração (`geracao.py`) e o painel

`geracao.py` dispara o filho com o Python do `.venv`, `cwd` na raiz do repositório e
argumentos em lista (o PowerShell quebra `-ip=127.0.0.1`; `subprocess` com lista não
passa por shell). O filho chama `gerar_limpador(sujo, pasta_guia, destino)`. O `PID`
vai para `PROCESSOS`.

**A etapa corrente** sai do `respostas.jsonl`, que o gerador grava a cada chamada: é o
campo `etapa` da última linha.

| `etapa` | Etapa no painel |
|---|---|
| (subprocesso subiu, nenhuma linha ainda) | 4 Detecção |
| `detector` | 4 Detecção |
| `especificador`, `residual` | 5 Geração de regras |
| `codificador` | 6 Geração de código |

A etapa 6 termina quando o filho sai com código 0. Nas fases determinísticas, que
levam segundos, o painel mantém a última etapa conhecida. Cada mudança de etapa grava
uma linha nova em `PROCESSOS`.

**O painel** (`tela_painel.py`) usa `st.fragment(run_every=1)`: lê a etapa, mostra
`st.status` como indicador de carregamento e um cronômetro desde
`DATA_HORA_INICIO_PROCESSO`, além da contagem de chamadas feitas.

**Aperfeiçoamento.** O filho roda com `PROVEDOR=reaproveitar`,
`RESPOSTAS_GRAVADAS=<respostas.jsonl da versão anterior>` e `PROVEDOR_VIVO` igual ao
`PROVEDOR` do `.env`. A pasta do guia passada ao gerador leva o `decisoes.json` da
seção 9. As chamadas novas são as chaves do `respostas.jsonl` novo que não estão no
anterior.

## 8. As mudanças no gerador

### 8.1 O princípio

**Sem `decisoes.json` na pasta do guia, o gerador é byte a byte o de hoje.** Os
prompts não mudam, o teste de invariante continua verde, a linha de comando é a
mesma. A assinatura de `gerar_limpador` e `espinha.py` **não mudam**: as decisões
viajam dentro da `Entrada`, que todas as etapas já recebem. As mudanças são **só
inserções**; nenhuma linha existente é reescrita, salvo quando a inserção o exige.

### 8.2 As mudanças

| Arquivo | Mudança | Linhas (est.) |
|---|---|---|
| `tipos.py` | `Entrada` ganha `decisoes: list` (vazia por padrão) | +1 |
| `e1_perfil.py` | `_ler_guia` lê `decisoes.json` se existir | +5 |
| `e2_detector.py` | no fim de `propor`, cada decisão `aprovar` cuja chave não foi proposta de novo entra como `Candidata` **herdada**, com raciocínio "aprovada pelo usuario na versao X" e `metricas["decisao"]` | +7 |
| `e3_crivo.py` | `rejeitar` → motivo `rejeitada_pelo_usuario`. `aprovar` → dispensa `marca_demais` e `ambigua` e vence a disputa de `superada`; os testes contra o guia continuam. No residual, `rejeitar` uma entrada a põe em `caidas` com `rejeitada_pelo_usuario` | +12 |
| `e4_especificador.py` | `_conteudo` acrescenta `instrucao do usuario: <texto>` só quando há instrução para a regra; `INSTRUCAO` não muda | +3 |
| `provedor.py` | `PROVEDOR=reaproveitar`: responde do `RESPOSTAS_GRAVADAS` e, quando falta a resposta, chama `PROVEDOR_VIVO`. `PROVEDOR_VIVO` desconhecido falha alto. Se `MODELO` diferir do modelo da origem gravada, falha alto: misturar respostas de dois modelos numa versão a tornaria inexplicável | +16 |
| `config.py` | `PROVEDOR_VIVO` | +2 |

Total estimado: cerca de +46, de 1.798 para cerca de 1.844 linhas.

**O que não muda:** `motor.py`, `portao.py`, `e6_codificador.py`, `espinha.py`,
`conformidade.py`, `limites.py` e todo prompt sem instrução do usuário. O
`raciocinio_<nome>.md` não muda de formato: o `e6_codificador.py` já imprime todas as
`metricas` de cada candidata, então o motivo novo e a marca `decisao` aparecem sem
tocar nele.

### 8.3 O teto

`e3_crivo.py` está em 196 linhas e deve ir a cerca de 208. **Não se refatora o crivo
para caber**: juntar a conta `sujo != guia`, que está escrita três vezes
(`docs/CONTINUACAO.md` §6), mexe em lógica que funciona por um ganho cosmético. Se o
arquivo passar de 200 ou o total passar de 1.850, o estouro é **aceito e declarado**
no `CLAUDE.md` §2 e no `docs/DECISOES.md`, com o motivo, como decidido pelo usuário em
17/10/2026.

### 8.4 A rede de proteção

Depois de **cada** mudança no gerador:

1. a suíte inteira (`.venv/Scripts/python -m pytest`);
2. `tests/test_invariante.py`, que regenera o limpador do MVP byte a byte a partir das
   respostas gravadas;
3. o teste novo: com `decisoes.json` igual a `[]`, o limpador e o raciocínio gerados
   são **idênticos** aos gerados sem o arquivo.

Se qualquer um quebrar, a mudança é revertida. Cada mudança traz teste próprio com
prova por mutação e entrada em `docs/DECISOES.md`.

### 8.5 Documentos do gerador

- `CLAUDE.md` §2: a medida passa a ser
  `git ls-files "limpeza2/*.py" preparar_guia.py medir.py`, com teto de 1.850 linhas;
  o orçamento do orquestrador é declarado ao lado.
- `CLAUDE.md` §9: o `decisoes.json` na pasta do guia e o modo `reaproveitar`.
- `CLAUDE.md` §10: o orquestrador e a fronteira da seção 2.1.

## 9. As decisões do usuário (`decisoes.py`)

### 9.1 O formato

`decisoes.json` é uma lista. Cada entrada:

```json
{"coluna": "ibu", "tipo": "faixa", "parametros": {"minimo": 0, "maximo": 150},
 "decisao": "aprovar", "instrucao": null, "origem": "usuario", "versao": "beers_2026-10-17_101500"}
```

- **A chave de uma regra** é `(coluna, tipo, parametros)`, comparados por igualdade.
  É o que liga uma decisão a uma regra entre versões.
- `decisao` ∈ {`aprovar`, `rejeitar`}. `instrucao` é texto livre ou `null`.
- `origem` ∈ {`usuario`, `herdada`}: `herdada` é uma regra aprovada numa versão
  anterior que passou adiante sem nova escolha do usuário.
- `versao` é a versão do limpador em que a decisão foi tomada.
- **Entrada do residual:** `{"coluna": "city", "tipo": "residual", "parametros":
  {"sujo": "San Fransisco"}, "decisao": "rejeitar"}`. Só `rejeitar` existe para o
  residual.

### 9.2 O que pode ser decidido

| Situação da regra | O usuário pode |
|---|---|
| aprovada | rejeitar, com ou sem instrução |
| reprovada por `marca_demais`, `superada`, `ambigua` | aprovar, com ou sem instrução |
| reparo reprovado por `sem_especificacao`, `especificacao_invalida`, `codigo_rejeitado`, `lancou` | pedir nova tentativa ao especificador, com instrução obrigatória |
| reprovada por `vacua`, `lancou` (detecção), `sem_perfil`, `nao_repara` | nada: aprovar uma regra que não marca, não repara ou quebra não tem efeito |
| reprovada por `marca_celula_correta`, `marca_valor_certificado`, `perde_par_do_guia`, `corrompe_celula_do_guia` | **nada: contradiz o guia** |
| entrada do residual que ficou | rejeitar |
| entrada do residual que caiu por `contradiz_o_guia` ou `valor_certificado` | **nada: contradiz o guia** |

**Duas camadas.** A interface não oferece o botão onde a tabela diz "nada", e
`decisoes.py` recusa a entrada se ela chegar assim mesmo. O crivo do gerador ainda
roda os testes contra o guia sobre toda regra aprovada pelo usuário: é a terceira
proteção, e a única que vale também para quem usar o gerador sem o orquestrador.

### 9.3 Acúmulo entre versões

O `decisoes.json` de uma versão nova é o da versão de origem, mais:

- uma entrada `aprovar` com `origem: herdada` para cada regra em `REGRAS` da versão
  de origem que ainda não tem decisão, quando a origem está `aprovado` (esquema
  conhecido);
- as escolhas novas do usuário, que substituem a decisão anterior da mesma chave.

`REGRAS` dá a chave das regras aprovadas; as reprovadas vêm do relatório de geração
(seção 10.1).

## 10. Os relatórios

### 10.1 Relatório de geração (`relatorio_geracao.py`)

Lê o `raciocinio_<versao>.md`: `## coluna`, `### tipo: motivo` e linhas
`- chave: valor`, com `parametros` lido por `ast.literal_eval`, que não executa
código. Produz:

- **Cabeçalho:** modelo e provedor; chamadas totais e novas; supervisão (linhas do
  guia, pares, trocas de "sortear de novo"); base da geração (amostra de N linhas ou
  tabela inteira, semente); aviso destacado se `GERACAO_TRUNCADA`.
- **Por coluna, as aprovadas:** o tipo em linguagem de usuário (`conformidade`: "os
  valores têm de seguir o formato que o guia mostra: `9`"; `dependencia`: "`state` é
  determinado por `city`"; etc.), a estratégia de reparo e o raciocínio do LLM.
- **Por coluna, as reprovadas:** a justificativa traduzida pelo glossário do handoff
  §5.4 ("marcou como erro uma célula que você confirmou como correta no guia"). As que
  contradizem o guia ficam destacadas e sem botão de aprovar.
- **Marcas** em cada regra herdada, aprovada ou rejeitada pelo usuário.
- **O dicionário residual**, com as entradas que caíram e o motivo.
- **Os limites conhecidos** do handoff §8 que se aplicam: memória congelada no
  residual e em `vizinho_no_dominio`, valor deslocado entre colunas.

Gravado como `relatorio_geracao.md` em `Limpador/<Gerado_em>/` e mostrado na tela.

### 10.2 Relatório de limpeza (`relatorio_limpeza.py`)

O módulo é executado como script filho: importa o limpador gerado, lê o CSV com o
`LER_CSV` do handoff §4, chama `aplicar_detalhado` sobre a **tabela inteira** e grava
`corrigido`, `flags` e `fontes` em CSV. O processo pai lê os três e produz:

- **Cada regra de `REGRAS`**, numerada (R1, R2, …) e identificada por coluna, tipo e
  estratégia. Uma regra é encontrada em `fontes` pelo par `(coluna, "<tipo>/<estrategia>")`.
- **Células alteradas por regra**, mais a linha `residual`.
- **Amostra de até 5 células por regra**, antes → depois, com a linha.
- **Células marcadas e não corrigidas**, por coluna (`flags`).
- **Totais:** células alteradas e linhas tocadas.

Gravado como `relatorio_limpeza.md`, com `dados.csv` e `flags.csv`, em
`Corrigido/<Gerado_em>/`.

## 11. A infraestrutura

**Sonda de 17/10/2026, sem API**, com o `weed.exe` instalado e uma pasta de dados nova
em `C:\Users\gusta\tools\seaweedfs\sonda_orquestrador\`:

- A licença do build enterprise é padrão e renovada a cada partida (`Expires:
  2027-01-17` na partida de 17/10); não bloqueia.
- O `panic` do raft de 29/04 (`sync data/m9333: Access is denied`) não se repetiu com
  pasta nova.
- `curl` anônimo e `boto3` criaram bucket, gravaram, leram e listaram por prefixo; a
  metadado `sha256` foi e voltou.
- Com `-volume.max=5`, o segundo bucket travou em `assign volume ... DeadlineExceeded`:
  cada bucket pede volumes próprios. Daí **um bucket só** e `-volume.max` no padrão.
- O PowerShell quebra `-ip=127.0.0.1`; por isso o script de partida é Bash e o
  orquestrador nunca passa argumentos por shell.

`subir_seaweed.sh` roda
`weed.exe server -dir=<SEAWEED_DADOS> -ip=127.0.0.1 -s3 -s3.port=8333`, com
`SEAWEED_DADOS` padrão `C:\Users\gusta\tools\seaweedfs\dados_orquestrador`. O bucket é
criado por `lago.py` no primeiro uso.

**Configuração** (`orquestrador/config.py`, lida do `.env`): `S3_ENDPOINT`,
`S3_BUCKET`, `SQLITE` (padrão `var/controle.sqlite`), `TRABALHO` (padrão
`var/trabalho`), `LINHAS_GUIA_PADRAO = 20`, `LINHAS_GUIA_MINIMO = 10`,
`AMOSTRA_PADRAO = 300`, `AMOSTRA_MINIMO = 100`, `SEMENTE_GUIA`,
`TIMEOUT_GERACAO = 1800`, `TIMEOUT_APLICACAO`, a lista de domínios da especificação
§1.1. `var/` entra no `.gitignore`.

**Dependências novas:** `streamlit` e `boto3` em `requirements.txt`; `moto` só para
testes.

## 12. Erros e salvaguardas

| Falha | Comportamento |
|---|---|
| Filho do gerador sai com erro | etapa `concluido com erro`; o fim do stderr vai a `erro.log` no bucket e ao painel; botão "tentar de novo" |
| Geração passa de `TIMEOUT_GERACAO` | o filho é encerrado; etapa com erro, motivo "timeout" |
| App reabre com etapa `em andamento` cujo `PID` não existe | etapa vira `concluido com erro`, motivo "interrompido"; "tentar de novo" |
| SeaweedFS fora do ar | verificado na abertura; aviso "bucket indisponível: rode `subir_seaweed.sh`"; ingestão bloqueada; **sem gravação local de reserva** |
| Dataset vazio, com coluna repetida ou com coluna começando por `_` | recusado no upload, com o motivo |
| Extração com sha256 já ingerido no mesmo esquema | aviso com a data da ingestão anterior; o processo pode seguir, sem gravar o original de novo |
| Template do guia com colunas ou `_linha` divergentes | recusado, com a lista do que diverge |
| Decisão que contradiz o guia | não oferecida; recusada por `decisoes.py`; reprovada pelo crivo |
| `GERACAO_TRUNCADA` | aviso na tela de resultado; **aprovar bloqueado**; o caminho é aperfeiçoar |
| Limpador lança ao ser aplicado | etapa 8 com erro; o caminho oferecido é gerar nova versão |
| `PROVEDOR_VIVO` desconhecido ou modelo diferente do gravado | o gerador falha alto; a etapa fica com erro e a mensagem vai ao painel |

## 13. Testes

Nenhum gasta API; nenhum precisa do SeaweedFS no ar. Todo teste novo vem com prova
por mutação (`CLAUDE.md` §8).

| Teste | O que assevera |
|---|---|
| Ponta a ponta offline | o fluxo inteiro, sem interface, sobre o MVP: `PROVEDOR=gravado`, `tests/fixtures/respostas_beers_poc2.jsonl`, `tests/fixtures/beers_dirty_300.csv`, o guia `dados/guia/beers/`, versão `beers_2026-10-12_2152`, base igual à tabela inteira. O guia entra pronto, no lugar do formulário, e o nome da versão é injetado pelo teste (o carimbo de `fluxo.py` vem de um relógio que o teste substitui). O limpador versionado no bucket é byte a byte o de `tests/fixtures/limpador_beers_poc2.py`, e as contagens do relatório de limpeza batem com as do teste de invariante |
| Ciclo de aperfeiçoamento offline | rejeita uma regra aprovada do MVP e gera com `reaproveitar` e um `PROVEDOR_VIVO` dublê que **falha o teste se for chamado**: zero chamadas novas, regra fora de `REGRAS` |
| Gerador: decisões vazias | `decisoes.json = []` dá limpador e raciocínio idênticos aos de sem arquivo |
| Gerador: cada mudança da seção 8.2 | rejeitar, aprovar (com teste contra o guia ainda reprovando), herdada, instrução no prompt só quando existe, `reaproveitar` com e sem resposta gravada, `PROVEDOR_VIVO` desconhecido e modelo divergente falhando alto |
| Bucket | com `moto`: o layout da seção 3 e o sha256 na metadado |
| Contrato do Markdown | o leitor sobre `docs/evidencia/parte-2/run-beers_2026-10-12_2152/raciocinio_beers_2026-10-12_2152.md`, conferindo a contagem de candidatas por motivo |
| Fronteira | varredura da AST de `orquestrador/`: nenhum import de `limpeza2` além de `limpeza2.espinha.gerar_limpador` no filho de geração; nenhum de `medir` nem `preparar_guia` |
| Amostra-guia | sorteio determinístico pela semente; "sortear de novo" registrado; template divergente recusado; amostra sempre contém as linhas do guia; renumeração da seção 6.4 aponta para as linhas certas |
| Decisões | aprovar motivo que contradiz o guia é recusado; acúmulo entre versões |
| SQLite | transições do fluxo; F5 volta à etapa; `PID` morto vira "interrompido" |
| Interface | fumaça das quatro telas com `streamlit.testing.v1.AppTest` |

## 14. Fora do escopo

- Vários usuários, autenticação e gerações simultâneas.
- Medir a qualidade do limpador contra gabarito: o orquestrador não tem gabarito;
  `medir.py` continua sendo a validação da POC, fora do orquestrador.
- Herdar o dicionário `RESIDUAL` entre versões.
- Mover valor de uma coluna para outra (limite do gerador, handoff §8).
- Rodar o caminho `ollama` de verdade: ele continua não testado.
- Tabelas com mais de 300 linhas ou 11 colunas como regime **validado**: a interface
  permite, avisa e não promete.

## 15. Riscos

- **O formato do Markdown do raciocínio é contrato implícito.** O teste de contrato o
  trava; mudar o `e6_codificador.py` sem atualizar o leitor quebra o teste, de
  propósito.
- **A chave por igualdade de parâmetros** não reconhece uma regra cujo LLM devolveu
  parâmetros ligeiramente diferentes numa versão nova. Por isso a regra aprovada
  entra como herdada com os parâmetros **gravados**, e não depende de o detector
  propô-la de novo.
- **O Streamlit reexecuta o script a cada interação.** Todo efeito colateral (gravar
  no bucket, disparar o filho) fica atrás de um botão e de uma transição de
  `fluxo.py`, nunca no corpo da tela.
- **Run pago.** Toda geração real é anunciada na tela (seção 6.3). Durante o
  desenvolvimento, nenhum run real é disparado sem anúncio ao usuário e aprovação
  (`CLAUDE.md` §8).

## 16. O que a implementação mudou neste desenho (18/10/2026)

Quando o código divergiu da spec, valeu o código, e o motivo está aqui.

- **15 arquivos, não 14.** `fluxo.py` saiu com 294 linhas e foi separado pela função:
  `automaticas.py` executa as etapas que o sistema faz sozinho (2, 3 do esquema
  conhecido, 7 e 8, e o registro de erro) e `fluxo.py` guarda as transições que o
  usuário dispara. O orquestrador fechou em 1.530 linhas (orçamento: 1.400). Declarado
  no `CLAUDE.md` §2.
- **Uma sexta tabela, `CONTEXTOS`** (`ID_PROCESSO`, `CONTEXTO` em JSON, `ENCERRADO`):
  é o estado de cada processo que as etapas seguintes leem (caminhos, versão, sorteio,
  parâmetros). `PROCESSOS` continua com uma linha por etapa; `ID_PROCESSO` vem de
  `CONTEXTOS`.
- **Etapa pulada é registrada.** Se a geração passa de uma etapa a outra entre duas
  consultas do painel, a intermediária ganha a linha dela em `PROCESSOS`, com duração
  quase zero, em vez de sumir do histórico.
- **O residual roda depois do codificador** na espinha; por isso a última chamada
  gravada é do residual e a etapa observada pode voltar de 6 para 5. O fluxo só anda
  para a frente.
- **`lago.disponivel` usa `head_bucket`.** Com acesso anônimo, o SeaweedFS responde a
  `list_buckets` com lista vazia; a primeira versão dizia "bucket indisponível" na
  segunda abertura do app. Achado no teste de integração com o SeaweedFS real.
- **`.streamlit/config.toml`** faz o app escutar só em `127.0.0.1` e desliga a
  estatística de uso: o padrão do Streamlit escutava na rede local e anunciava URL
  externa.
- **`cancelar` não apaga a pasta de trabalho.** Tudo o que importa está no lago;
  apagar não era necessário.
- **A origem de cada linha da entrada** (`parametros.json`) usa `fonte: "dados"` para
  as linhas da extração do processo e `fonte: "guia"` para as linhas sujas antigas.
- **Gerador:** o estouro previsto se confirmou e foi declarado: 1.875 linhas (teto
  1.850) e `e3_crivo.py` com 211 (teto 200). Rejeitar a regra vencedora de um
  `(coluna, tipo)` deixa a variante seguinte vencer
  (`docs/DECISOES.md#decisoes-do-usuario`).
- **Percurso offline pela interface:** com `PROVEDOR=gravado` a geração só funciona com
  o mesmo guia das respostas gravadas, e o sorteio da interface não o reproduz. O
  percurso offline completo está nos testes (`tests/orquestrador/test_fluxo.py`), e
  foi repetido contra o SeaweedFS real, fora da suíte.
- **Correções da revisão de código (18/10/2026)**, cada uma com teste e prova por
  mutação:
  - "Gerar nova versão" lê `REGRAS` do arquivo do limpador pela AST
    (`decisoes.regras_do_limpador`), sem executar o arquivo e sem depender de a
    aplicação ter dado certo.
  - Esquema nomeado num processo cancelado antes do guia volta a sortear o guia na
    ingestão seguinte, em vez de quebrar.
  - Falha do lago ou de arquivo no versionamento fecha a etapa 7 com erro; aprovar só
    vale na etapa 9 em andamento; cada geração limpa o corrigido e o truncamento da
    versão anterior do contexto. Antes, aprovar podia gravar o corrigido da v1 como v2.
  - O PID só é tratado como nosso filho se o processo nasceu até um minuto da hora
    registrada (o Windows reaproveita PID), e cancelar só encerra durante a geração.
  - A API viva do aperfeiçoamento é sempre o `PROVEDOR` que a tela anuncia;
    `PROVEDOR_VIVO` do ambiente só vale com `PROVEDOR=gravado`.
  - `reaproveitar` pergunta de novo à API o que tinha falhado por rede, e isso conta
    como chamada nova.
  - Aperfeiçoar só reprova a versão depois de a nova geração subir.
  - Cada processamento ganha a sua linha em `DADOS`, mesmo com o hash repetido.

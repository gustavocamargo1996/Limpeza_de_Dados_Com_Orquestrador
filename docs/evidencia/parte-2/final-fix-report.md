# Relatório da leva de correção da revisão final — parte 2

Branch `parte-2-agentes`, a partir de 722d148 (282 passed). Os itens seguem a
numeração de `final-fix-brief.md`. Toda mutação foi aplicada por um script que
grava os bytes originais, roda o pytest e restaura os bytes, conferindo que o
arquivo voltou idêntico (`revertido: True` em todas).

## 1. (Critical) A função que lança numa célula derruba o limpador

**O que mudou.**
- `limpeza2/motor.py`, `reparar`: `escalar(antes)` fica num `try`; com exceção,
  `depois = None`, então a célula fica marcada e não reparada (flag). O comentário
  de 1 linha nomeia a degradação e aponta `docs/DECISOES.md#funcao-que-lanca`.
- `limpeza2/e6_codificador.py`, `_funcao`: `marcados = sorted(set(...))` guarda
  **todos** os valores marcados distintos; o prompt leva
  `marcados[: config.VALORES_NO_PROMPT]` e `testar_fumaca` roda sobre
  `marcados + exemplos do guia`. Saldo de linhas: zero.
- `docs/DECISOES.md`: nova seção `{#funcao-que-lanca}`.

**Testes.**
- `tests/test_motor_aplicar.py::test_funcao_que_lanca_numa_celula_vira_flag_e_nao_derruba_a_tabela`:
  `normalizar` com função que lança em `N/A`; `aplicar_regras` não levanta, `N/A`
  fica com o valor original e com `flags` True, e `12 oz` continua reparado.
- `tests/test_e6_codificador.py::test_fumaca_cobre_valor_marcado_que_nao_coube_no_prompt`:
  35 valores marcados distintos; a função só lança no último, que comprovadamente
  não está no prompt; ela é rejeitada.

**Efeitos colaterais que exigiram ajuste de teste existente** (consequência direta
da decisão, não pedidos no brief):
- `tests/test_e3_crivo.py::test_crivar_reparo_reprova_estrategia_que_lanca`: com a
  captura, uma função que lança em toda célula não chega mais ao `except` do crivo.
  O teste passou a cobrir o `lancou` que ainda existe (a função ausente de
  `funcoes`, `KeyError` fora da célula). Um teste novo,
  `test_crivar_reparo_reprova_funcao_que_lanca_em_toda_celula`, fixa que a função
  que lança em toda célula cai como `nao_repara`. Isso está escrito na seção nova
  do DECISOES.
- `tests/test_e6_codificador.py::test_funcao_quebrada_derruba_a_fumaca_final`: o
  código `return valor + desconhecida` lança por célula e agora vira flag, então a
  fumaça final não o veria mais. O teste passou a usar uma função que quebra ao
  **carregar** o módulo (`def corrigir(valor=desconhecida)`), que é o que a fumaça
  final ainda pega.

**Mutações.**
- Tirar o `try/except` do motor → falham
  `test_funcao_que_lanca_numa_celula_vira_flag_e_nao_derruba_a_tabela` e
  `test_crivar_reparo_reprova_funcao_que_lanca_em_toda_celula`.
- Voltar a fumaça para `marcados[: config.VALORES_NO_PROMPT]` → falha
  `test_fumaca_cobre_valor_marcado_que_nao_coube_no_prompt`.
- Trocar `spec.loader.exec_module(modulo)` por `pass` em `escrever` → falha
  `test_funcao_quebrada_derruba_a_fumaca_final`.

## 2. (Important) O replay não reproduzia o limpador byte a byte

**O que mudou.**
- `limpeza2/provedor.py`, `Cliente.__init__`: `self.origem = getattr(api, "origem", None) or {provedor, modelo, esforco do config}`,
  e o `respostas.jsonl` nasce com a linha `{"origem": {...}}`.
- `_Gravado.__init__`: lê a origem do registro `{"origem": ...}` e não a põe nas
  filas de respostas. Como o `Cliente` do replay recebe a origem do `_Gravado`, ele
  regrava a mesma origem no novo `respostas.jsonl`. `_Api` e o `Roteiro` dos testes
  não têm `origem`, e caem no `config`.
- `limpeza2/e6_codificador.py`: `_limpador` recebe o `cliente`; `_cabecalho` recebe
  `origem` e `chamadas`; o `.md` usa
  `"- modelo: {modelo} ({provedor}), raciocinio {esforco}".format(**cliente.origem)`.
  Nada de `config.MODELO`/`PROVEDOR`/`ESFORCO_RACIOCINIO` sobra no e6. Saldo de
  linhas: zero (200).
- `docs/DECISOES.md#determinismo-da-geracao`: parágrafo "A origem viaja com as
  respostas".

**Testes.**
- `tests/test_espinha.py::test_replay_gravado_reproduz_o_limpador_byte_a_byte`:
  gera o `beers` com o dublê em `a/beers_teste`, restaura o `_construir_api` real,
  põe `PROVEDOR=gravado` e `RESPOSTAS_GRAVADAS` no arquivo gravado, gera em
  `b/beers_teste` e exige bytes idênticos do limpador **e** do `.md`.
- `tests/test_provedor.py::test_gravado_devolve_a_origem_gravada_e_a_regrava`: com
  `config.MODELO` trocado depois da gravação, a origem do replay é a gravada, a
  resposta ainda é reproduzida, e a primeira linha do novo `respostas.jsonl` é a
  mesma origem.

**Mutações.**
- Cabeçalho de volta a `config.PROVEDOR` → falha o teste de replay da espinha.
- `_Gravado` sem ler a origem → falham o teste do provedor e o da espinha.
- `_Gravado` sem pular o registro de origem (`if False:`) → falham
  `test_gravado_reproduz_a_geracao_na_mesma_ordem` e o teste novo do provedor.

## 3. (Important) O `.md` mostrava como aprovada a variante que perdeu

**O que mudou.** `limpeza2/e3_crivo.py`: `"superada"` entrou em `MOTIVOS`; depois
da disputa, toda candidata com `motivo == "aprovada"` que não ficou entre as
vencedoras recebe `motivo = "superada"`. Três linhas.

**Teste.** `tests/test_e3_crivo.py::test_entre_variantes_fica_a_que_marca_menos`
agora exige `("superada", "aprovada")` para larga e estreita, e `superada` de novo
com a ordem invertida da lista. Antes, esse mesmo teste fixava o defeito
(`larga.metricas["motivo"] == "aprovada"`).

**Mutação.** Trocar a regravação por `pass` → falha
`test_entre_variantes_fica_a_que_marca_menos`.

## 4. (Important) A guarda do teste de vazamento era fraca

**O que mudou.** `tests/test_vazamento.py::test_geracao_so_abre_o_sujo_o_guia_e_o_motor`.

**Desvio do brief, com motivo.** A primeira versão fez o que o brief pede ao pé da
letra (exigir os quatro arquivos em `abertos`), e a mutação pedida **não mordeu**:
removi o registro da espia de `read_csv` e o teste seguiu verde. O motivo é que o
`pd.read_csv` abre o arquivo pelo `open` embutido, e a espia de `open` registrava
os CSVs também. Por isso, cada espia passou a ter a sua lista: `lidos_csv` (do
`read_csv`) tem de conter o sujo e os dois CSVs do guia, e `abertos` (do `open`)
tem de conter os quatro, motor incluído. Os intrusos são procurados na união das
duas.

**Mutações.**
- A espia de `read_csv` não registra → falha (antes da correção acima, não falhava).
- A espia de `open` não registra → falha.

## 5. Itens da triagem

- `limpeza2/e3_crivo.py`, `crivar_residual`: o comentário passou a ser
  `# Ver docs/DECISOES.md#residual-congelado: no dicionario o veto nao tem excecao.`
  A seção citada contém o parágrafo "O veto por valor certificado não tem exceção
  no dicionário".
- `limpeza2/e6_codificador.py`: a chave do retry agora é `tentativa_rejeitada`.
  `test_rejeitada_duas_vezes_cai` lê a chave nova, e um teste novo,
  `test_aprovada_na_segunda_tentativa_guarda_a_rejeitada_com_nome_proprio`, exige
  que a regra aprovada na segunda tentativa não carregue `detalhe_reparo`.
  Mutação: voltar a `detalhe_reparo` → falham os dois. Sem linha a mais.
- `tests/test_e1_perfil.py::test_contagens_do_perfil_sao_int_do_python`: 1 linha
  de comentário dizendo que é guarda de versão do pandas, sem RED no pandas 3.
- `docs/REGRAS_DO_LIMPADOR.md` §2: a tabela foi reescrita com os dez passos de
  `espinha.py` (perfil; conformidade e crivo; detector; crivo da detecção;
  especificador; funções de correção; crivo do reparo; residual; crivo do
  residual; arquivos), em linguagem de usuário. A menção a "etapa 6" no §7 virou
  "passo 8".

## 6. Menores

- **Recursão**: `limpeza2/portao.py`, `validar`, rejeita `ast.Name` com
  `id == nome_funcao` dentro da função, com a mensagem
  "recursao proibida: o corpo nao pode citar 'corrigir', que muda de nome no
  limpador". Dois casos novos em `tests/test_portao.py::test_rejeita_codigo_proibido`
  (chamada recursiva e alias `f = corrigir`). Mutação: `if False:` no lugar da
  condição → falham os dois.
- **inf**: `limpeza2/e2_detector.py`, `_valida`, exige `math.isfinite` nos dois
  limites (`import math` no topo). Teste novo
  `tests/test_e2_detector.py::test_faixa_com_limite_infinito_cai` (`inf/inf` e
  `-inf/3` caem, `1/3` fica). Mutação: tirar o `isfinite` → falha.
- **Ordem de aplicação**: `limpeza2/motor.py`, `TIPOS` começa por `conformidade`.
  Teste novo `tests/test_tipos.py::test_conformidade_vem_antes_de_formato`.
  Mutação: `conformidade` de volta ao fim → falha. Registrado em
  `docs/DECISOES.md#motor-unico` em 2 linhas. Os limpadores congelados em
  `tests/fixtures/` embutem o motor antigo e não mudaram; os números deles seguem
  os mesmos.
- **`.gitignore`**: `saida/` acrescentado (`git check-ignore` confirma; nada em
  `saida/` estava versionado).
- **CLAUDE.md** §9: o comentário de `espinha.py` agora é
  `# a ordem das etapas, e nada mais; o CLI so a chama`.

## Suíte, tamanho e commits

- Suíte final: `292 passed in 35.26s` (282 + 10 testes novos; nenhum skip,
  nenhum teste toca rede ou API).
- Tamanho: 16 arquivos `.py` fora de `tests/`; 1.794 linhas no total (teto 1.800).
  Maiores: `e6_codificador.py` 200 (sem linha líquida a mais), `motor.py` 197,
  `e3_crivo.py` 196, `provedor.py` 158. `portao.py` 115, `e2_detector.py` 132.
  Nada foi espremido para caber.
- Commits:
  - `b234d3c` Revisao final: funcao que lanca vira flag, replay byte a byte, variante superada (itens 1 a 4; 5 no e3 e no e6)
  - `4575769` Revisao final: recursao no portao, faixa infinita, conformidade aplica primeiro (item 6, código)
  - `02d83ba` Revisao final: ordem da geracao nos documentos, saida/ ignorada (itens 5 e 6, documentos e housekeeping)

## Observações

- Folga de linhas: sobram 6 até 1.800 e zero no `e6_codificador.py`.
- O item 4 não ficou como o brief descrevia, porque a mutação pedida não mordia na
  forma literal; a explicação está acima.
- Pré-existente, fora do escopo: com `PROVEDOR=ollama`, a origem registra
  `esforco` do `config` ("none"), embora o `_Api` do Ollama não envie o parâmetro.
  O cabeçalho já imprimia isso antes desta leva.

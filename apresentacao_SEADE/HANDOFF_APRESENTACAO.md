# Handoff: a seção "Ferramenta de limpeza de dados" da apresentação SEADE

> **Para a sessão que vai montar os slides.** Escrito em 18/10/2026 pela sessão que
> construiu o gerador e o orquestrador deste repositório. O usuário é o Gustavo
> Camargo, mestrando do IME-USP. Ele trabalha em português do Brasil e prefere ouvir
> que um número é ruim a ver um número inflado. Leia este arquivo inteiro antes de
> abrir o `.pptx`.

---

## 1. A missão

Criar os 10 slides desenhados pelo usuário em
`apresentacao_SEADE/especificacao_apresentacao.excalidraw` e com eles **substituir a
seção dele** no deck `apresentacao_SEADE/Apresentação SEADE 21102026.pptx`, respeitando
o layout e as fontes desse deck.

**O deck é coletivo.** São 67 slides de um grupo do IME-USP para a Fundação SEADE, com
seções de outras pessoas (Thales, Wagner, Pedro, Rafael e outros). A seção do Gustavo é
**do slide 24 ao 31**:

| Slide | Hoje | O que fazer |
|---|---|---|
| 24 | separador "Ferramenta de limpeza de dados" (layout `SECTION_HEADER`) | **manter** |
| 25 a 31 | Contexto; Oportunidade: LLMs; Framework: Visão Geral; LLM de limpeza (2×); Resultados (2×) | **substituir** pelos 10 slides novos |
| 1 a 23 e 32 a 67 | seções dos colegas, agenda, capa, equipe | **não tocar** |

Regras da entrega:
- **Não sobrescreva o original.** Grave como
  `apresentacao_SEADE/Apresentação SEADE 21102026 - v2.pptx` e só troque o original se o
  usuário pedir.
- **Mostre ao usuário antes de dar por pronto**: a lista dos 10 slides com o texto de
  cada um e, se for possível renderizar, as imagens.
- O arquivo tem 50 MB, quase tudo imagem dos colegas. Edite com `python-pptx`
  preservando o resto; não reconstrua o deck do zero.

## 2. O que ler, nesta ordem

1. **Este arquivo.**
2. `apresentacao_SEADE/especificacao_apresentacao.excalidraw`: o desenho dos 10 slides.
   É JSON. Leia só os elementos com `"isDeleted": false`; os textos estão em
   `originalText`. A seção 4 abaixo já traz a transcrição, mas confira no original.
   **Abra também as imagens `apresentacao_SEADE/layout_excalidraw/slide01.png` a
   `slide10.png`**: são o desenho de cada slide, com a disposição dos blocos que o usuário
   quer (seção 4.1).
3. `Qualificacao_Mestrado_Gustavo_Camargo.pdf` (raiz do repositório, 91 páginas; leia
   com `pages`):
   - Resumo, p. 5;
   - Cap. 1, Introdução, p. 13 a 16: contexto SEADE e os objetivos;
   - Cap. 2, p. 17 a 30: estatísticas públicas, Data Mesh (2.2) e limpeza de dados (2.3);
   - Cap. 4, Proposta, p. 55 a 63, com a **Figura 4.1 na p. 57** (o fluxograma do
     framework);
   - Cap. 3 (mapeamento) só se precisar citar a literatura.
4. `extracao_final.xlsx` (raiz): as **73 referências** do mapeamento sistemático. A aba
   `Extracao` tem `Titulo`, `Nome da Tecnica`, `Ano`, `Abordagem Tecnica Proposta`,
   `Metricas de Avaliacao` e `Resultados Principais`; a aba `Sumario` traz as contagens.
   É a fonte para o slide 2 e para os números da literatura no slide 10.
5. A solução neste repositório:
   - `docs/CONTINUACAO.md`: o estado e os **resultados medidos** (§7);
   - `docs/HANDOFF_ORQUESTRADOR.md`: como o gerador funciona, em linguagem de usuário;
   - `CLAUDE.md`: §1 (o que é), §9 (arquitetura do gerador) e §11 (orquestrador e como
     rodar);
   - `docs/superpowers/specs/2026-10-17-orquestrador-design.md`: o orquestrador.

## 3. O layout e as fontes do deck (medidos no arquivo)

- **16:9, 13,333 × 7,5 polegadas.**
- **Layout dos slides de conteúdo: `2_1 conteúdo`** (índice 22 em
  `prs.slide_layouts`), o mesmo dos slides 25 a 31 de hoje. Placeholders:

  | idx | tipo | posição (pol) | tamanho (pol) |
  |---|---|---|---|
  | 0 | título | (0,34; 0,28) | 12,67 × 1,22 |
  | 1 | corpo | (0,34; 1,52) | 12,67 × 5,07 |
  | 12 | número do slide | (12,14; 7,00) | 0,87 × 0,40 |

- **Fontes:** o tema é **Arial** (maior e menor). Os textos da seção do Gustavo **não
  definem fonte nem tamanho**: herdam do layout. Faça igual: escreva nos placeholders e
  **não fixe fonte nem tamanho**, salvo onde o texto não couber. Nesse caso, reduza o
  tamanho, mas não troque a fonte. Use os níveis de parágrafo (0 e 1) como os slides
  atuais fazem.
- **Cores do tema:** `2A5FFF` (azul principal, `dk2` e `accent1`), `93AFFF`, `D3DFFF`,
  `C5C5C5`, `5B9BD5`. Use-as nos destaques e no sombreamento das figuras; não traga
  cores de fora.
- **Imagens:** os slides atuais as colocam soltas sobre o layout. Por exemplo, a figura
  do framework fica em (0,17; 1,67) com 13,00 × 4,34 pol.
- **Português com acentuação normal** nos slides.

## 4. O desenho do usuário, slide a slide

Transcrição do Excalidraw, com o que cada slide pede e de onde tirar o conteúdo. Onde
o usuário escreveu **"Me ajude aqui"**, a seção 5 traz o texto proposto.

| # | Título | O que o desenho pede |
|---|---|---|
| 1 | **Contexto** | três blocos ligados por setas ao **Problema**: "4 requisitos que regem a produção de estatísticas oficiais"; "4 requisitos que regem o Data Mesh"; "Limpeza de dados: primeira etapa responsável pela qualidade; pode consumir 80% do tempo de um cientista". Embaixo: *"Problema: como sistematizar a limpeza de dados atendendo aos requisitos críticos das estatísticas públicas e de forma aderente ao Data Mesh?"* |
| 2 | **Limpeza de Dados e LLMs** | "O que é limpeza de dados" (conjunto de processos e técnicas de identificação, correção e mitigação de erros, inconsistências, ruídos e incompletudes); exemplos (*feature cleaning*, *entity matching*, imputação); "Oportunidade das LLMs" (explodiram em 2023; interpretação semântica, geração de regras, geração de código) |
| 3 | **Visão Geral do Framework** | *"Objetivo: estruturar um framework baseado em LLMs para apoiar a limpeza de dados em estatísticas públicas, garantindo reprodutibilidade, auditabilidade e integração com a arquitetura Data Mesh"* + a figura do framework |
| 4 | **Etapa 1: Ingestão e Verificação** | figura completa **sombreada** + recorte da etapa **explodido** + tela do controle de esquemas do banco + tela da POC + explicação: (1) varre o controle e verifica se há esquema e limpador para o dado ingerido; (1.a) se não há, cria o esquema e inicia a criação do limpador; (1.b) se há, usa o limpador existente |
| 5 | **Etapa 2: Amostra Guia** | figura sombreada + recorte + tela da POC + explicação: disponibiliza ao usuário algumas linhas do dado e pede que ele corrija o necessário |
| 6 | **Etapa 3: Detector e Gerador de Regras** | figura sombreada + recorte + tela da POC + **Responsabilidade / Entradas / Saídas ("Me ajude aqui")** |
| 7 | **Etapa 4: Gerador de Código** | figura sombreada + recorte + **trecho do código Python gerado** + **Responsabilidade / Entradas / Saídas ("Me ajude aqui")** |
| 8 | **Etapa 5: Relatório e Validação** | figura sombreada + recorte + tela da POC + explicação: o usuário aprova ou reprova; na aprovação, o dado corrigido e os artefatos vão ao data lake; na reprovação, ele realimenta o limpador aprovando regras não incluídas ou reprovando regras propostas |
| 9 | **Etapa 6: Armazenamento** | figura sombreada + recorte + tela do bucket + "explicar a estratégia de armazenamento e a organização dos diretórios" |
| 10 | **Resultados Preliminares e Próximos Passos** | comparação de **F1-score em três benchmarks** (environment, beers e mais um) **contra 2 ou 3 soluções da literatura** (exemplos dele: HoloClean, ZeroDC, BClean), informando tamanho do guia e modelo. Próximos passos: aplicar o limpador em **estatísticas vitais com Ollama**, propondo um modelo que aceite esquema |

Observação: o título do slide 10 no desenho diz "Premilinares"; o certo é "Preliminares".

**De onde tirar o texto dos slides 1 e 2:** dos slides 25 e 26 atuais (os quatro
requisitos já estão lá: qualidade dos indicadores, rastreabilidade, auditabilidade e
reprodutibilidade) e da qualificação, §2.1, §2.2 e §2.3. Os "4 requisitos do Data Mesh"
são os quatro pilares (§2.2): propriedade orientada a domínio, dados como produto,
plataforma de autoatendimento e governança federada. Os slides 6 e 13 do deck (seção
dos colegas) falam dos mesmos pilares: confira lá para usar o mesmo vocabulário.
**Confirme a fonte do "80% do tempo"** na qualificação antes de pôr o número no slide.

### 4.1 A disposição dos blocos: o usuário a desenhou, e ela vale

O Excalidraw não traz só o conteúdo: **a posição e o tamanho de cada bloco são a
sugestão do usuário para a disposição no slide**. Siga essa disposição.

- **Veja antes de montar:** `apresentacao_SEADE/layout_excalidraw/slide01.png` a
  `slide10.png` são os 10 quadros do Excalidraw desenhados como imagem: os blocos nas
  posições e proporções do desenho, a faixa verde do título e as setas em vermelho (a
  bolinha marca a ponta). Abra cada PNG com a ferramenta de leitura de imagem.
- **Posições prontas:** `apresentacao_SEADE/layout_excalidraw/posicoes.md` dá, para cada
  bloco, x, y, largura e altura **em polegadas do slide**. A área útil do quadro (abaixo da
  faixa de título) foi mapeada na área do placeholder de corpo do layout `2_1 conteúdo`,
  de (0,34; 1,52) a (13,01; 6,59). O quadro do Excalidraw é mais quadrado que o slide de
  16:9, então trate as medidas como **guia de proporção**, não como coordenada exata:
  alinhe as bordas e iguale os espaçamentos.
- **A faixa verde de cada quadro é o título do slide.** Use o placeholder de título
  (idx 0), sem o "Slide N -" do desenho.
- **Slide 1:** três blocos lado a lado no alto (requisitos das estatísticas oficiais,
  requisitos do Data Mesh e limpeza de dados), com **setas convergindo** para o bloco do
  Problema, largo, embaixo.
- **Slide 2:** coluna da esquerda com "O que é limpeza de dados" em cima e "Exemplos"
  embaixo; coluna da direita, mais alta, com "Oportunidade das LLMs".
- **Slide 3:** o objetivo numa faixa larga no alto e a figura do framework ocupando a
  largura toda embaixo.
- **Slides 4 a 9, uma grade comum** (mantenha-a idêntica nos seis, para a sequência ser
  lida como uma só):
  - à esquerda, em cima: a **figura completa sombreada**, pequena (cerca de 4,4 × 1,3 pol);
  - à esquerda, embaixo: o **recorte explodido** da etapa (cerca de 4,3 × 2,4 pol);
  - à direita, em cima: **a tela** (da POC, do banco, do bucket ou o código gerado). No
    slide 4, ela se divide em duas, lado a lado: a tela da POC e a do controle de esquemas;
  - à direita, embaixo: a **explicação**.
- **Slide 10:** duas faixas largas: a comparação de F1 em cima e os próximos passos
  embaixo.

## 5. A solução, o suficiente para escrever os slides 4 a 9

### 5.1 A figura do framework e o que foi implementado

A figura é a **Figura 4.1** da qualificação (PDF p. 57). Ela já está embutida no slide
27 atual como PNG de 2048 × 684, e é dali que se extrai a imagem com `python-pptx`
(`shape.image.blob`). Ela tem quatro raias (Front-End, Entrada de Dados, Integrador e
Banco de Dados), mas **não tem as seis etapas nomeadas**. Esta é a correspondência
entre as etapas do desenho e as regiões da figura, para o sombreamento e o recorte:

| Etapa do desenho | Região da Figura 4.1 | O que existe no repositório |
|---|---|---|
| 1. Ingestão e Verificação | Plataforma Self-Service → Dados → losango "Modelo de Limpeza Existente?" (+ Metadados) | `orquestrador/fluxo.py` `iniciar`; esquema conhecido = mesmo domínio e mesmo conjunto de colunas (`controle.buscar_esquema`) |
| 2. Amostra Guia | "Iniciar Geração de Novo Modelo" + "Amostra de Dados" | `orquestrador/amostra.py`, `tela_guia.py`: linhas sorteadas com semente, corrigidas pelo usuário, por formulário ou template |
| 3. Detector e Gerador de Regras | "Agente Gerador de Prompt (Chain-of-Thought)" + "Prompt Construtor de Regras" + "Instruções do Dono de Produto" | `limpeza2/`: conformidade de schema, **detector**, crivo, **especificador** e residual |
| 4. Gerador de Código | "Agente Gerador de Código de Limpeza" + "Código de Limpeza" + "Documentador de Código" | `limpeza2/e6_codificador.py` (**codificador**), `portao.py`, `motor.py` |
| 5. Relatório e Validação | Executar Limpeza → Auditor de Execução → Relatórios → Avaliação do Dono → "Modelo Aprovado?" e o laço "Não: feedback atualiza instruções" | `orquestrador/relatorio_geracao.py`, `relatorio_limpeza.py`, `decisoes.py`, `tela_resultado.py` |
| 6. Armazenamento | raia "Banco de Dados": Metadados e "Dados Tratados Inseridos na Base" | `orquestrador/lago.py` (SeaweedFS, S3) e `controle.py` (SQLite) |

**Uma diferença que precisa ficar coerente nos slides.** A figura desenha **dois**
agentes de LLM (gerador de prompt e gerador de código). A implementação tem **três**
(detector, especificador e codificador), e a etapa 3 do desenho junta os dois
primeiros. Escreva os slides 6 e 7 pela implementação, e não pela figura. Se for
redesenhar a figura em vez de sombrear a original, pergunte ao usuário antes.

**Sombreado e explodido:** a forma mais simples, sem editar a imagem, é pôr sobre ela
retângulos semitransparentes (cinza ou `D3DFFF`) cobrindo o que **não** é a etapa, e
um recorte ampliado da região da etapa ao lado, cortando o PNG com Pillow. Use as
mesmas coordenadas do recorte nos seis slides, para a sequência ficar consistente.

### 5.2 Texto proposto para o slide 6 (Etapa 3: Detector e Gerador de Regras)

- **Responsabilidade:** decidir **onde estão os erros** e **como corrigi-los**, sem
  escrever código. Primeiro uma etapa determinística deriva o formato de cada coluna das
  células que o guia certificou (conformidade de schema). O **agente detector** propõe
  regras de um catálogo fechado: formato, domínio, faixa, ausente disfarçado e
  dependência entre colunas. Um **crivo determinístico, sem LLM**, reprova toda regra que
  o guia desmente. O **agente especificador** escolhe, para cada regra aprovada, uma
  estratégia de correção (normalizar, moda condicionada, vizinho no domínio, dicionário
  ou esvaziar), com o raciocínio em três frases.
- **Entradas:** o perfil da tabela suja (valores frequentes e raros, padrões e
  dependências mineradas entre colunas; o LLM não recebe a tabela inteira), a
  amostra-guia corrigida pelo usuário e, num ciclo de aperfeiçoamento, as decisões e
  instruções do usuário.
- **Saídas:** as regras aprovadas (detecção + estratégia de correção) e um relatório
  com **cada regra proposta, aprovada ou não, com o motivo** (por exemplo: "marcou como
  erro uma célula que você confirmou como correta").

Fontes: `CLAUDE.md` §9, `docs/HANDOFF_ORQUESTRADOR.md` §5.4 (o glossário dos motivos) e
`limpeza2/e2_detector.py` (o que o detector recebe).

### 5.3 Texto proposto para o slide 7 (Etapa 4: Gerador de Código)

- **Responsabilidade:** traduzir cada estratégia de correção do tipo "normalizar" numa
  função Python pequena, `corrigir(valor)`, que passa por um **portão de segurança**
  (análise da AST: sem `import`, sem `eval`, `exec` ou `open`) antes de rodar. O resto
  do limpador é um **motor determinístico único**, copiado byte a byte, e por isso o
  limpador gerado roda **sem LLM** e sempre do mesmo jeito.
- **Entradas:** as especificações de correção do especificador e os exemplos
  `sujo → limpo` do guia.
- **Saídas:** o `limpador_<versão>.py`, um script autônomo com as regras (`REGRAS`), o
  dicionário residual e as funções; o raciocínio em Markdown; e o `respostas.jsonl`, que
  permite **regenerar exatamente o mesmo limpador sem chamar a API**
  (reprodutibilidade).
- **Trecho de código para o slide:** `corrigir_1` e `corrigir_2` de
  `tests/fixtures/limpador_beers_poc2.py` (a partir da linha 320). São curtos e mostram
  a correção de `"12.0 oz"` → `"12"` e de `"0.069%"` → `"0.069"`. Para o leitor ver a
  regra junto do código, use também o começo da lista `REGRAS` (linha 218).

### 5.4 Slides 4, 5, 8 e 9: o que contar

- **Slide 4:** o controle de esquemas é o SQLite `var/controle.sqlite`, tabelas
  `ESQUEMAS`, `LIMPADORES`, `PROCESSOS`, `DADOS` e `ETAPAS` (os campos estão na spec do
  orquestrador, §4). Um esquema é reconhecido pelo domínio mais o conjunto de colunas.
- **Slide 5:** o padrão é de **20 linhas, no mínimo 10**. O experimento de tamanho de
  guia mostrou que 10 bastam (`docs/HANDOFF_ORQUESTRADOR.md` §5.2). As linhas são
  **sorteadas do próprio dataset**, o usuário corrige o que estiver errado e pode
  "sortear de novo" uma linha que não saiba corrigir, e a troca fica registrada. O guia
  é a "verdade estabelecida": nenhuma regra pode contradizê-lo.
- **Slide 8:** aprovar grava o corrigido e os relatórios. Aperfeiçoar permite aprovar
  uma regra reprovada ou rejeitar uma aprovada, **nunca contra o guia** (a interface não
  oferece a opção, e o crivo do gerador a recusa). O ciclo novo **reaproveita as
  respostas gravadas** e só chama a API para o que mudou: no teste, rejeitar uma regra
  ruim gerou a versão nova com **zero chamadas novas**.
- **Slide 9:** um bucket S3 (SeaweedFS) com
  `<Domínio>/<Esquema>/{Original, Amostra_Guia, Limpador, Corrigido}/<data_hora>/`. O
  original vai com o sha256, e cada versão do limpador guarda o código, o raciocínio, as
  respostas do LLM e as decisões. Metadados de controle ficam no SQLite. A tabela
  completa está na spec do orquestrador, §3.

### 5.5 O slide 10: números, só os medidos

Resultados **medidos** (gpt-6-luna, tabelas de 300 linhas, as linhas do guia fora da
medição; fonte `docs/CONTINUACAO.md` §7 e `docs/HANDOFF_ORQUESTRADOR.md` §1 e §5.2):

| Braço | Guia | Precisão | Recall | F1 |
|---|---|---|---|---|
| beers | 20 linhas + 10 pares | 98,6% | 98,4% | 98,5% |
| beers | sem guia | 82,7% | 9,7% | 17,3% |
| environment | 20 linhas | 95,2% | 74,1% | 83,3% |
| environment | sem guia | 50,0% | 16,0% | 24,3% |

A curva de tamanho do guia (5, 10, 15 e 20 linhas, só linhas corretas, sem pares) está
em `docs/HANDOFF_ORQUESTRADOR.md` §5.2.

**Regras, sem exceção:**
1. **Não invente número.** Os F1 da literatura (HoloClean, ZeroED/ZeroEC, BClean e
   outros) só entram se vierem de `extracao_final.xlsx` (`Resultados Principais`,
   `Metricas de Avaliacao`) ou do artigo, com a referência no slide. Sem número na
   fonte, a célula fica "não reportado".
2. **Declare que a comparação não é direta.** Nós medimos em recortes de 300 linhas,
   com supervisão de um guia de 20 linhas (220 células). Os artigos usam as tabelas
   inteiras e protocolos próprios. O slide tem de dizer isso numa nota.
3. **O terceiro benchmark não foi rodado.** Hospital, flights e rayyan são candidatos
   comuns na literatura, mas rodar custa API. **Pergunte ao usuário** se ele quer rodar
   (é decisão dele, anunciada antes) ou mostrar só dois.
4. Mostre precisão ao lado de recall, não só o F1: é onde a degeneração aparece, e o
   usuário pediu isso no projeto.

**Próximos passos, com Ollama:** o caminho `ollama` existe em
`limpeza2/provedor.py`, mas **nunca rodou de verdade**. O gerador pede resposta em
JSON com esquema estrito. Proponha um modelo aberto que aceite saída estruturada por
esquema JSON no Ollama (a família Qwen, de 7B a 14B, é uma candidata comum) e **diga no
slide que é proposta, não resultado**. Verifique antes, na documentação do Ollama, se a
versão em uso aceita `response_format` com esquema pela API compatível com a da OpenAI.

## 6. Os insumos visuais

| Insumo | Como obter |
|---|---|
| Figura do framework | o PNG do slide 27 atual (`prs.slides[26]`, a imagem) ou a p. 57 do PDF |
| Telas da POC (slides 4, 5, 6 e 8) | o app Streamlit (seção 7). Sem navegador automatizado, **peça ao usuário** que tire as capturas, com a lista exata de telas e estados |
| Tela do controle de esquemas (slide 4) | `var/controle.sqlite`, aberto num visualizador de SQLite, ou uma tabela montada no slide a partir de um `SELECT` |
| Tela do bucket (slide 9) | o Filer do SeaweedFS em `http://127.0.0.1:8888/buckets/limpeza/`, com o SeaweedFS no ar |
| Código gerado (slide 7) | `tests/fixtures/limpador_beers_poc2.py`, linhas 218 a 240 e 320 a 333 |

## 7. Como subir a POC para as capturas

Da raiz do repositório, no PowerShell:

```powershell
.\subir_seaweed.cmd                              # num terminal; deixe aberto
.venv\Scripts\streamlit run orquestrador\app.py  # noutro terminal; abre em 127.0.0.1:8501
```

- **Dataset e guia prontos** em `simulacao/` (veja `simulacao/LEIA-ME.md`): `beers` e
  `environment`, com o guia já corrigido nas linhas que o app sorteia.
- **Custo:** com `PROVEDOR=openai` no `.env`, clicar em "Iniciar geração" gasta API
  (cerca de 30 chamadas, centavos de dólar) e manda linhas para a OpenAI. **Nunca
  dispare uma geração sem anunciar e ter o aceite do usuário.** Sem gastar, a interface
  vai até a tela de parâmetros. A tela de resultado sem gasto exige montar o estado por
  script, como em `tests/orquestrador/test_fluxo.py` (fixture `mvp`, com
  `PROVEDOR=gravado` e o guia do MVP).
- **O disco C: está 94,6% cheio:** o SeaweedFS só comporta um bucket, o `limpeza`.
  Não crie outros.
- **Capturas automáticas** precisam de um navegador automatizado (por exemplo, o
  Playwright, que baixa um Chromium). Isso é instalação de software, não de skill:
  **pergunte antes**.

## 8. Ferramentas e permissões

- **Skill de PowerPoint:** já disponível nesta instalação (`anthropic-skills:pptx` ou
  `pptx`). Carregue-a antes de editar o `.pptx`.
- **Excalidraw:** o arquivo é JSON e se lê direto, sem skill. O usuário **autorizou
  instalar** uma skill de PowerPoint ou de Excalidraw se for preciso.
- **`python-pptx`, `openpyxl`, `pypdf`, `Pillow`:** use com `uv run --no-project --with
  <pacote>` para não mexer no `.venv` do projeto.
- **Renderização dos slides em imagem:** o LibreOffice **não está instalado**. Sem ele,
  não há como gerar uma prévia em PNG para conferir o resultado. Instalar é software
  novo: **pergunte ao usuário**. Sem prévia, confira pelo `python-pptx` (posições, se o
  texto cabe) e peça ao usuário para abrir o arquivo.
- **Não altere** `limpeza2/`, `orquestrador/`, `tests/` nem os documentos do projeto.
  Esta tarefa é só a apresentação.

## 9. Perguntas para fazer ao usuário logo no começo

1. O terceiro benchmark do slide 10: rodar um (qual, e com o custo anunciado) ou
   apresentar só beers e environment?
2. Quais soluções da literatura comparar: as que ele citou (HoloClean, ZeroDC, BClean)
   ou as que `extracao_final.xlsx` tiver com números nos mesmos benchmarks?
3. A figura: sombrear a Figura 4.1 original ou redesenhá-la com as seis etapas e os três
   agentes da implementação?
4. As capturas de tela: ele tira, ou você instala um navegador automatizado?
5. Na entrega: gravar como `- v2.pptx` ao lado do original (padrão deste handoff) ou
   substituir o original?

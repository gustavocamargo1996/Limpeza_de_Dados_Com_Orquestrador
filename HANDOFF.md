# Handoff: da POC 1 para a POC 2

Escrito em 22/09/2026, ao fim da sessão que construiu a POC 1, para a sessão do
Claude que vai abrir esta pasta. Leia junto com o `CLAUDE.md`, que traz os
requisitos de arquitetura e de estilo.

---

## 1. O que o usuário quer

Gustavo Camargo, mestrando no IME, pesquisa o uso de LLMs em limpeza de dados
para estatísticas públicas. Nas palavras dele:

> "eu gostaria de tentar gerar um limpador mais simples e mais efetivo, manter
> a proposta de ter um agente detector de erros, outro que especifica as
> regras de correção e outro que cria o código. Podemos fazer uma estratégia de
> detecção de erros totalmente diferente da atual se necessário, gostaria que
> ele tivesse metade da quantidade de arquivos .py e volume de código do que
> temos hoje."

Em requisitos:

| Requisito | Detalhe |
|---|---|
| **Três agentes** | detector de erros, especificador das regras de correção, gerador do código |
| **Mais efetivo** | a POC 1 é precisa (100%) mas corrige pouco: recall de 24% no `beers` e de 13% no `environment` (seção 3) |
| **Mais simples** | no máximo metade da POC 1: 13 arquivos `.py` e 1.400 linhas (`CLAUDE.md` §2) |
| **Estratégia livre** | a detecção pode ser completamente diferente da POC 1 |
| **Projeto novo** | a POC 1 não pode ser alterada |
| **Limpo dividido em guia e gabarito** | a geração recebe o sujo e, opcionalmente, um guia pequeno: ~20 linhas limpas, para mostrar schema, formatos e relacionamento entre campos, e poucos pares `sujo → limpo` que um humano separaria por inspeção visual. O limpo completo (gabarito) só entra na validação. Detalhes no `CLAUDE.md` §1 |

Sobre o guia, nas palavras dele: "pensando num contexto real, o humano no
máximo iria abrir o dataset e separar alguns erros esdrúxulos identificados
por inspeção visual para gerar a amostra de limpo. Posteriormente na fase de
validação, aí sim para testar o modelo entregaríamos um arquivo de fato limpo
grande."

### O que esta sessão deve fazer primeiro

1. **Brainstorming com base no mapeamento sistemático** (seção 5): levantar
   as melhores estratégias de detecção, especificação e geração de código
   entre os estudos extraídos e propor 2 ou 3 arquiteturas com trade-offs.
2. **Pedir ao usuário os papers ou arquivos** de que precisar para decidir.
   Muitos já estão em texto na pasta do mestrado (seção 5). Ele espera ser
   consultado.
3. Só depois: spec, plano e implementação. O fluxo que funcionou com ele está
   na seção 7.

---

## 2. A POC 1 em uma página

Caminho: `C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados`
(**somente leitura**). Repositório:
`https://github.com/gustavocamargo1996/AgenteLimpezaDeDados`, branch `main`,
commit `4c2f38e`.

**Origem:** a POC 1 se baseia em dois trabalhos do mapeamento, o **ZeroDC**
(S2, *A Zero-Training Data Cleaning System With Large Language Models*) e o
**ZeroEC** (S3, *A Zero-Training Error Correction System with Large Language
Models*). O código do ZeroDC, com os datasets de benchmark, está em
`C:\Users\gusta\projects\Limpeza_de_Dados\ZeroDC`.

**Pipeline** (`limpeza/pipeline.py::gerar_limpador`):

| Etapa | O que faz |
|---|---|
| 1. Carga | lê sujo e limpo como texto literal |
| 2. Amostragem | embeddings MiniLM (ONNX local) + KMeans escolhem ~10 células por coluna; o par `sujo → limpo` delas é o orçamento de rotulagem |
| 3a. Detecção intra-coluna | um agente escreve `detectar(col) -> Series[bool]`; um loop de refino com oráculo (5 iterações) melhora a regra |
| 3b. Detecção por FD | informação mútua sugere determinantes, um agente propõe a dependência funcional, um gate de 100% sobre as células rotuladas aprova, e marca-se quem desvia da moda do grupo |
| 4. Correção em cascata | camada 1: agente especificador (regra em JSON + raciocínio) → agente tradutor (JSON → Python `corrigir(valor)`); camada 2: moda condicionada da FD; o que sobra vira flag. Cada camada só entra se acertar 100% das células rotuladas |
| 5. Empacotamento | escreve o `limpador_*.py` autônomo |
| 6. Métricas | precisão, recall e F1 de detecção e de reparo |

Todo código escrito por LLM passa por um portão AST
(`limpeza/sandbox.py`). `limpeza/llm.py` seleciona OpenAI ou Ollama.

**Tamanho:** 26 arquivos `.py` e 2.810 linhas de produção; 19 arquivos de
teste com 2.768 linhas; 139 testes, nenhum gasta API.

---

## 3. Resultados da POC 1: o placar a bater

Medidos com `avaliar_limpador.py` (F1 de reparo sobre a tabela inteira) nos
limpadores congelados em `tests/fixtures/` da POC 1:

| | `beers` (300 linhas) | `environment` (300 linhas) |
|---|---|---|
| erros na tabela | 495 | 334 |
| células alteradas | 121 | 44 |
| alterações corretas | 121 | 44 |
| **precisão** | **100%** | **100%** |
| **recall** | **24,4%** | **13,2%** |
| **F1** | **39,3%** | **23,3%** |
| flags (marcadas e não resolvidas) | 71 | 663 |

Condições: `gpt-4o-mini`. O `beers` foi um run de 20/08 com 5 iterações de
refino; o `environment` foi um run de 21/09 com todas as colunas. **Para
comparar com a POC 1, use as mesmas fixtures e a mesma definição de métrica.**
A fórmula está em `avaliar_limpador.py`: recall = alterações corretas / erros,
precisão = alterações corretas / alterações.

No `environment`, só `Monitoring_Station_ID` foi corrigida (44/44). As outras
seis colunas com erro ficaram em 0%.

**A comparação favorece a POC 1, e isso deve ser dito ao reportar.** A POC 1
teve mais supervisão do que a POC 2 terá: ~10 células rotuladas por coluna,
sorteadas do limpo completo, mais o que o oráculo rotulou nas 5 iterações de
refino. A POC 2 recebe no máximo o guia (seção 1). Empatar com a POC 1 usando
menos rótulo já é avanço. Reporte o tamanho do guia junto de cada número.

---

## 4. O que a POC 1 ensinou

Cada lição foi medida, não suposta. As âncoras apontam para
`docs/DECISOES.md` da POC 1.

1. **Separar o que a geração vê do que a métrica mede é a base
   metodológica.** Na POC 1 eram três papéis do limpo (orçamento de
   rotulagem, gates, gabarito). Na POC 2 a separação fica mais dura: a geração
   nunca lê o limpo completo, só o guia (`CLAUDE.md` §1).
2. **Gates de 100% dão precisão, mas o problema é o recall.** A POC 1 nunca
   estraga um dado, e corrige pouco.
3. **Detecção valor a valor não alcança erro que depende da linha.** No
   `environment`, 21,5% dos erros são inalcançáveis por uma regra intra-coluna:
   todo valor errado de `State` e de `Climate_Zone` também aparece correto em
   outra linha. No `beers`, 0%. (`#deteccao-por-fd`)
4. **Quando o erro é inalcançável, a regra degenera em "marcar tudo".** No run
   real, o LLM escreveu `^[A-Z]{2}$` para `State` e `Tropical|Temperate` para
   `Climate_Zone`. Cada regra marca as 300 células, porque é a única forma de
   acertar 100% dos erros rotulados. Resultado: 600 flags inúteis.
5. **Uma detecção que marca tudo anula qualquer camada que dependa de linhas
   limpas.** A FD calcula a moda só com linhas não marcadas. Com tudo marcado,
   não sobra referência e a FD acrescentou zero marcas. Com a detecção intra
   vazia, a mesma FD corrige **54/54** erros de `State` e **26/26** de
   `Climate_Zone`. Um sinal forte de que a detecção por contexto de linha
   funciona, desde que não seja envenenada. (`#fd-no-limpador`)
6. **Um gate de 100% passa por vacuidade.** Se nenhuma célula rotulada da
   coluna está errada, qualquer regra acerta 100% delas. Foi o que aprovou a
   FD `City → Climate_Zone`, que nunca foi testada contra um erro.
7. **A correção é gargalo à parte.** `Measurement_Date` teve detecção com
   precisão e recall de 100% e correção de 0%: as 48 células viraram flag.
   `Project_Name` detecta com precisão de 100% e não corrige nada.
8. **Nunca duplique a lógica entre a POC e o limpador gerado.** A POC 1 aplica
   as regras com um código e empacota uma cópia congelada no limpador. As duas
   divergiram, e o run chegou a publicar F1 = 100% numa coluna em que o
   limpador entregue marcava zero. Consertar exigiu um projeto inteiro. Na POC
   2, a métrica é calculada **executando o arquivo gerado** (`CLAUDE.md` §4).
9. **LLM falha por limite de saída.** A correção de `Eco_Status` quebrou com
   `LengthFinishReasonError` (16.384 tokens de completion). Especificação por
   coluna pode estourar; considere saídas curtas e estruturadas.
10. **Congelar um limpador real num teste é a melhor rede de segurança.** Os
    invariantes pegaram regressões que a suíte comum não pegava. Faça isso
    cedo.
11. **Teste sem prova por mutação engana.** Mais de uma vez, um teste verde
    não mordia. A mutação mostrou isso: apagar uma feature inteira deixava 127
    testes verdes.

---

## 5. Material de apoio

### Nesta pasta

| Arquivo | O que é |
|---|---|
| `Qualificacao_Mestrado_Gustavo_Camargo.pdf` | texto de qualificação |
| `extracao_final.xlsx` | formulário de extração do mapeamento (idêntico ao da pasta do mestrado) |

### Pasta do mestrado (tudo o que o usuário tem)

`C:\Users\gusta\OneDrive - Sinapsis Inovação em Energia\Documentos\Gustavo\IME\Mapeamento Data Cleaning LLMs\Claude_Extracao_de_Dados`

| Onde | O que é |
|---|---|
| `04-Proposta_de_Mestrado.tex` | **leia primeiro**: questão de pesquisa, framework proposto, princípios, metodologia e avaliação |
| `03-Revisao_da_Literatura.tex` | o mapeamento escrito |
| `01-Introducao.tex`, `02-Referencial_Teorico.tex` | contexto (estatísticas públicas, Data Mesh) |
| `Fluxograma_Framework_Limpeza_de_Dados.png` | o fluxograma do framework |
| `full_screening/` | os PDFs dos estudos |
| `_txt/` | **os mesmos estudos em texto**: prefira ler daqui |
| `extracao/` | planilhas e JSONs da extração, `RELATORIO.md`, `referencias_selecionados.bib`, `zeroec_extracao.xlsx` |
| `artigo_sbbd/`, `Artigo_SBBD.md` | artigo derivado |

### O framework da dissertação (capítulo 4, resumido)

O limpador da POC 2 é um passo em direção a este framework:

- **Caminho de geração:** um agente gerador de prompt com Chain-of-Thought
  (instruções do responsável + amostra + modelos já aprovados), seguido de um
  agente gerador de código de limpeza.
- **Execução, auditoria e documentação determinísticas**, sem LLM.
- **Aprovação humana** antes de persistir; **reúso** do código aprovado via
  metadados.
- Princípio central, tirado do mapeamento: **converter o conhecimento do LLM
  em código ou regras reexecutáveis**, em vez de chamar o LLM a cada execução.
- Implementação prevista: Python, execução local via **Ollama** (APIs só na
  prototipação), validação com **Pandera**.
- **Avaliação:** datasets **Hospital, Flights, Beers e Rayyan**; baselines
  **HoloClean, Raha+Baran, Cocoon, ZeroEC e BClean+**.

Os três agentes pedidos (detector, especificador, codificador) encaixam aqui:
o especificador faz o papel do gerador de prompt com CoT, e o codificador é o
gerador de código.

### A planilha de extração

Aba `Extracao`: 73 estudos, **51 aprovados** e 22 reprovados (coluna
`Status`), com 39 colunas. As mais úteis para o brainstorming:

- `Abordagem Tecnica Proposta`, `Estrategia de Uso da LLM (descr)`
- `Estrategia LLM (cat)`: Zero-shot, Few-shot, CoT, Rule/Code Generation, Agent-based, Fine-tuning
- `Escopo (cat)`: 32 estudos cobrem detecção + correção
- `Tipo de Dados (cat)`: 34 são tabulares
- `Desafios e Limitacoes`, `Metricas de Avaliacao`, `Resultados Principais`, `Link do Codigo Fonte` (30 têm código)
- Abas `Sumario` (contagens) e `Dicionario` (significado de cada campo)

Para ler (o `.venv` da POC 1 não tem `openpyxl`, e o do Anaconda é antigo
demais para o pandas):

```bash
uv run --no-project --with "openpyxl>=3.1.5" python -c "import openpyxl; ..."
```

**Filtro sugerido para o brainstorming:** estudos aprovados, com dados
tabulares, que fazem detecção + correção ou geram regras/código. Leitura
obrigatória: **ZeroDC (S2)** e **ZeroEC (S3)**, que são a base da POC 1;
**Cocoon (S19)**, **BClean+ (S11)**, **CodeGenWrangler (S17)**, **CatDB
(S13)** e **IterClean (S28)**, citados no framework; e dois estudos só de
detecção que estão em `full_screening/`: **ZeroED** (*Hybrid Zero-Shot Error
Detection Through LLM Reasoning*) e *Zero-Shot Error Detection via
Performance-Guided Rule Generation with LLMs*. Todos esses têm versão em
`_txt/`. O arquivo do Cocoon **não** tem "Cocoon" no nome: é *Data Cleaning
Using Large Language Models*. Para os demais, o nome do arquivo está na coluna
`Arquivo` da planilha.

**Acesso:** a pasta do mestrado fica fora deste projeto. Se a sessão não
conseguir lê-la, peça ao usuário para liberá-la com `/add-dir`.

**Critérios para comparar estratégias** (derivados das seções 1, 3 e 4):
detectam erros que dependem da linha? geram regras ou código reutilizável?
funcionam só com o sujo (zero-shot) e melhoram com um guia pequeno de ~20
linhas e poucos pares (few-shot), **sem** depender de rótulos sorteados do
limpo completo? rodam com modelo local (privacidade)?
reportam resultados em Beers, Hospital, Flights ou Rayyan? cabem em 1.400
linhas?

---

## 6. Ativos reutilizáveis

| O quê | Onde |
|---|---|
| Datasets completos (sujo e limpo) | `C:\Users\gusta\projects\Limpeza_de_Dados\ZeroDC\datasets\` — `beers`, `environment`, `flights`, `hospital`, `rayyan`, `movies`, `imdb`, `food`, `tax-*`, com variantes `_300` e taxas de erro (`flights_10`…`flights_50`, `hospital_10`, `hospital_20`, `rayyan_5`) |
| Fixtures de 300 linhas já validadas | `POC_Limpeza_de_Dados\tests\fixtures\` — `beers_dirty_300.csv`/`beers_clean_300.csv`, `environment_dirty_300.csv`/`environment_clean_300.csv` |
| Limpadores congelados da POC 1 (o placar) | mesma pasta: `limpador_beers_congelado.py`, `limpador_environment_congelado.py` |
| Métrica de reparo | `POC_Limpeza_de_Dados\avaliar_limpador.py` |
| Portão AST para código gerado | `POC_Limpeza_de_Dados\limpeza\sandbox.py` |
| Seletor OpenAI/Ollama | `POC_Limpeza_de_Dados\limpeza\llm.py` |
| Modelo de embeddings MiniLM (ONNX) | `C:\Users\gusta\projects\Limpeza_de_Dados\ZeroDC\all-MiniLM-L6-v2` |
| Chave da OpenAI | no `.env` da POC 1 (`OPENAI_API_KEY`); copie para um `.env` novo, nunca para um arquivo versionado |
| Decisões e o porquê delas | `POC_Limpeza_de_Dados\docs\DECISOES.md` |

Carregue os CSVs sempre como texto literal:
`pd.read_csv(p, dtype=str, keep_default_na=False, na_values=[])`.

---

## 7. Como o usuário gosta de trabalhar

- **Português do Brasil** em tudo, inclusive nas respostas.
- **Processo com as skills do superpowers:** brainstorming (uma pergunta por
  vez, 2 ou 3 abordagens com recomendação, design em seções aprovadas uma a
  uma) → spec em `docs/superpowers/specs/` → plano em
  `docs/superpowers/plans/` → execução com subagent-driven development, com
  ledger, revisão por tarefa e revisão final do branch no modelo mais capaz.
  Ele aprovou esse fluxo em todos os projetos da POC 1.
- **Honestidade acima de tudo.** Ele prefere ouvir que o limpador corrige 13%
  a ouvir um número bonito. Registre resultado desfavorável com a mesma
  clareza do favorável. Nada de rodar de novo até sair um número melhor.
- **Run pago é decisão dele.** Anuncie antes de disparar.
- **Privacidade:** o destino é rodar com dados de estatísticas públicas que
  não podem sair da rede. Por isso o Ollama existe. Na POC 1 ele pediu para
  testar com OpenAI durante a prototipação; confirme antes de assumir o mesmo
  aqui.
- **Merge e push:** só quando ele pedir.

---

## 8. Perguntas em aberto para fazer ao usuário

1. Qual dataset é o alvo principal da POC 2? A dissertação cita Hospital,
   Flights, Beers e Rayyan; a POC 1 usou Beers e Environment.
2. Provedor na prototipação: OpenAI (`gpt-4o-mini`, como na POC 1) ou já
   Ollama? Qual modelo local?
3. **Como produzir o guia nos benchmarks?** Ele precisa ser reprodutível
   (fixado em arquivo e igual entre runs). As opções são o usuário escolher à
   mão, por inspeção visual, as ~20 linhas e os pares de cada dataset (o mais
   fiel ao uso real), ou um procedimento simulado com semente fixa (mais
   rápido, porém menos realista: um sorteio não imita "erros esdrúxulos" vistos
   a olho). Quantos pares? Em que formato (por exemplo, `guia_linhas.csv` com o
   mesmo schema e `guia_pares.csv` com linha, coluna, sujo e limpo)?
   E vale medir também sem guia nenhum, para ver quanto o guia ajuda?
4. A POC 2 terá repositório Git próprio? A POC 1 publica em
   `github.com/gustavocamargo1996/AgenteLimpezaDeDados`.
5. Quais PDFs ou textos ele quer que você leia além da lista sugerida na
   seção 5?

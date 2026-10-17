# Continuação: estado em 12/10/2026

> **Comece por aqui.** Este é o ponto de entrada para quem pega o projeto depois
> desta sessão. Leia na ordem: este arquivo, `CLAUDE.md` (requisitos),
> `docs/REGRAS_DO_LIMPADOR.md` (o limpador vigente, explicado) e
> `docs/DECISOES.md` (as decisões com âncora). A evidência de que a suíte morde
> está em `docs/evidencia/`, e as 43 decisões tomadas durante a execução estão em
> `docs/evidencia/ledger-das-decisoes.md`.

> **Se a sua tarefa é o orquestrador** descrito em
> `docs/especificacoes_do_humano/`, comece por `docs/HANDOFF_ORQUESTRADOR.md`.

Escrito para a próxima sessão, e para mim mesmo depois de a conversa ser
resumida. Leia junto com o `CLAUDE.md` e o `docs/DECISOES.md`.

---

## 1. O que existe e está em `main`

A **parte 2 está implementada, mesclada em `main` e já rodou com API**: os três
agentes, o residual, a espinha e o CLI de geração. Medido: 16 arquivos `.py` fora
de `tests/` (16 de 16, folga zero), 1.798 linhas no total (teto 1.800, folga de 2),
e o maior, `limpeza2/e6_codificador.py`, com 200 linhas, exatamente no teto. A
suíte completa: 295 testes passando. A seção 2 do `CLAUDE.md` declara que isto é
dois terços da POC 1, e não a metade pedida no começo.

**O MVP está guardado** na tag `mvp-poc2-beers` (ver seção 7) e num *bundle* do git
fora da pasta do projeto, em `../backups/`.

| Arquivo | Função |
|---|---|
| `limpeza2/tipos.py` | o que viaja entre etapas |
| `limpeza2/config.py` | modelo, caminhos, limiares, semente |
| `limpeza2/provedor.py` | entrega o cliente do provedor escolhido (`openai`, `ollama`, `gravado`) |
| `limpeza2/portao.py` | valida o Python gerado por LLM antes de deixá-lo rodar |
| `limpeza2/motor.py` | única implementação de aplicação de regra |
| `limpeza2/conformidade.py` | deriva o schema de cada coluna das células certificadas |
| `limpeza2/limites.py` | o que o guia sustenta para uma coluna |
| `limpeza2/e1_perfil.py` | etapa 1: perfila a tabela suja |
| `limpeza2/e2_detector.py` | etapa 2: agente detector |
| `limpeza2/e3_crivo.py` | etapa 3: reprova a regra que não se sustenta (detecção, reparo, residual) |
| `limpeza2/e4_especificador.py` | etapa 4: agente especificador |
| `limpeza2/e5_residual.py` | etapa 5: rodada residual por entidade |
| `limpeza2/e6_codificador.py` | etapa 6: agente codificador e escrita dos artefatos |
| `limpeza2/espinha.py` | a ordem das etapas e o CLI de geração |
| `preparar_guia.py` | sorteia o guia com semente fixa |
| `medir.py` | executa o limpador gerado e mede |

**O modelo mudou para `gpt-6-luna`** com `reasoning_effort="none"`, em 12/10/2026
(`docs/DECISOES.md#provedor`). A POC 1 rodou com `gpt-4o-mini`, então **toda
comparação com o placar dela muda método e modelo ao mesmo tempo**, e a diferença
não se atribui só ao método.

A métrica reproduz o placar da POC 1 exato — `beers` 495/121/121 com recall de
24,4%, `environment` 334/44/44 com 13,2% — e esse teste existe para provar que a
**nossa fórmula está certa**, não porque a POC 1 seja alvo. O usuário foi
explícito: esta POC não é melhoria da POC 1, é resolver bem o problema que ela
resolve mal.

## 2. O guia, como ficou

20 linhas sorteadas de qualquer parte da tabela, **com os valores do CSV limpo**
— um humano pegou algumas linhas e as deixou corretas. Sempre há 20, em qualquer
dataset. Vale 220 células rotuladas, usadas como **oráculo de correção**:

- **Detecção:** a regra não pode marcar célula do guia que já estava certa no
  sujo (`marca_celula_correta`). Marcar célula em que `sujo != guia` é correto.
- **Reparo:** onde o reparo escreveu numa célula do guia, o valor tem de ser o do
  guia (`corrompe_celula_do_guia`). Não escrever não reprova.
- O CLI aceita `--linhas`, `--pares` e `--destino`, e cada pasta tem um
  `guia_receita.txt`. Isso permite medir a curva de supervisão contra recall:
  rodar sem guia, com 10, 20 e 40 linhas.

## 3. Conformidade de schema (IMPLEMENTADA)

**O problema que o usuário identificou, e ele estava certo.** Eu construí um
único juiz para todo tipo de erro e o calibrei com um teto estatístico de
marcação. Para coluna com tipo claro — numérico com uma decimal, inteiro, data —
a pergunta certa não é estatística, é lógica: "este valor obedece ao formato da
coluna?". Roteei um problema fácil por um juiz desenhado para o difícil, e isso
nos custou meia sessão tentando tirar um `℃` de uma coluna numérica.

**O que o mapeamento prescreve**, e os três estudos concordam: inferir o tipo da
coluna primeiro e **derivar a restrição dele**, em vez de pedir predicado livre
ao LLM e policiar por estatística. O **BClean+** usa o LLM só para rotular o tipo
semântico e sintetiza a regex dele — a ablação sem isso derruba o F1 em 0,36 e vai
a **zero** no `flights`. O **CatDB** deriva as regras **deterministicamente** de
um catálogo por coluna e deixa o LLM só traduzir em código. O **Cocoon** põe
caractere e padrão **antes** da dependência funcional, e reporta F1 de 0,99 em
tipo de coluna, onde todos os baselines dão zero.

**A medição que fecha o caso.** Derivei o schema de cada coluna **só das 20
células certificadas do guia**, com o `padrao(v, 2)` (nível 2; hoje o nível é 3) que já existe em
`e1_perfil`, e marquei o que não conforma — sem LLM e sem teto:

| Coluna | padrões no guia | precisão | recall |
|---|---|---|---|
| `beers` `ounces` | 1 — `92` | **1,000** | **1,000** |
| `beers` `state` | 1 — `A2` | **1,000** | **1,000** |
| `beers` `abv` | 2 | 0,972 | **1,000** |
| `beers` `ibu` | 3 | 0,957 | **1,000** |
| `environment` `Temperature` | 3 | **1,000** | **1,000** |
| `environment` `Measurement_Date` | 1 — `94-92-92` | **1,000** | **1,000** |
| `environment` `Monitoring_Station_ID` | 6 | **1,000** | **1,000** |

**634 dos 829 erros dos dois datasets — 76% — detectados deterministicamente**,
com recall de 1,000 e precisão nunca abaixo de 0,957.

**E o método se autodiagnostica.** O número de padrões distintos no guia diz se
ele se aplica: 1 a 6 em 20 amostras significa que a coluna tem schema; 9 a 20
significa texto livre, e aí ele produz lixo — `beer-name` marca 265 células com
precisão **0,000**, `Project_Name` e `Eco_Status` marcam ~270 com precisão 0,2.
O próprio guia avisa para não usar.

**E ele se abstém onde deve.** `State` e `Climate_Zone` têm schema apertado — 1 e
2 padrões — e a conformidade marca **zero**, porque `HH` e `BE` são siglas de
duas letras válidas. São exatamente as colunas que precisam de dependência
funcional, e a abstenção é o sinal de roteamento: schema apertado com zero
violação significa que, se há erro, ele é contextual.

### Correção posterior: o nível do padrão é 3, não 2

A tabela acima é do nível 2, que codifica a quantidade de dígitos: `index` (0 a
299) tem os padrões `9`, `92`, `929`, e 20 linhas amostram algumas larguras, não
todas. O schema ficava sensível a um acidente da amostra. O nível 3 descarta a
contagem, e o argumento independe do gabarito. Implementado em
`motor.NIVEL_SCHEMA = 3`; o corte continua um terço. Medido depois, com o
gabarito, no nível 3: **678 de 829 erros** alcançados, precisão agregada 0,943
(nível 2: 634 e 0,924). Por coluna: `ounces`, `state`, `ibu`, `Temperature`,
`Measurement_Date`, `Monitoring_Station_ID` com 1,000 e 1,000; `abv` 0,972 e
1,000; `city` 0,562 e 1,000 (9 de 9 erros, 16 marcadas); `Project_Name` 0,972 e
0,625, mas o crivo a reprova por `perde_par_do_guia`. `index`, `id`, `brewery_id`,
`PM2.5` e o `index` do `environment` deixam de ser marcadas.

**O custo:** `brewery-name` passa a ter schema com 6 padrões e marca 31 células
com precisão 0,000, e o crivo a aprova. **Opção não aplicada:** corte de um quarto
excluiria `brewery-name` e daria precisão 0,985 com recall de 678 de 829. Não há
argumento independente do gabarito para preferir um quarto, e aplicar seria ajustar
limiar olhando a resposta; fica como decisão do usuário.

### O desenho aprovado pelo usuário, implementado

Implementado em `limpeza2/conformidade.py` (`schema_da_coluna`,
`candidatas_de_conformidade`), no tipo `conformidade` de `motor.py` (com `padrao`
movida para lá) e na exceção do teto em `e3_crivo.py`. Âncora:
`docs/DECISOES.md#conformidade-de-schema`. A espinha chama `candidatas_de_conformidade`
antes do crivo. Reproduziu todos os números
da tabela acima. O problema das colunas sem erro e de largura variável foi resolvido pelo nível 3 (ver acima).

Uma etapa **determinística antes do detector**, no espírito do CatDB:

- Deriva o conjunto de padrões (`padrao(v, 2)`) das células certificadas do guia,
  por coluna.
- A coluna **tem schema** se os padrões distintos forem no máximo **um terço** do
  número de linhas do guia — com 20 linhas, no máximo 6. Limiar *a priori*,
  declarado, separa 6 de 9 nos nossos dados.
- Para coluna com schema, emite uma `Candidata` de tipo novo `conformidade`, com
  os padrões como parâmetro. `motor.detectar` marca a célula cujo padrão não está
  no conjunto.
- **O crivo NÃO aplica o teto de marcação a `conformidade`**, porque a restrição
  veio de dado certificado e não de chute do LLM. Aplica só não-vacuidade e o
  piso do par. Note que `marca_celula_correta` e o veto por valor certificado
  **não podem disparar** nesse tipo, por construção: célula certificada conforma
  ao schema derivado dela mesma. Isso é sinal de que o mecanismo é o certo.
- O LLM passa a ser chamado **só para as colunas que a conformidade não cobre**,
  que são as difíceis — e ali o teto faz sentido, porque o caso é estatístico.
- A **correção** fica com o especificador, que recebe o schema no prompt. Para
  `Temperature` é "tire o sufixo"; para `ounces`, "tire o sufixo e a decimal".

Três decisões de desenho que ficaram em aberto e que eu tomaria assim: a etapa
mora em módulo próprio (`limpeza2/conformidade.py`); o corte é um terço das
amostras; e ela **não** propõe a correção, só detecta.

## 4. O portão da união (REMOVIDO)

Decidido com o usuário e **implementado**: o portão saiu, `taxa_da_uniao` mudou de `limites.py` para `e3_crivo.py` e cada regra que sobrevive guarda `taxa_uniao` em `metricas`. Em `e3_crivo`, quando a
união das máscaras de uma coluna estoura o teto, hoje descarta-se o tipo de maior
taxa. Isso **descarta a regra boa**: ela marca mais justamente porque acha todos
os erros.

Reproduzido com dados reais em `environment` `Temperature`:

```
BOA  formato -?\d+(\.\d+)?        marca 56, todas erradas   precisao 1,000
RUIM ausente_disfarcado, 22 sent. marca 52, 8 erradas       precisao 0,154
uniao = 100 celulas, taxa 0,3333 > teto 0,3236
resultado: SOBREVIVE a RUIM; a BOA sai por uniao_acima_do_teto
```

**A correção:** remover o portão e deixar a taxa da união como **número no
relatório de raciocínio**, não como gate. O buraco que ele fechava — dois tipos
somando e marcando tudo — é menor que o dano que ele causa, e ele não tem como
saber qual regra é boa. Com a conformidade de schema, as colunas de schema não
terão regra do LLM para entrar em união nenhuma, o que reduz ainda mais o caso.

## 5. O limite estrutural, que tem de ser declarado e não escondido

**Precisão é inobservável fora do guia.** O crivo só vê acerto e erro nas 220
células em que tem resposta; fora delas não tem referência. Então ele limita
**quanto** uma regra marca, nunca **quão bem**.

Uma revisão construiu e rodou o ataque: regra com "domínio = valores
certificados mais os mais frequentes, ajustada para ficar logo abaixo do teto"
passa com **precisão 0,000** em colunas limpas (`index`, `id`, `PM2.5`, 30% de
marcação) e **0,41** em `abv` (57%). O veto por valor certificado não protege
porque, em coluna de alta cardinalidade, 20 linhas certificam só 6 a 7% dos
valores — é lista branca de 20 itens. Ele protege bem em coluna de baixa
cardinalidade, onde é menos necessário.

**O que isso custa, e é o alívio:** regra ruim aprovada **piora o limpador** e
não falsifica o número. A medição final roda o limpador gerado contra o gabarito,
então precisão baixa **aparece**. É diferente do defeito que custou um projeto na
POC 1, onde o número publicado estava errado.

**Reportar sempre precisão ao lado de recall**, porque é ali que a degeneração
aparece.

## 6. Pendências menores, registradas e decididas

- O piso de detecção **não** inclui as células sujas do guia, de propósito:
  exigiria que a regra marcasse todas e rejeitaria regra que pega corretamente só
  um dos tipos de erro da coluna.
- A conta `sujo != guia` nas linhas do guia está escrita três vezes.
- A docstring de `_reprovar` diz "cinco testes" e há sete motivos.
- `valores_certificados` ignora os `limpo` de `guia_pares.csv` fora das 20 linhas.
- Empate de taxa entre variantes do mesmo `(coluna, tipo)` depende da ordem da
  lista.
- `limpeza2/__init__.py` foi apagado para abrir a 16ª vaga; não resta vaga livre.

## 7. Os runs pagos, e o que vem depois

Todo degrau pago é **anunciado ao usuário e aprovado por ele antes de disparar**.

1. **Sonda (feita, 12/10/2026).** Uma chamada: o `gpt-6-luna` com
   `reasoning_effort="none"` aceitou o schema JSON estrito, `temperature=0` e `seed`.
   Nenhum plano B foi necessário.
2. **`beers` com guia (feito, 12/10/2026, o MVP).** 31 chamadas, 38,7 mil tokens,
   sem falha nem truncamento. Com holdout de 26 linhas: 445 erros, 438 alterações,
   438 corretas — **precisão 100,0%, recall 98,4%, F1 99,2% pela fórmula da POC 1**.
   A fórmula não conta alteração em coluna sem erro, e houve 6 assim: 5 em
   `brewery-name` (`'Base Camp Brewing Co.'` → `'... Co'`) e 1 em `brewery_id`
   (`95` → `12`, moda condicionada). **Contando-as, precisão 98,6% e F1 98,5%.**
   Quase todo o recall vem da conformidade de schema (336 por `normalizar`, 101 por
   `esvaziar`); o residual acertou 1, e as regras propostas pelo detector LLM não
   acertaram nenhuma célula. Das 31 marcações de `brewery-name`, 26 viraram flag e 5
   foram reescritas errado — e o especificador justificou "não alterar os nomes
   marcados" e escolheu `normalizar` assim mesmo. Os 7 erros de `state` (estados
   vazios) ficaram sem correção. Congelado como invariante:
   `tests/fixtures/limpador_beers_poc2.py`, `tests/fixtures/respostas_beers_poc2.jsonl`
   e `tests/test_invariante.py`; o raciocínio do run está em
   `docs/evidencia/parte-2/run-beers_2026-10-12_2152/`.
3. **`environment` com guia e os dois braços sem guia (feito, 12/10/2026).** 68
   chamadas, sem falha nem truncamento. Medidos com o mesmo holdout do braço com
   guia, para a base de linhas ser a mesma. "P real" conta também as alterações em
   colunas sem erro, que a fórmula da POC 1 ignora.

   | Braço | Erros | Corretas | Alterações | P (POC 1) | P real | Recall | F1 real |
   |---|---|---|---|---|---|---|---|
   | `beers` com guia | 445 | 438 | 438 + 6 | 100,0% | 98,6% | 98,4% | 98,5% |
   | `beers` sem guia | 445 | 43 | 51 + 1 | 84,3% | 82,7% | 9,7% | 17,3% |
   | `environment` com guia | 293 | 217 | 228 | 95,2% | 95,2% | 74,1% | 83,3% |
   | `environment` sem guia | 293 | 47 | 47 + 47 | 100,0% | 50,0% | 16,0% | 24,3% |

   **O guia vale a maior parte do resultado**: sem ele não há conformidade de
   schema, e o recall cai de 98,4% para 9,7% no `beers` e de 74,1% para 16,0% no
   `environment`. No `environment` com guia, `City → State` corrigiu 47 de 47;
   `Project_Name` (51 erros) ficou em zero, porque a conformidade dela é reprovada.
   No `environment` sem guia, a moda condicionada "corrigiu" 47 células de `City`,
   uma coluna sem erro, ao tratar a cidade como determinante com erro de digitação;
   a fórmula da POC 1 mostra 100% de precisão ali, e a real é 50%.

**Por que `state` não foi corrigido no `beers`.** O erro não é de dependência: é
valor deslocado. Nas 9 linhas, a sigla foi parar dentro da cidade
(`city='San Francisco CA'`, `state=''`). Três camadas falharam:
(a) nenhuma estratégia do catálogo escreve numa coluna a partir de outra, então a
conformidade de `city` tira o `' CA'` e o descarta; (b) o especificador escolheu
`moda_condicionada` com determinantes `['brewery-name', 'city']`, e incluir a
própria `city` corrompida faz cada grupo ter uma linha só, então nada é reparado;
(c) com `brewery-name` sozinha, a moda acertaria 5 de 9 sem errar nenhuma, mas o
crivo a reprova por `perde_par_do_guia`, porque os dois pares do guia em `state`
não são reparados. Diagnóstico feito sem API, com o gabarito, só para entender:
não pode virar parâmetro da geração.

Depois vem a **medição nas linhas nunca vistas** (700 de `environment` e 2.110 de
`beers`). Ela fica **fora do plano da parte 2**: exige preparar as fatias a partir
do arquivo completo, renomeando `beer_name`/`brewery_name` para a grafia com hífen,
e isso lê o CSV limpo, então tem de morar fora de `limpeza2/`.

## 8. Como o usuário trabalha

Português do Brasil em tudo. Honestidade acima de número bonito: ele prefere
ouvir que o limpador corrige 13% a ouvir um número inflado. Run pago é decisão
dele, anunciada antes. Merge e push só quando ele pedir — nesta sessão ele pediu
merge local em `main`, sem remoto.

Ele aprovou cada mudança de limiar separadamente, e corrigiu o rumo três vezes de
forma decisiva: tirou a POC 1 do papel de alvo, mandou o guia vir do limpo, e
apontou que conformidade de schema deveria ser a parte fácil. **Nas três ele
estava certo e eu não tinha visto.**

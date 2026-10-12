# As regras do limpador, explicadas

Este documento descreve **o estado vigente** do limpador: o que ele sabe fazer,
como decide que uma célula está errada, como escolhe o valor que põe no lugar, e
onde ele falha. Não exige leitura de código.

Reescrito em 12/10/2026, depois de a conformidade de schema entrar e de o portão
da união sair. É a referência estável do projeto — o
`raciocinio_<dataset>_<carimbo>.md` conta o que aconteceu num run específico,
este documento conta as regras que valem em todos. As decisões e o porquê delas
estão em [`DECISOES.md`](DECISOES.md); o estado do trabalho, em
[`CONTINUACAO.md`](CONTINUACAO.md).

Quando este documento divergir do código, **o código ganha**, e corrigir este
documento faz parte da tarefa que causou a divergência.

---

## 1. O que o limpador é

É um **programa Python autônomo**. Ele não chama nenhum modelo de linguagem
quando roda. Todo o conhecimento que o LLM contribuiu foi convertido, na geração,
em três coisas que vivem dentro do arquivo: **parâmetros de regra** (um conjunto
de padrões, uma lista de valores válidos, um par de colunas), **funções curtas de
normalização** e **dicionários de substituição**.

Ele recebe uma tabela com o mesmo schema da tabela de origem e devolve a tabela
corrigida mais uma **máscara de flags**, que marca as células que ele considerou
erradas e **não** soube corrigir.

Duas consequências que importam desde já.

**O limpador é menos poderoso do que rodar a geração inteira numa tabela nova.**
A geração reperfila a tabela, remina as dependências e consulta o LLM. O limpador
carrega o que foi extraído da tabela de origem: parte viaja para qualquer tabela
da mesma origem (as regras), parte não viaja (o dicionário, que só reconhece
valores sujos que já viu).

**Flag não é sucesso.** Célula marcada e não corrigida conta como recall perdido
na medição. Isso é deliberado: na POC anterior uma coluna teve detecção perfeita
e correção de zero, e os 48 flags dela não valeram nada para o usuário final.

---

## 2. A ordem das coisas

A geração segue dez passos, na ordem em que `limpeza2/espinha.py` os chama, e
nenhum outro lugar guarda essa sequência. O crivo aparece três vezes, porque o
guia confere a regra que detecta, a que repara e o dicionário. Os dois primeiros
passos são **determinísticos, sem LLM** — e é no segundo que está a mudança mais
importante do projeto.

| Passo | O que faz | Usa LLM? |
|---|---|---|
| 1. Perfil | lê o CSV sujo como texto literal e calcula estatísticas por coluna e por par de colunas | não |
| 2. **Conformidade e crivo** | deriva o schema de cada coluna das células que o guia certificou, e o crivo decide se essa regra se sustenta | **não** |
| 3. Detecção | o detector propõe regras para o que a conformidade não cobriu | sim |
| 4. Crivo da detecção | testa cada regra contra a tabela suja e contra o guia, reprova a maioria e, entre variantes do mesmo tipo, fica com a que marca menos | não |
| 5. Especificação | o especificador diz, para cada regra aprovada, como corrigir | sim |
| 6. Funções de correção | o codificador escreve, para cada correção do tipo "normalizar", uma função curta que passa pelo portão de segurança | sim |
| 7. Crivo do reparo | aplica cada correção à tabela suja e reprova a que escreve errado numa célula do guia ou não corrige nada | não |
| 8. Residual | o que nenhuma regra corrigiu vira um dicionário de substituição | sim |
| 9. Crivo do residual | tira do dicionário a troca que contradiz o guia ou mexe num valor que o guia mostra correto | não |
| 10. Arquivos | o codificador escreve o `limpador_*.py` e o relatório de raciocínio, e roda o limpador uma vez para conferir | não |

Depois, numa fase separada que nunca se mistura com a geração, o limpador é
executado e medido contra o CSV limpo.

**Todas as etapas estão implementadas e testadas com um provedor de LLM falso.**
Nenhum run pago foi feito ainda: os números de qualidade do limpador gerado por
LLM real não existem.

---

## 3. O que a geração pode ler

| Artefato | Lê? | Por quê |
|---|---|---|
| CSV sujo | sim | é a entrada |
| `guia_linhas.csv`: 20 linhas que um humano corrigiu | sim | mostra schema, formato, relação entre campos, e serve de oráculo |
| `guia_pares.csv`: poucos pares `sujo → limpo`, até 2 por coluna | sim | mostra que cara tem um erro grosseiro |
| CSV limpo completo (o gabarito) | **nunca** | se vazar, a POC mede memorização e todo número publicado vira ficção |
| `FunctionalDependency.txt` e `TypeConstraint.txt` do benchmark | **nunca** | é conhecimento de especialista; descobrir as dependências é o trabalho da POC |

Dois módulos — `preparar_guia.py` e `medir.py` — são os **únicos** que abrem o
CSV limpo, e ficam fora do pacote `limpeza2/`. Um teste assevera que nenhum
módulo da geração os importa nem cita arquivo `.csv` fora dos dois do guia.

### O guia, e quanto ele supervisiona

São **20 linhas sorteadas de qualquer parte da tabela, com os valores do CSV
limpo**. A imagem é a de um humano que pegou algumas linhas e as **deixou
corretas**, para servir de referência. Sempre há 20, em qualquer tabela.

Isso vale **220 células rotuladas** numa tabela de 11 colunas, e o crivo as usa
como **oráculo de correção**, não só como "não mexa aqui":

- Na detecção, a regra não pode marcar célula do guia que **já estava certa** no
  sujo. Marcar célula em que o sujo difere do guia é **correto**.
- No reparo, onde o reparo escreveu numa célula do guia, o valor tem de ser o do
  guia.

**As linhas do guia saem da medição.** Medir nelas mediria o que o LLM viu.

O tamanho é parâmetro: `preparar_guia.py` aceita `--linhas`, `--pares` e
`--destino`, e cada pasta carrega um `guia_receita.txt` com dataset, semente e
tamanhos. Isso permite medir a curva de supervisão contra recall — sem guia, com
10, com 20, com 40 — sem nunca ficar em dúvida sobre qual guia gerou qual número.

---

## 4. Os seis tipos de erro, do mais fácil ao mais difícil

Esta seção está ordenada por **dificuldade real**, não por ordem de execução,
porque é essa ordenação que explica o desenho.

### 4.1 O caso fácil: `conformidade`, e ele não vem do LLM

Uma coluna de tipo claro — inteiro, numérico com decimal, data, sigla de duas
letras — tem um **formato**, e valor que não obedece ao formato está errado. É
pergunta lógica, não estatística, e não precisa de modelo de linguagem.

**Como o schema é derivado.** Cada um dos 20 valores certificados é generalizado
em classes de caractere, **descartando a contagem**: maiúscula vira `A`,
minúscula `a`, dígito `9`, e o resto fica. Então `2023-02-26` vira `9-9-9`, e
`12`, `16` e `299` viram todos `9`. O conjunto desses padrões **é** o schema, e
ele vem de dado que o humano atestou.

Descartar a contagem não é detalhe. A versão anterior guardava quantos dígitos
cada valor tinha, e isso fazia o schema depender de quais larguras as 20 linhas
sorteadas por acaso incluíram — artefato da amostra, não propriedade da coluna.
Colunas sem erro nenhum, como `index` e `id`, eram marcadas por isso.

**Quando a coluna tem schema.** Se os padrões distintos forem no máximo um terço
das linhas do guia — com 20 linhas, no máximo 6. Acima disso a coluna é texto
livre e o método não se aplica.

Isso torna o mecanismo **autodiagnóstico**: o próprio guia diz se ele serve.

**O teto de marcação não se aplica a este tipo.** A restrição veio de dado
certificado, não de chute: se a coluna está 98% fora do schema, 98% é a verdade.

**O que isso entrega, medido nos dois datasets:**

| Coluna | padrões | precisão | recall | o crivo |
|---|---|---|---|---|
| `beers` `ounces` | 1 | **1,000** | **1,000** | aprova |
| `beers` `ibu` | 2 | **1,000** | **1,000** | aprova |
| `beers` `state` | 1 | **1,000** | **1,000** | aprova |
| `beers` `abv` | 1 | 0,972 | **1,000** | aprova |
| `beers` `city` | 2 | 0,562 | **1,000** | aprova |
| `beers` `brewery-name` | 6 | **0,000** | — | aprova |
| `environment` `Temperature` | 2 | **1,000** | **1,000** | aprova |
| `environment` `Measurement_Date` | 1 | **1,000** | **1,000** | aprova |
| `environment` `Monitoring_Station_ID` | 2 | **1,000** | **1,000** | aprova |
| `environment` `Project_Name` | 3 | 0,972 | 0,625 | **reprova** |
| `environment` `State`, `Climate_Zone` | 1 | — | 0,000 | abstém |

**678 dos 829 erros — 82% — detectados sem LLM e sem teto, com precisão de
0,943.** O `ounces`, que concentra 60% dos erros do `beers`, sai de graça: as
células certificadas são todas `9` e `12.0 oz.` não conforma. No `beers` a
conformidade alcança **todos os 495 erros**; no `environment`, 183 de 334 com
precisão de 0,995.

**E ela se abstém onde deve.** `State` e `Climate_Zone` têm schema apertado e a
conformidade marca **zero**, porque `HH` e `BE` são siglas de duas letras
perfeitamente bem formadas. São exatamente as colunas que precisam de dependência
funcional, e a abstenção é o sinal de roteamento:

| O schema da coluna | O que acontece | Quem resolve |
|---|---|---|
| apertado, **com** violações | caso fácil: os erros estão marcados, sem LLM | `conformidade`; o especificador só diz como corrigir |
| apertado, **sem** violação | se há erro, ele é contextual | a dependência funcional |
| largo, texto livre | o caso difícil | o detector, com teto de marcação |

**Dois custos declarados.** `brewery-name` tem 6 padrões, entra no limite do
corte e marca 31 células **corretas** — precisão zero, e o crivo aprova, porque
não tem como saber. E `Project_Name` detecta 35 dos 56 erros com precisão de
0,972 e é **reprovada** pelo crivo, por perder um par do guia: o piso do par é
tudo-ou-nada, então 35 acertos não chegam ao limpador. Esse segundo caso é uma
tensão de desenho ainda aberta.

### 4.2 Os quatro tipos que o LLM propõe, para o que sobrou

Para as colunas que a conformidade não cobre, o detector propõe parâmetros de um
catálogo fechado. Ele nunca escreve Python aqui — só o parâmetro, de cinco a
vinte tokens.

| Tipo | Parâmetro |
|---|---|
| `formato` | uma regex que o valor válido casa |
| `dominio` | a lista de valores válidos |
| `faixa` | mínimo e máximo |
| `ausente_disfarcado` | a lista de sentinelas (`N/A`, `-`, `?`, vazio) |

**Nota técnica que não é detalhe:** os CSVs são sempre carregados como texto
literal, com `dtype=str, keep_default_na=False, na_values=[]`. Se deixarmos o
pandas interpretar, `'N/A'` vira `NaN` sozinho e a medida mente.

### 4.3 O caso difícil: `dependencia`

Este é o tipo que a POC anterior não conseguia usar, e é a maior aposta de recall
no que sobra.

Uma coluna é **determinada** por outra: sabendo a cidade, sabe-se o estado.
Quando duas linhas concordam nas determinantes e discordam na determinada, uma
delas está errada.

Por que importa: num dos datasets, **21,5% dos erros são invisíveis a qualquer
regra que olhe só a coluna**, porque todo valor errado também aparece correto em
outra linha. Aplicada sozinha, a dependência corrigiu **54 de 54** erros de
`State` e **26 de 26** de `Climate_Zone`.

#### Como a dependência é descoberta

Minerar primeiro, deixar o LLM julgar depois — nunca o contrário. Pedir
dependências ao LLM só pelos nomes das colunas produz plausibilidade sem suporte
nos dados; minerar sem o LLM produz coincidência estatística.

Para cada par ordenado de colunas, a etapa 1 calcula cinco números **só no sujo**:

| Número | O que significa |
|---|---|
| razão de determinação | de 0 a 1: quanto o valor da determinante prevê o da determinada |
| grupos com suporte | quantos valores da determinante aparecem em pelo menos duas linhas |
| **cobertura** | que fração das linhas da tabela vive nesses grupos |
| células divergentes | quantas células da determinada discordam da maioria do seu grupo |
| fração de grupos ambíguos | em quantos grupos não existe maioria clara |

Só os pares com razão alta e cobertura suficiente vão ao LLM, que dá o veredito
semântico: essa dependência faz sentido no mundo real?

#### A cobertura, e por que não basta contar grupos

Este número separa evidência de coincidência, e errá-lo custou uma volta inteira.
A primeira versão exigia um mínimo de **grupos**, e isso rejeita o forte e aceita
o fraco:

| Par | Grupos | Linhas cobertas | Ambíguos |
|---|---|---|---|
| `City → State` | 9 | 300, a tabela inteira | 0% |
| `Temperature → Climate_Zone` | 46 | 105, um terço | 41% |

Nove cidades, cada uma aparecendo umas 33 vezes, são a melhor evidência que uma
tabela de 300 linhas pode dar. Quarenta e seis temperaturas distintas, cobrindo
um terço das linhas e sem maioria clara em 41% dos grupos, são ruído.

#### Os dois limiares são a mesma afirmação

A razão de determinação tem de passar de **0,70**, e isso é o complemento do teto
de marcação de 30% da seção 5. Se o limpador parte do princípio de que nenhuma
coluna está mais de 30% errada, uma dependência verdadeira não pode falhar em
mais de 30% das linhas. A mesma crença, nos dois lugares onde ela tem
consequência.

Isso corrige uma perversidade: **a razão cai justamente porque a coluna tem
erro.** `City → State` tem razão de 0,82 porque 54 das 300 células de `State`
estão erradas. Um limiar alto rejeitaria exatamente a regra que as corrigiria.

#### A fração de grupos ambíguos, e por que ela salva a POC

Uma dependência pode ser estatisticamente forte e metodologicamente inútil. O
caso documentado na literatura: num dataset de voos, o voo determina o horário de
chegada — mas o dado é inconsistente, e o mesmo voo aparece com 22h30 em cinco
linhas, 22h31 em quatro, 22h28 em três e 22h39 em uma. Não há como saber qual é o
verdadeiro. Um sistema publicado aplicou a regra e perdeu desempenho.

Esse perfil é detectável **sem o gabarito**.

#### Qual lado da violação está errado

Por padrão, o erro é atribuído ao **lado determinado**: corrige-se o estado, não
a cidade.

Há uma exceção: se o valor da determinante aparece **uma única vez** na tabela e
existe outro valor de determinante a **uma edição de distância** com um grupo de
verdade, então o erro está na determinante. É o erro de digitação na chave —
`Bosotn` em vez de `Boston`.

Uma edição é a troca, a inserção ou a remoção de um caractere, **ou a troca de
lugar entre dois caracteres vizinhos**. Essa última é a mais comum de todas, e
contá-la como uma edição só é o que faz `Bosotn` ser reconhecido — pela conta
tradicional ele estaria a duas edições e passaria batido.

#### Duas salvaguardas, e por que cada uma existe

**A primeira protege a chave legítima.** O valor errado tem de aparecer **uma
única vez**, e o vizinho **duas ou mais**. Se `Austin` e `Austen` aparecem duas
vezes cada, nenhum é raro e nenhum é corrigido — porque não há como saber qual é
o certo.

**A segunda garante que o resultado não mude entre execuções.** Um valor raro
pode estar a uma edição de **mais de um** vizinho comum. A regra de desempate é:

> entre os vizinhos a uma edição, vence **o mais frequente**; em empate de
> frequência, vence **o primeiro em ordem alfabética**.

Parece detalhe e não é. Sem ordem total explícita, o desempate acabaria decidido
pela ordem interna de uma estrutura de dados, que em Python muda a cada execução
— e a mesma tabela seria limpa de dois jeitos em dias diferentes. Para um
limpador que promete ser reexecutável e auditável, isso é defeito grave, e passou
perto de acontecer.

---

## 5. O crivo: por que a maioria das regras propostas é reprovada

Esta é a parte que mais difere da POC anterior.

Lá, uma regra era aprovada se **acertasse 100% das células rotuladas** daquela
coluna. Dois defeitos fatais:

- Se nenhuma célula rotulada da coluna estava errada, **qualquer** regra acertava
  100% delas. Foi assim que uma dependência foi aprovada sem nunca ter sido
  testada contra um erro. Isso se chama passar por vacuidade.
- Para acertar 100% dos erros rotulados, bastava marcar tudo. Foi o que o LLM
  fez, e o resultado foram 600 flags inúteis — que envenenaram a camada seguinte,
  porque ela precisava de linhas não marcadas como referência.

Aqui a pergunta virou **"a regra viu erro?"**. Cada camada cobre um buraco da
anterior, e cada uma tem um ponto cego. **Dizer onde cada uma falha vale mais que
dizer o que ela pega**, e é por isso que esta tabela tem a última coluna.

| # | Camada | Reprova quando | Onde falha sozinha |
|---|---|---|---|
| 1 | **não-vacuidade** | a regra não marca nenhuma célula do sujo | nada; é piso absoluto |
| 2 | **controle negativo por célula** | marca célula do guia que já estava certa no sujo | coluna cujo guia não tem célula correta |
| 3 | **veto por valor certificado** | marca célula cujo **valor** o guia certificou | só protege coluna de baixa cardinalidade: em coluna de 300 valores distintos, 20 linhas certificam 7% |
| 4 | **teto de marcação por coluna** | marca mais do que a sujeira que o guia sustenta | fica acima de 1 em coluna quase toda errada, e aí está desligado |
| 5 | **piso do guia** | deixa passar célula errada do guia, ou par, na coluna da regra | só cobre as 20 linhas do guia, e é tudo-ou-nada |
| 6 | **ambiguidade**, só para `dependencia` | a fração de grupos sem maioria clara passa do limiar | — |
| 7 | **escolha entre variantes** | entre variantes do mesmo tipo, a que marca mais perde | só protege se o LLM ofereceu variante melhor |

O veto por valor certificado **não se aplica a `dependencia`**, e a razão é
medida: no `environment`, 49 das 54 células erradas de `State` e 26 das 26 de
`Climate_Zone` carregam um valor que o guia certificou em outra linha — são
exatamente os erros contextuais. Nas outras doze colunas dos dois datasets, zero
erro verdadeiro carrega valor certificado. O veto é seguro para os tipos que
julgam o valor, e proibido para o que julga a linha.

A camada 4 **não se aplica a `conformidade`**, pela razão da seção 4.1.

### Como o teto de marcação é calculado

`teto da coluna = max(30%, taxa de sujeira no guia + 2·√(0,25/n))`

Os 30% são *a priori* e **não podem ser calibrados**: olhar a taxa real de erro
por coluna para escolher o número exigiria o gabarito. A parte informada pelo
guia é o que torna colunas muito sujas alcançáveis. A margem é duas vezes o erro
padrão de uma proporção com `n` amostras, então ela **aperta sozinha** quando o
guia cresce: com 20 linhas são 22 pontos, com 40 são 16.

### O portão da união, que existiu e foi removido

Houve uma oitava camada: quando dois tipos de regra na mesma coluna somavam
marcação acima do teto, descartava-se o de maior taxa. **Ela foi removida**, e a
razão merece ficar registrada, porque é instrutiva.

Reproduzido com dados reais em `Temperature`: uma regra de formato marcava 56
células, **todas erradas**, precisão 1,000; uma regra de sentinelas marcava 52,
oito erradas, precisão 0,154. A união estourava o teto, e o crivo descartava **a
regra perfeita** — porque ela marca mais justamente por achar todos os erros. O
critério estava anticorrelacionado com qualidade.

Hoje a taxa da união é **um número no relatório de raciocínio**, para o humano
ver, e não um portão.

---

## 6. As cinco maneiras de corrigir

Aprovada a detecção, o especificador escolhe **como** reparar, de catálogo
fechado.

| Estratégia | O que faz | Exemplo |
|---|---|---|
| `normalizar` | aplica uma transformação de texto ao valor | `22.2℃` vira `22.2`; `12.0 oz.` vira `12` |
| `moda_condicionada` | usa o valor majoritário entre as linhas que concordam nas determinantes | a cidade é Boston, as outras linhas de Boston dizem MA, então o `TX` desta vira `MA` |
| `vizinho_no_dominio` | troca pelo valor mais parecido entre os observados na coluna | `Tropcial` vira `Tropical` |
| `dicionario` | substituição literal, de tabela congelada | `Mass.` vira `Massachusetts` |
| `esvaziar` | troca a ausência disfarçada por vazio de verdade | `N/A` vira `` |

Ordem de preferência, e esta ordem é a resposta ao recall baixo da POC anterior:
primeiro a regra determinística, depois a vizinhança condicionada, depois o
dicionário, e só então a flag.

A `moda_condicionada` é a mais poderosa e roda inteiramente sem LLM dentro do
limpador: ela recalcula a maioria na tabela que estiver sendo limpa. É isso que
faz dela conhecimento que **viaja** para tabelas novas.

Cada estratégia vem com três frases de justificativa — padrão identificado,
análise do erro, transformação — e essas frases vão para o relatório.

Depois de escolhida, a estratégia passa pelo crivo **de novo**. E vale uma regra
nos dois lugares em que o guia é consultado: **onde o reparo escreveu, o valor
tem de estar certo; não escrever não reprova.** Não escrever é falha de alcance,
não corrupção. A versão oposta rejeitava reparo válido, e isso foi descoberto
rodando.

---

## 7. O dicionário residual, e a honestidade sobre ele

Depois de tudo, sobram células detectadas que nenhuma estratégia soube reparar.
Na POC anterior elas viravam flag, e é daí que vinha a maior parte do recall
perdido. O passo 8 faz uma última tentativa, **na geração**, nunca em execução:

1. Junta os **valores distintos** que sobraram, não as células. Cem células com o
   mesmo erro de digitação são um valor, não cem.
2. Monta cada lote de prompt agrupando pela **coluna-sujeito** — a que nomeia a
   entidade principal. Assim o LLM vê, num mesmo prompt, todas as linhas da mesma
   entidade, e enxerga a redundância entre elas.
3. Recebe `{valor_sujo: valor_limpo}` com justificativa por entrada, e `null`
   onde não sabe.
4. Passa pelo crivo: nenhuma entrada pode alterar célula do guia para valor
   diferente do do guia.
5. **É congelado como texto literal dentro do limpador.**

O passo 2 não é detalhe: na literatura, agrupar o prompt pela entidade vale mais
que escolher bem os exemplos — sem o agrupamento, o F1 de um sistema publicado
caiu de 0,595 para 0,164.

### A limitação, dita com clareza

O dicionário é indexado por coluna e por valor sujo. Ele corrige **qualquer linha
futura que repita aquele valor**, e não faz nada com um valor sujo inédito.

Isso significa que **parte do que o limpador sabe é memória, não padrão**. Por
isso a medição acontece em dois lugares e o recall é decomposto por fonte. A
diferença entre os dois números é o tamanho da memorização, e ela é publicada.

O dicionário não é a única memória. O **domínio** da estratégia
`vizinho_no_dominio` — os valores da coluna que aparecem duas ou mais vezes sem
marca, mais os que o guia certifica — também é calculado na tabela de geração e
congelado no limpador. Numa tabela nova, um valor válido que nunca apareceu na de
geração não está nele.

No **braço sem guia**, o dicionário entra no limpador sem filtro nenhum: as três
condições que derrubam uma entrada dependem do guia. Os números desse braço medem,
entre outras coisas, o residual sem supervisão.

---

## 8. Como a qualidade é medida

A métrica é calculada **executando o arquivo gerado**. Nunca por uma
reimplementação paralela. Essa regra existe porque na POC anterior a lógica vivia
em dois lugares, as cópias divergiram, e um run publicou F1 de 100% numa coluna
em que o limpador entregue marcava zero células.

| Medida | Fórmula |
|---|---|
| precisão | alterações corretas ÷ alterações feitas |
| recall | alterações corretas ÷ erros existentes |
| F1 | média harmônica |
| flags | células marcadas e não resolvidas |

As linhas que apareceram no guia são descontadas, e quantas foram é publicado ao
lado de cada número.

**Dois locais, dois números, ambos publicados:**

| Onde se mede | O que significa |
|---|---|
| nas linhas em que o limpador foi gerado | o limpador na tabela de origem |
| nas linhas da mesma tabela que a geração nunca viu | o limpador como **programa**, não como tabela de consulta |

Mais a **decomposição por fonte**: quantas correções vieram de cada tipo de regra
e quantas do dicionário residual.

---

## 9. Os limites conhecidos

Escritos aqui porque omiti-los seria apresentar o método como melhor do que ele é.

**Precisão é inobservável fora do guia.** O crivo só vê acerto e erro nas 220
células em que tem resposta. Fora delas não tem referência. Então ele limita
**quanto** uma regra marca, nunca **quão bem**. Uma regra ajustada para marcar
logo abaixo do teto, evitando as linhas do guia, passa por todas as camadas com
precisão baixa — isso foi construído e rodado, não é hipótese.

O que isso custa é um **limpador pior**, não um número falso: a medição final roda
o artefato contra o gabarito, então precisão baixa **aparece**. É diferente do
defeito que custou um projeto na POC anterior, onde o número publicado estava
errado. **Reportar sempre precisão ao lado de recall**, porque é ali que a
degeneração se mostra.

**A conformidade erra em coluna de texto no limite do corte.** `brewery-name` tem
6 padrões em 20 amostras, entra como schema e marca 31 células corretas. Apertar
o corte de um terço para um quarto resolveria e levaria a precisão a 0,985, mas
não há argumento independente do gabarito para escolher um quarto — então o corte
fica em um terço e o falso positivo fica declarado.

**O piso do guia é tudo-ou-nada.** `Project_Name` detecta 35 dos 56 erros com
precisão de 0,972 e é reprovada por perder **um** par do guia. Trocar o veto por
penalidade é uma decisão de desenho aberta.

**O guia cobre 20 das 300 linhas.** Toda proteção que depende dele é cega ao que
acontece fora dessas linhas.

**O limpador roda sem o portão de segurança** na máquina do usuário, por desenho,
e o cabeçalho dele avisa. O portão existe para proteger a máquina de quem **gera**.

---

## 10. De onde cada peça veio

| Peça | Origem |
|---|---|
| derivar a restrição do tipo da coluna, em vez de pedir predicado ao LLM | **BClean+**, que sintetiza regex do tipo semântico; **CatDB**, que deriva regras deterministicamente de um catálogo |
| decomposição em tipos de erro, com padrão antes de dependência funcional | **Cocoon** |
| minerar dependências no sujo e o LLM dar o veredito semântico | **Cocoon** |
| perfil por coluna: frequência de valor e de padrão em níveis | **ZeroED** e **IterClean** |
| pedir ao LLM o parâmetro da regra, não código nem valor corrigido | **ZeroEC** |
| justificativa em três frases: padrão, análise do erro, transformação | **ZeroEC** |
| três variantes da mesma regra, escolhidas por desempenho | **ZeroEC** |
| a regra não pode corromper célula limpa | **ZeroEC** |
| agrupar o lote residual pela coluna que nomeia a entidade | **IterClean** |
| decidir qual lado da violação está errado | versão barata do **BClean+** |
| `try/except` com sentinela e voto entre funções | **CodeGenWrangler** |
| metadados de coluna em uma linha, para o prompt ficar curto | **CatDB** |
| **o schema derivado das células que o humano certificou** | **nosso** |
| **a regra tem de disparar em pelo menos uma célula** | **nosso**, contra a vacuidade da POC anterior |
| **teto de marcação informado pelo guia** | **nosso** |
| **veto por valor certificado** | **nosso** |
| **residual congelado como dicionário em vez de chamada em execução** | inversão do **ZeroEC**, exigida pelo princípio de converter conhecimento em artefato reexecutável |
| **medir executando o arquivo gerado** | lição da POC anterior |
| **uma única implementação da aplicação de regra, copiada byte a byte** | **nosso**, pela mesma lição |

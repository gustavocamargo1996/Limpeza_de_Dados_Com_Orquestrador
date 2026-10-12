# As regras do limpador, explicadas

Este documento explica, sem exigir leitura de código, **o que o limpador gerado
sabe fazer, por que ele decide que uma célula está errada e como ele escolhe o
valor que coloca no lugar**. É a referência estável do projeto: o
`raciocinio_<dataset>_<carimbo>.md` conta o que aconteceu num run específico,
este documento conta as regras que valem em todos.

Quando este documento divergir do código, **o código ganha**, e corrigir este
documento faz parte da tarefa que causou a divergência.

---

## 1. O que o limpador é, e o que ele não é

O limpador é um **programa Python autônomo**. Ele não chama nenhum modelo de
linguagem quando roda. Todo o conhecimento que o LLM contribuiu foi convertido,
na geração, em três coisas que vivem dentro do arquivo: **parâmetros de regra**
(uma expressão de formato, uma lista de valores válidos, um par de colunas),
**funções curtas de normalização** e **dicionários de substituição**.

Ele recebe uma tabela com o mesmo schema da tabela de origem e devolve duas
coisas: a tabela corrigida e uma **máscara de flags**, que marca as células que
ele considerou erradas e **não** soube corrigir.

Duas consequências que importam entender desde já:

**O limpador é menos poderoso do que rodar a geração inteira numa tabela nova.**
A geração reperfila a tabela, remina as dependências entre colunas e consulta o
LLM. O limpador carrega o que foi extraído da tabela de origem. Parte desse
conhecimento viaja para qualquer tabela da mesma origem (as regras), e parte não
viaja (o dicionário de substituição, que só reconhece valores sujos que já
apareceu).

**Flag não é sucesso.** Uma célula marcada e não corrigida conta como recall
perdido na medição. Isso é deliberado: a POC 1 teve uma coluna com detecção
perfeita e correção de zero, e os 48 flags dela não valeram nada para o usuário
final.

---

## 2. O passo a passo da geração

São seis etapas, nesta ordem. As etapas 1 e 3 são determinísticas; as outras
quatro usam LLM.

| Etapa | O que faz | Usa LLM? |
|---|---|---|
| 1. Perfil | lê o CSV sujo como texto literal e calcula estatísticas por coluna e por par de colunas | não (exceto uma chamada para escolher a coluna-sujeito) |
| 2. **Detecção** | o agente detector propõe, por coluna, regras que dizem onde estão os erros | sim |
| 3. Crivo | testa cada regra proposta contra a tabela suja e contra o guia, e reprova a maioria | não |
| 4. **Especificação** | o agente especificador diz, para cada regra aprovada, como corrigir | sim |
| 5. **Residual** | o que nenhuma regra corrigiu vira um dicionário de substituição | sim |
| 6. **Codificação** | o agente codificador escreve o arquivo `limpador_*.py` e o relatório de raciocínio | sim |

Depois, numa fase separada que nunca se mistura com a geração, o limpador é
executado e medido contra o CSV limpo.

---

## 3. O que a geração pode ler, e o que é proibido

| Artefato | A geração lê? | Por quê |
|---|---|---|
| CSV sujo | sim | é a entrada |
| `guia_linhas.csv`: 20 linhas que um humano confirmou estarem corretas | sim | mostra schema, formato de cada campo e como os campos se relacionam |
| `guia_pares.csv`: poucos pares `sujo → limpo`, até 2 por coluna | sim | mostra que cara tem um erro grosseiro |
| CSV limpo completo (o gabarito) | **nunca** | se vazar, a POC mede memorização e todo número publicado vira ficção |
| `FunctionalDependency.txt` e `TypeConstraint.txt` do benchmark | **nunca** | são conhecimento de especialista; descobrir as dependências é justamente o trabalho da POC |
| `real_examples.txt` do benchmark | **nunca** | o guia é sempre o nosso, sorteado com semente fixa |

As linhas que aparecem no guia **saem da medição**. Medir nelas mediria o que o
LLM viu, não o que ele generalizou.

### Quantas linhas o guia tem de verdade

As 20 linhas são o que se pede, não o que sempre se consegue. O guia só aceita
linhas em que **nenhuma** célula está errada, e há tabelas em que isso é raro.
Medido nos dois datasets em uso:

| Dataset | Linhas sem erro nenhum, em 300 | Por quê |
|---|---|---|
| `environment` | 85 | os erros se espalham por sete colunas, e a maioria das linhas tem um ou dois |
| `beers` | **5** | a coluna `ounces` está errada em 295 das 300 linhas, então quase toda linha tem ao menos esse erro |

Então o guia do `beers` sai com 5 linhas, não 20. Isso não é defeito: é o que um
humano também encontraria ao procurar linhas impecáveis numa tabela cuja coluna
principal está quase toda errada. O efeito prático é que **no `beers` o controle
negativo é fraco** — cinco linhas vezes onze colunas dão 55 células em que a
regra não pode mexer. Os outros três testes do crivo não dependem dessas linhas,
então a proteção não desaparece; ela afina.

O tamanho real do guia é publicado junto de cada número, sempre.

---

## 4. Os cinco tipos de erro que o limpador reconhece

O catálogo é **fechado**: o detector escolhe entre estes cinco e não inventa um
sexto. A ordem é de abrangência crescente — primeiro o que se vê no caractere,
depois o que se vê no padrão, depois a ausência, e por último o que só se vê
olhando outras colunas da mesma linha.

### 4.1 `formato`

A coluna tem uma forma esperada, e o valor que fugir dela está errado.

O detector emite uma expressão de formato. Exemplo real da POC 1, na coluna
`ounces` do `beers`: valores como `12.0` onde o correto é `12`.

**Cuidado conhecido.** Este é o tipo que mais degenera. No `environment` da POC
1, o LLM escreveu `^[A-Z]{2}$` para a coluna `State`, o que marca as 300 células
da coluna, porque era a única forma de "acertar" todos os erros rotulados. O
crivo (seção 5) existe principalmente por causa disso.

### 4.2 `dominio`

A coluna só admite valores de um conjunto pequeno e conhecido. Quem estiver fora
está errado.

Exemplo: `Climate_Zone` admite um punhado de zonas climáticas. Valor fora da
lista é erro.

### 4.3 `faixa`

A coluna é numérica e tem mínimo e máximo plausíveis. Fora da faixa, erro.

### 4.4 `ausente_disfarcado`

O valor existe na célula mas significa ausência: `N/A`, `-`, `?`, `unknown`,
`null` escrito como texto, string vazia. São ausências fantasiadas de dado.

É um tipo que os benchmarks clássicos quase não pontuam, e que o Cocoon mostrou
valer muito: nos cenários de ausência disfarçada e tipo de coluna, os sistemas
clássicos ficam em F1 zero.

**Nota técnica importante:** por isso os CSVs são sempre carregados como texto
literal, com `dtype=str, keep_default_na=False, na_values=[]`. Se deixarmos o
pandas interpretar, `'N/A'` vira `NaN` sozinho e a medida mente.

### 4.5 `dependencia`

Este é o tipo que a POC 1 não conseguia usar, e é a maior aposta de recall.

Uma coluna é **determinada** por uma ou mais outras: sabendo a cidade, sabe-se o
estado. Quando duas linhas concordam nas colunas determinantes e discordam na
determinada, uma das duas está errada.

Por que isso importa tanto: no `environment` da POC 1, **21,5% dos erros são
invisíveis a qualquer regra que olhe só a coluna**, porque todo valor errado de
`State` e de `Climate_Zone` também aparece correto em outra linha. Não existe
formato nem domínio que os separe. Quando a dependência foi aplicada sozinha,
ela corrigiu **54 de 54** erros de `State` e **26 de 26** de `Climate_Zone`.

#### Como a dependência é descoberta

Minerar primeiro, deixar o LLM julgar depois — nunca o contrário. Pedir
dependências ao LLM só pelos nomes das colunas produz plausibilidade sem
suporte nos dados; minerar sem o LLM produz coincidências estatísticas.

Para cada par ordenado de colunas, a etapa 1 calcula quatro números **só na
tabela suja**:

| Número | O que significa |
|---|---|
| razão de determinação | de 0 a 1: quanto o valor da coluna determinante prevê o da determinada |
| número de grupos com suporte | quantos valores da determinante aparecem em pelo menos duas linhas |
| **cobertura** | que fração das linhas da tabela vive nesses grupos |
| células divergentes | quantas células da determinada discordam da maioria do seu grupo |
| fração de grupos ambíguos | em quantos grupos não existe maioria clara |

Só os pares com razão alta e cobertura suficiente vão ao LLM, que dá o veredito
semântico: essa dependência faz sentido no mundo real?

#### A cobertura, e por que não basta contar grupos

Este é o número que separa evidência de coincidência, e errá-lo custou uma volta
inteira neste projeto. A primeira versão exigia um mínimo de **grupos**, e isso
rejeita o forte e aceita o fraco:

| Par | Grupos | Linhas cobertas | Ambíguos |
|---|---|---|---|
| `City → State` | 9 | 300, a tabela inteira | 0% |
| `Temperature → Climate_Zone` | 46 | 105, um terço | 41% |

Nove cidades, cada uma aparecendo umas 33 vezes, são a melhor evidência que uma
tabela de 300 linhas pode dar sobre uma dependência. Quarenta e seis temperaturas
distintas, cobrindo um terço das linhas e sem maioria clara em 41% dos grupos,
são ruído. Contar grupos premiava o segundo e barrava o primeiro.

#### Os dois limiares são a mesma afirmação

A razão de determinação tem de passar de **0,70**, e isso não é um número solto:
é o complemento do teto de marcação de 30% da seção 5. Se o limpador parte do
princípio de que nenhuma coluna está mais de 30% errada, então uma dependência
verdadeira não pode falhar em mais de 30% das linhas. A mesma crença, escrita nos
dois lugares onde ela tem consequência.

Isso também corrige uma perversidade: **a razão de determinação cai justamente
porque a coluna tem erro.** `City → State` tem razão de 0,82 porque 54 das 300
células de `State` estão erradas. Um limiar alto rejeitaria exatamente a regra que
corrigiria esses 54 erros.

#### A fração de grupos ambíguos, e por que ela salva a POC

Uma dependência pode ser estatisticamente forte e metodologicamente inútil. O
caso que o Cocoon documenta: no dataset `flights`, o voo determina o horário de
chegada — mas o próprio dado original é inconsistente, e o mesmo voo aparece com
22h30 em cinco linhas, 22h31 em quatro, 22h28 em três e 22h39 em uma. Não há
como saber qual é o verdadeiro. O Cocoon aplicou a regra e perdeu desempenho
nesse dataset.

Esse perfil — muitos grupos sem maioria clara — é detectável **sem o gabarito**.
É o teste 5 do crivo.

#### Qual lado da violação está errado

Por padrão, o erro é atribuído ao **lado determinado**: corrige-se o estado, não
a cidade.

Há uma exceção, e ela recupera erros que a regra orientada perderia: se o valor
da coluna determinante aparece **uma única vez** na tabela e existe outro valor
de determinante a **uma edição de distância** com um grupo de verdade, então o
erro está no determinante. É o caso do erro de digitação na chave — `Bosotn` em
vez de `Boston`. Aí se corrige o determinante e se deixa o determinado em paz.

Uma edição é a troca, a inserção ou a remoção de um caractere, **ou a troca de
lugar entre dois caracteres vizinhos**. Essa última é a mais comum de todas, e
contá-la como uma edição só é o que faz `Bosotn` ser reconhecido como `Boston` —
pela conta tradicional ele estaria a duas edições e passaria batido.

#### Duas salvaguardas, e por que cada uma existe

**A primeira protege a chave legítima.** O valor errado tem de aparecer **uma
única vez** na coluna, e o vizinho tem de aparecer **duas ou mais**. Se `Austin`
e `Austen` aparecem duas vezes cada, nenhum dos dois é raro, e nenhum é corrigido
para o outro — porque não há como saber qual é o certo. Sem essa condição, o
limpador passaria a reescrever valores válidos e frequentes, que é o oposto do
que ele promete.

**A segunda garante que o resultado não mude entre execuções.** Um valor raro
pode estar a uma edição de **mais de um** vizinho comum. `Bostn` está a uma
edição de `Boston` e de `Bostan`. A regra de desempate é:

> entre os vizinhos a uma edição, vence **o mais frequente**; em empate de
> frequência, vence **o primeiro em ordem alfabética**.

Então com `Boston` três vezes e `Bostan` duas, sai `Boston`, pela frequência.
Com os dois aparecendo duas vezes, sai `Bostan`, porque `a` vem antes de `o`.

Essa regra parece detalhe e não é. Sem uma ordem total explícita, o desempate
acabaria decidido pela ordem interna de uma estrutura de dados, que em Python
muda a cada execução do programa — e a mesma tabela seria limpa de dois jeitos
em dias diferentes. Para um limpador cujo propósito é ser reexecutável e
auditável, isso é defeito grave, e passou perto de acontecer.

---

## 5. O crivo: por que a maioria das regras propostas é reprovada

Esta é a parte mais importante do documento, e a que mais difere da POC 1.

Na POC 1, uma regra era aprovada se **acertasse 100% das células rotuladas**
daquela coluna. Dois defeitos fatais:

- Se nenhuma célula rotulada da coluna estava errada, **qualquer** regra acertava
  100% delas. Foi assim que a dependência `City → Climate_Zone` foi aprovada sem
  nunca ter sido testada contra um erro. Isso se chama passar por vacuidade.
- Para acertar 100% dos erros rotulados, bastava marcar tudo. Foi o que o LLM
  fez, e o resultado foram 600 flags inúteis.

Aqui, uma regra candidata é **executada na tabela suja inteira** e precisa
passar por cinco testes. Nenhum deles consulta o gabarito.

| # | Teste | A regra é reprovada quando | O que isso impede |
|---|---|---|---|
| 1 | **controle negativo** | ela marca ou altera qualquer célula das 20 linhas que o humano disse estarem corretas | regra que estraga dado bom |
| 2 | **não-vacuidade** | ela não marca nenhuma célula da tabela suja | regra que nunca viu um erro ser aprovada no silêncio |
| 3 | **teto de marcação** | ela marca mais que 30% da coluna | a regra "marca tudo" |
| 4 | **piso do guia** | existem pares `sujo → limpo` naquela coluna e ela não marca todos | regra que ignora o erro que o humano apontou |
| 5 | **ambiguidade** | só para `dependencia`: a fração de grupos sem maioria clara passa do limiar | a dependência do tipo `flights` |

O teste 2 é a inversão metodológica central: **o gate não pergunta mais "a regra
deixou de errar?", pergunta "a regra viu erro?"**. O número de células que cada
regra marcou entra no relatório de raciocínio, inclusive o zero, para a
vacuidade ficar visível em vez de silenciosa.

Em coluna sem par no guia, o teste 4 simplesmente não se aplica, e os testes 1,
2 e 3 decidem sozinhos. Era exatamente aí que o gate da POC 1 ficava vazio.

Três variantes de cada regra são geradas, e entre as que sobrevivem fica a de
**menor taxa de marcação** que ainda passa no piso. É a escolha conservadora, e é
explicável numa frase.

Os cinco tipos de erro coexistem na mesma coluna: a máscara final é a união.

### Sobre o teto de 30%

Esse número **não foi calibrado, e não pode ser**. Olhar a taxa real de erro de
cada coluna para escolher o teto seria ler o gabarito. Ele está fixado a priori,
acima da taxa de erro por coluna dos datasets em uso e muito abaixo do que
permitiria marcar uma coluna inteira.

Consequência declarada: numa tabela em que alguma coluna tenha mais de 30% de
erro, o limpador vai subdetectar essa coluna. É um limite conhecido do método,
não um defeito a consertar escolhendo um número mais bonito.

---

## 6. As cinco maneiras de corrigir

Aprovada a detecção, o especificador escolhe **como** reparar, também de um
catálogo fechado.

| Estratégia | O que faz | Exemplo |
|---|---|---|
| `normalizar` | aplica uma transformação de texto ao valor | `12.0` vira `12`; data em três formatos vira ISO |
| `moda_condicionada` | olha as outras linhas que concordam nas colunas determinantes e usa o valor majoritário da coluna-alvo | a cidade é Boston, as outras linhas de Boston dizem MA, então o `TX` desta linha vira `MA` |
| `vizinho_no_dominio` | troca o valor pelo mais parecido entre os valores observados na coluna | `Tropcial` vira `Tropical` |
| `dicionario` | substituição literal, consultada numa tabela congelada | `Mass.` vira `Massachusetts`, porque não há padrão que derive um do outro |
| `esvaziar` | troca a ausência disfarçada por vazio de verdade | `N/A` vira `` |

Ordem de preferência, e esta ordem é a resposta ao recall de 24%: primeiro a
regra determinística, depois a vizinhança condicionada, depois o dicionário, e
só então a flag.

A `moda_condicionada` é a mais poderosa e a que roda inteiramente sem LLM dentro
do limpador: ela recalcula a maioria na tabela que estiver sendo limpa. Isso é o
que faz dela conhecimento que **viaja** para tabelas novas.

Cada estratégia vem com três frases de justificativa do LLM — padrão
identificado, análise do erro, transformação — e essas frases vão para o
relatório de raciocínio.

Depois de escolhida, a estratégia passa pelo crivo **de novo**: ela não pode
alterar nenhuma célula das linhas limpas do guia, tem de reproduzir os pares
`sujo → limpo` daquela coluna, e tem de reparar pelo menos uma célula detectada.

---

## 7. O dicionário residual, e a honestidade sobre ele

Depois de tudo isso, sobram células que o limpador detectou como erradas e que
nenhuma estratégia soube reparar. Na POC 1, elas viravam flag — e é daí que vem
a maior parte do recall perdido.

A etapa 5 faz uma última tentativa, **na geração**, nunca em execução:

1. Junta os **valores distintos** que sobraram, não as células. Cem células com
   o mesmo erro de digitação são um valor, não cem.
2. Monta cada lote de prompt agrupando pela **coluna-sujeito** — a coluna que
   nomeia a entidade principal da tabela. Assim o LLM vê, num mesmo prompt,
   todas as linhas da mesma entidade, e enxerga a redundância entre elas.
3. Recebe `{valor_sujo: valor_limpo}` com uma justificativa por entrada, e
   `null` onde o LLM não sabe.
4. Passa pelo crivo: nenhuma entrada pode alterar célula limpa do guia.
5. **É congelado como texto literal dentro do limpador.**

O passo 2 não é detalhe. A ablação do IterClean mostra que agrupar o prompt pela
entidade vale mais que escolher bem os exemplos: sem o agrupamento, o F1 do
`flights` cai de 0,595 para 0,164.

### A limitação, dita com clareza

O dicionário é indexado por coluna e por valor sujo. Ele corrige **qualquer
linha futura que repita aquele valor sujo**, e não faz nada com um valor sujo
inédito.

Isso significa que **parte do que o limpador sabe é memória, não padrão**. Por
isso a medição acontece em dois lugares (seção 8) e o recall é decomposto por
fonte. A diferença entre os dois números é o tamanho da memorização, e ela é
publicada, não escondida.

---

## 8. Como a qualidade é medida

A métrica é calculada **executando o arquivo gerado**. Nunca por uma
reimplementação paralela da lógica. Essa regra existe porque na POC 1 a lógica
vivia em dois lugares, os dois divergiram, e um run publicou F1 de 100% numa
coluna em que o limpador entregue marcava zero células.

| Medida | Fórmula |
|---|---|
| precisão | alterações corretas ÷ alterações feitas |
| recall | alterações corretas ÷ erros existentes |
| F1 | média harmônica das duas |
| flags | células marcadas e não resolvidas |

As linhas que apareceram no guia são descontadas, e quantas foram descontadas é
publicado ao lado de cada número.

**Dois locais, dois números, ambos publicados:**

| Onde se mede | O que o número significa |
|---|---|
| nas linhas em que o limpador foi gerado | o limpador na tabela de origem; é o número comparável ao placar da POC 1 |
| nas linhas da mesma tabela que a geração nunca viu | o limpador como **programa**, não como tabela de consulta |

E a **decomposição por fonte**: quantas correções vieram de cada tipo de regra e
quantas vieram do dicionário residual.

### Sobre comparar com a POC 1 e com os papers

A comparação com a POC 1 **favorece a POC 1**, e isso precisa ser dito sempre
que os números forem reportados. A POC 1 recebeu cerca de 10 células rotuladas
por coluna, sorteadas do limpo completo, mais tudo o que um oráculo rotulou em
cinco iterações de refino. Esta POC recebe, no máximo, 20 linhas limpas e dois
pares por coluna. **Empatar usando menos rótulo já é avanço.** O tamanho do guia
vai ao lado de cada número.

Os números dos papers não são alvo comparável:

- O ZeroDC reporta F1 de 1,00 em Hospital e Beers, mas cerca de 60% do resultado
  dele vem de um laço de 10 anotações humanas por coluna que, no código
  publicado, são simuladas lendo o arquivo limpo.
- CodeGenWrangler e CatDB validam o código gerado contra conjuntos rotulados
  grandes.
- O ZeroEC chama o LLM célula a célula no residual, em tempo de execução, o que
  entrega mais recall ao custo de não produzir artefato reexecutável.

Nenhum desses sinais de validação está disponível aqui, por escolha
metodológica.

---

## 9. De onde cada peça veio

| Peça | Origem |
|---|---|
| decomposição em tipos de erro, em ordem fixa | Cocoon |
| minerar dependências no sujo e o LLM dar o veredito semântico | Cocoon |
| perfil por coluna: frequência de valor, de vizinhança e de padrão em três níveis | ZeroED e IterClean |
| pedir ao LLM o parâmetro da regra, não código nem valor corrigido | ZeroEC |
| justificativa em três frases: padrão, análise do erro, transformação | ZeroEC |
| três variantes da mesma regra, escolhidas por desempenho | ZeroEC |
| a regra não pode corromper célula limpa | ZeroEC |
| **a regra tem de disparar em pelo menos uma célula** | nosso, em resposta à lição 6 da POC 1 |
| **teto de marcação** | nosso, em resposta à lição 4 da POC 1 |
| **residual congelado como dicionário em vez de chamada em execução** | inversão do ZeroEC, exigida pelo princípio de converter conhecimento em artefato reexecutável |
| agrupar o lote residual pela coluna que nomeia a entidade | IterClean |
| decidir qual lado da violação está errado | versão barata do BClean+ |
| `try/except` com sentinela e voto entre funções | CodeGenWrangler |
| metadados de coluna em uma linha, para o prompt ficar curto | CatDB |
| **medir executando o arquivo gerado** | lição 8 da POC 1 |
| **uma única implementação da aplicação de regra, copiada byte a byte para o limpador** | nosso, em resposta à lição 8 |

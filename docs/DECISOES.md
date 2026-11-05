# Decisões

Uma entrada por decisão que o código não explica sozinho. As âncoras são citadas
em comentários e docstrings, para o código ficar curto sem ficar misterioso.

---

## Catálogo fechado em vez de Python livre {#catalogo-fechado}

**Decisão.** O detector e o especificador escolhem entre cinco tipos de erro e
cinco estratégias de reparo, e emitem só os parâmetros. Não escrevem Python.

**Por quê.** Duas razões medidas. A primeira é tamanho de saída: na POC 1 a
especificação de `Eco_Status` quebrou com `LengthFinishReasonError` aos 16.384
tokens de completion, porque pedia a correção ao LLM. Um parâmetro de regra tem
de 5 a 20 tokens — uma dependência é `["State","Measure"]`. A segunda é o
portão: código livre do LLM amplia a superfície que a análise de AST precisa
cobrir.

**Alternativa recusada.** População de funções Python livres com loop evolutivo,
como o estudo de geração de regra guiada por desempenho. Vale de 0,10 a 0,20 de
F1 nos números deles, mas multiplica as chamadas de API e a variância entre
runs, o que atrapalha o teste de invariante.

**Consequência.** Erro que não cabe em nenhum dos cinco tipos é invisível ao
limpador. Ampliar o catálogo é decisão consciente, com medição antes e depois.

---

## A regra vê a linha, não a célula {#regra-sobre-a-linha}

**Decisão.** Todo predicado é avaliado sobre o DataFrame e devolve uma máscara
booleana, nunca sobre um valor escalar isolado.

**Por quê.** No `environment` da POC 1, 21,5% dos erros são inalcançáveis por
regra intra-coluna: todo valor errado de `State` e de `Climate_Zone` também
aparece correto em outra linha. O estudo de geração de regra guiada por
desempenho usa assinatura por célula e os próprios autores listam isso como
limitação.

**Exceção.** As funções de normalização escritas pelo LLM são escalares,
`corrigir(valor) -> str`. É o único Python que o LLM escreve, e ser escalar é o
que permite executá-las sem pandas no namespace do portão.

---

## O gate pergunta "a regra viu erro?" {#crivo-sem-vacuidade}

**Decisão.** Cinco testes determinísticos, nenhum consultando o gabarito:
controle por célula do guia, não-vacuidade, teto de marcação,
piso dos pares do guia, e fração de grupos ambíguos para dependências.

**Por quê.** O gate da POC 1 aprovava uma regra que acertasse 100% das células
rotuladas, e tinha dois modos de falha. Passava por vacuidade quando nenhuma
célula rotulada da coluna estava errada — foi assim que a dependência
`City → Climate_Zone` foi aprovada sem nunca ter visto um erro (lição 6). E
premiava marcar tudo: `^[A-Z]{2}$` em `State` marcava as 300 células porque era
a única forma de cobrir todos os erros rotulados (lição 4).

**Com guia pequeno o gate antigo seria pior**, não melhor: há poucos pares,
escolhidos por serem erros grosseiros, então a maioria das colunas não teria par
nenhum e passaria por vacuidade.

---

## O teto de marcação tem piso a priori e sobe com o guia {#teto-de-marcacao}

**Decisão.** O teto da coluna é `max(TETO_MARCACAO, taxa_suja_no_guia + 2 * sqrt(0,25 / n))`,
em `e3_crivo.teto_da_coluna`. `TETO_MARCACAO = 0,30` continua em `config.py`,
escolhido sem olhar os dados, e agora é o **piso**. `taxa_suja_no_guia` é a
fração das `n` linhas do guia em que `sujo != guia` naquela coluna. Sem guia, ou
sem a coluna no guia, o teto é exatamente 0,30. O teto usado fica em
`candidata.metricas["teto"]`, para o relatório mostrar "marcou 98% e passou"
junto de "porque o guia diz 100%".

**O que o teto fixo impedia.** No `beers`, `ounces` está errada em 295 de 300
linhas (98%). Um teto de 30% proibia por construção qualquer regra que detectasse
a coluna que concentra 60% dos erros do dataset: o recall ficava travado em cerca
de 41%. A regra de formato escrita para `ounces` morria por `marca_demais`.

**Por que o guia resolve.** O teto fixo existia porque, sem informação, não se
distingue "a regra marca demais" de "a coluna está quase toda errada". O guia
distingue: a taxa de células sujas dele, por coluna, estima a taxa de erro da
coluna, e `n` diz com que precisão.

**A forma da margem.** É o erro padrão de uma proporção observada em `n` amostras,
no pior caso (`p = 0,5`): `sqrt(0,25 / n)`, duas vezes para cerca de 95%. Com 20
linhas a margem é 0,22; com 40, 0,16. Ela aperta sozinha quando o guia cresce, o
que casa com `preparar_guia.py --linhas`. O `max` com o a priori não é enfeite:
em coluna que o guia viu limpa, a taxa é 0 e a margem sozinha (0,22) ficaria
abaixo de 0,30, apertando o teto e reprovando regra que antes passava.

**Honestidade sobre a ordem dos fatos.** A **forma** da margem vem do argumento
de erro amostral, que se sustenta lendo só o tamanho do guia. Mas o autor
**verificou** que ela funciona nas duas tabelas comparando a taxa suja do guia
com a taxa de erro real, e essa verificação usou o gabarito (`beers`: `ounces`
1,00 contra 0,98 real, `ibu` 0,40 contra 0,37, `abv` 0,35 contra 0,23;
`environment`: `State` 0,10 contra 0,18). É confirmação posterior: não foi o que
escolheu a fórmula, e o número 2 não foi ajustado. A evidência é limitada: cobre
**dois** datasets e **uma** semente de 20 linhas.

**Consequência declarada.** O guia agora supervisiona também o teto: um guia
pequeno e azarado pode subir o teto de uma coluna que é limpa (`Climate_Zone`:
guia 0,20, real 0,09, teto 0,42). O custo é aceito porque os outros testes do
crivo continuam valendo. A regra `^[A-Z]{2}$` que marcava 300 de 300 em `State`
continua morrendo (teto 0,32), e esse caso não pode voltar.

### Dois testes para o que o teto não alcança

**Veto por valor certificado (`marca_valor_certificado`).** Em `ounces` o teto
passa de 1 e `marca_demais` fica desligado, e o guia não tem célula correta de
`ounces` para o controle por célula. O guia certifica valores: se uma regra dos
tipos `formato`, `dominio`, `faixa` ou `ausente_disfarcado` marca célula cujo valor
sujo é **igual** (não substring) a um valor do guia naquela coluna, ela se
contradiz. Não vale para `dependencia`, em que o erro está no contexto da linha.
Medido com o gabarito (confirmação posterior): células realmente erradas que
carregam valor certificado: `beers` 0 de 495 nas cinco colunas com erro;
`environment` `State` 49 de 54 e `Climate_Zone` 26 de 26 (as duas precisam de
`dependencia`), 0 de 254 nas outras cinco. Posição: logo após `marca_celula_correta`,
por ser a mesma evidência direta de falso positivo.

**União por coluna: tentada e removida (`uniao_acima_do_teto`).** A escolha entre
variantes é por `(coluna, tipo)`, então tipos diferentes coexistem e a máscara
final é a união, que nenhum teto examinava. Tentou-se um portão: se a união
passasse do teto da coluna, descartava-se o tipo de maior taxa, até caber. Ele
falhou por construção, porque descarta a regra boa: ela marca mais justamente por
achar todos os erros. Caso reproduzido em `environment` `Temperature`: a regra de
`formato` `-?\d+(\.\d+)?` marca 56 células, todas erradas (precisão 1,000); uma
`ausente_disfarcado` de 22 sentinelas marca 52, com 8 erradas (precisão 0,154); a
união, 100 células (0,3333), passa do teto de 0,3236, e o portão mantinha a ruim e
descartava a boa. O buraco que ele fechava, dois tipos somando e marcando tudo, é
menor que o dano, e ele não sabe qual regra é boa. Hoje o crivo só grava a
`taxa_uniao` da coluna em `metricas` de cada regra que sobrevive, como informação
para o relatório de raciocínio ("as regras desta coluna somadas marcam 33%, acima
do que o guia sustenta"), nunca como critério.

### `DET_MINIMO` é o complemento deste número

`DET_MINIMO = 0.70`: uma dependência entre colunas só vira candidata se valer em
pelo menos 70% das linhas. **É a mesma premissa do piso de `TETO_MARCACAO`, dita uma
vez só.** Se o projeto declara não acreditar que uma coluna esteja mais de 30%
errada, então uma dependência verdadeira não pode falhar em mais de 30% das
linhas.

A primeira versão usava 0,85, e isso tinha um defeito perverso: a razão de
determinação cai **justamente porque a coluna tem erro**. No `environment`,
`City → State` tem razão de 0,82, porque 54 das 300 células de `State` estão
erradas — e o limiar de 0,85 rejeitava exatamente a dependência que corrigiria
esses 54 erros. O limiar punia o caso que a regra existe para consertar.

### O suporte se mede em linhas, não em grupos

A primeira versão exigia **dez grupos** de chave repetida (`GRUPOS_MINIMOS = 10`).
Isso era erro conceitual, e ele zerava a etapa: no `environment`, **nenhum** par
de colunas passava o filtro, então o tipo `dependencia` — a aposta central de
recall da POC — nunca dispararia no dataset onde ele importa.

Medido no sujo, sem gabarito, em 12/10/2026:

| Par | Grupos | Linhas cobertas | Razão | Grupos ambíguos | Veredito antigo |
|---|---|---|---|---|---|
| `City → State` | 9 | 300 (100%) | 0,820 | 0% | **rejeitado**, por 9 < 10 |
| `PM2.5 → Climate_Zone` | 3 | 8 (3%) | 0,875 | 33% | rejeitado, por sorte |
| `Temperature → Climate_Zone` | 46 | 105 (35%) | 0,800 | 41% | **passaria** |

Nove grupos cobrindo a tabela inteira é a evidência mais forte possível, e era
rejeitada por um grupo. Quarenta e seis grupos cobrindo um terço das linhas, com
41% deles sem maioria clara, é ruído, e passaria. O critério certo é **quantas
linhas vivem em grupos com suporte**, não quantos grupos existem:
`COBERTURA_MINIMA = 0.50` e `GRUPOS_MINIMOS_PAR = 2`.

Com os números novos, sete pares passam no `environment`, todos com ambiguidade
zero, e `City → State` acusa exatamente **54** células divergentes enquanto
`City → Climate_Zone` acusa **26** — que são os números de erro reais dessas
colunas. Essa conferência é **posterior à decisão** e foi feita com a métrica,
que é ferramenta de validação; ela não escolheu os limiares. O que escolheu foi o
argumento do complemento, que se sustenta lendo só o `config.py`.

---

## O residual é congelado como dicionário {#residual-congelado}

**Decisão.** As células detectadas que nenhuma estratégia reparou vão ao LLM **na
geração**, agrupadas por valor distinto e por entidade, e a resposta é gravada
como literal `{valor_sujo: valor_limpo}` dentro do limpador.

**Por quê.** A ablação do ZeroEC sem o passo residual dá precisão de 1,00 e
recall de 0,70 no Hospital e 0,00 no Rayyan — o perfil exato da POC 1, em que
`Measurement_Date` teve detecção perfeita e correção de zero. O residual é o
mecanismo que carrega recall nos papers.

**A inversão em relação ao ZeroEC.** Ele chama o LLM célula a célula em tempo de
execução. Isso é proibido aqui pelo princípio de converter conhecimento do LLM
em artefato reexecutável (`HANDOFF.md` §5).

**Consequência declarada.** O dicionário cobre valor sujo repetido, não valor
sujo inédito. Parte do que o limpador sabe é memória, não padrão. Por isso a
medição acontece em dois lugares e o recall é decomposto por fonte.

**O veto por valor certificado não tem exceção no dicionário.** Na detecção,
`dependencia` pode marcar valor certificado, porque o erro está no contexto da
linha (49 das 54 células erradas de `State` carregam valor certificado). No
dicionário não pode, porque a chave não carrega contexto: na tabela de origem,
dois `HH` marcados que pedem correções diferentes dão `conflitante`, mas numa
tabela nova todo `HH` marcado viraria `MA`. Custo: o residual perde o erro
contextual que tinha correção única na tabela de origem; esse fica para a
`moda_condicionada`.

**No braço sem guia, o dicionário passa sem filtro.** As três condições de
`crivar_residual` dependem do guia. É parte do que o braço mede: o residual sem
supervisão. O que limita o alcance é estrutural: o dicionário só age em célula que
uma detecção aprovada marcou.

**O domínio de `vizinho_no_dominio` também é memória.** Calculado na tabela de
geração e congelado como literal, vale para valores já vistos e não cobre valor
inédito.

---

## Uma única implementação da aplicação de regra {#motor-unico}

**Decisão.** `motor.py` é a única implementação. O crivo o importa; o codificador
copia o texto-fonte dele inteiro para dentro do limpador. A igualdade byte a byte
é assegurada por `tests/test_e6_codificador.py::test_bloco_embutido_e_motor_byte_a_byte`,
e `tests/test_vazamento.py` trava os imports do `motor.py` em `{"pandas"}`, para o
texto copiado não quebrar o limpador entregue.

**Por quê.** Na POC 1 a lógica existia duas vezes, uma na POC e uma cópia
congelada dentro do limpador, e as duas divergiram. Um run publicou F1 de 100%
numa coluna em que o limpador entregue marcava zero células. Consertar custou um
projeto inteiro (lição 8).

**Por que copiar em vez de importar.** O limpador tem de rodar sem depender deste
repositório. A cópia é mecânica e verificada por igualdade (o teste acima), não mantida à
mão — é isso que a diferencia do defeito da POC 1.

**Ordem de aplicação.** `conformidade` é o primeiro tipo de `TIPOS`: numa célula disputada,
a regra derivada de dado certificado pelo guia escreve antes da proposta pelo LLM.

---

## Medição em dois lugares {#duas-medicoes}

**Decisão.** Publicar o F1 nas linhas em que o limpador foi gerado **e** nas
linhas da mesma tabela que a geração nunca viu, mais a decomposição do recall por
fonte.

**Por quê.** O dicionário residual é construído a partir da tabela em que depois
se mede. Não é vazamento de gabarito — o LLM nunca vê a resposta certa — mas é
ajustar o artefato à tabela em que ele é avaliado. Com um número só, memorização
e capacidade ficariam somadas e indistinguíveis.

**Limitação conhecida da precisão publicada.** A fórmula é a da POC 1, de
propósito. Coluna sem nenhum erro é "não mensurável" e fica fora do total, então
um limpador que estraga uma coluna perfeitamente limpa recebe precisão 1,0 nessa
coluna. `flags` é o único lugar onde isso aparece. Nenhuma fixture está nesse
estado hoje; um teste (`..._limitacao_conhecida`) trava o comportamento. Mudar a
fórmula moveria números ancorados e é decisão do usuário.

**Viabilidade verificada.** As 300 linhas do `environment` são 300 das 1.000 do
arquivo completo, e as do `beers` são 300 das 2.410. No `beers`, duas colunas
grafam hífen no arquivo de 300 e sublinhado no completo; a fatia nunca vista é
renomeada antes de rodar o limpador.

---

## O guia é sorteado, e o CSV limpo tem dois guardiões declarados {#guia-sorteado}

**Decisão.** `preparar_guia.py` (sorteia o guia com semente fixa) e `medir.py`
(executa o limpador e calcula as métricas) são os únicos módulos que abrem o CSV
limpo, e os dois ficam fora do pacote `limpeza2/`.

**Por que dois e não um.** Eram um só, chamado `gabarito.py`. Mas sortear o guia
e medir o limpador não se chamam entre si, rodam em momentos diferentes e têm
entradas diferentes: o que compartilhavam era só o arquivo que abrem. Agrupar
pelo recurso em vez de pela função é a fronteira fraca que o `CLAUDE.md` §2
manda evitar.

**Por quê.** Transforma a regra "o gabarito nunca é lido pela geração" num
invariante verificável por import, em vez de uma convenção que depende de
disciplina. O teste de vazamento fica trivial: nenhum módulo de `limpeza2/`
importa nenhum dos dois.

**Sobre o sorteio.** Decisão do usuário, revista em 12/10/2026. *Era:* até 20
linhas sorteadas entre as que estavam 100% corretas no sujo, usadas só como
"não mexa". *Passa a ser:* 20 linhas sorteadas de **qualquer** parte da tabela,
com os valores do **CSV limpo**, mais até 2 pares `sujo → limpo` por coluna que
tem erro. O guia é a referência de um humano que pegou algumas linhas e as
deixou corretas. Gerado uma vez por semente, commitado, igual entre runs; cada
pasta traz `guia_receita.txt` (dataset, semente, linhas, pares por coluna),
registro para humano que nenhum módulo lê.

*Motivo.* O critério antigo rendia 5 linhas no `beers` (`ounces` errada em 295
de 300) e dependia de a tabela ter linhas perfeitas por sorte. O novo dá sempre
20, e o `ounces` limpo (`12`, `16`, `8.4`) mostra o formato certo contra catorze
variantes sujas.

*Efeito no crivo.* O controle negativo passa a ser por célula, só na coluna da
regra: reprova (`marca_celula_correta`) quem marca célula do guia com
`sujo == guia`; marcar célula com `sujo != guia` é correto. No reparo, onde ele
escreveu em célula do guia o valor tem de ser o do guia
(`corrompe_celula_do_guia`); não escrever não reprova *nesse* teste. A coluna-alvo
cobra o valor certo mesmo sem escrita, pelo piso do par
(`#par-exige-valor-exato`), que vale também para as células sujas do guia.

*Custo.* Mais supervisão: 20 × 11 = 220 células rotuladas no lugar de 55 no
`beers`, usadas como oráculo de correção. Ela tem de ser reportada ao lado de
cada número. `preparar_guia.py` aceita `--linhas`, `--pares` e `--destino` para
medir quanto o tamanho do guia compra.

**Braço sem guia.** A mesma espinha com os dois CSVs vazios, para medir quanto o
guia vale.

---

## Minerar primeiro, o LLM julga depois {#coluna-sujeito}

**Decisão.** Vale para dependências e para a coluna-sujeito: o perfil
determinístico propõe candidatos, e o LLM dá o veredito semântico.

**Por quê.** É a ordem do Cocoon. Pedir dependências ao LLM só pelos nomes das
colunas produz plausibilidade sem suporte nos dados; minerar sem o LLM produz
coincidência estatística — foi o que afundou o HoloClean nos benchmarks.

**A coluna-sujeito serve ao residual.** A ablação do IterClean mostra o F1 do
`flights` caindo de 0,595 para 0,164 quando os lotes de prompt são agrupados ao
acaso em vez de por entidade.

---

## Qual lado da violação está errado {#lado-errado-da-dependencia}

**Decisão.** Por padrão, repara-se o lado determinado. Exceção: se o valor do
determinante ocorre uma única vez na coluna e existe outro valor de determinante
a distância de edição 1 com grupo de suporte ≥ 2, corrige-se o determinante. A
distância é **Damerau-Levenshtein restrita**.

**Por que Damerau e não Levenshtein.** Descoberto na auto-revisão do plano: em
Levenshtein puro a transposição `Bosotn` → `Boston` custa 2, e como a exceção
exige distância exatamente 1, a classe mais comum de erro de digitação ficaria
fora do método. Contar transposição de adjacentes como uma edição custa quatro
linhas.

**Por quê.** A dependência orientada perde erro de digitação na chave. O BClean+
resolve isso reinferindo cada célula a partir da linha inteira, por máximo a
posteriori, mas isso exigiria congelar tabelas de probabilidade grandes no
limpador e reduziria o papel dos três agentes a quase nada.

**Alternativa recusada.** O grafo bayesiano completo do BClean+ (arquitetura C do
brainstorming).

---

## Portão AST {#portao-ast}

**Decisão.** Adaptado de `../POC_Limpeza_de_Dados/limpeza/sandbox.py`, com quatro
correções que a POC 1 não tem: allowlist de builtins, proibição de `import`,
dunder, `eval`, `exec`, `compile`, `open`, `getattr` e companhia, execução em
namespace descartável e nunca `globals()`, **um proxy de `re` em vez do módulo**,
**proibição de ler `.format` e `.format_map`**, **proibição de escrever ou apagar
atributo**, e **um proxy novo por materialização**.

**Por quê as quatro correções, e o que elas consertam.** Eu escrevi antes que o
`sandbox.py` da POC 1 "já é implementação testada". Isso estava errado num ponto
que importa: ele entrega o **módulo** `re` ao namespace, e o módulo `re` importa
`enum`, que importa `sys`. Executado contra a versão herdada, em 12/10/2026:

```python
def corrigir(valor):
    return str(re.enum.sys.modules["os"].getcwd())
```

Isso passou pelo portão e devolveu o diretório do projeto. Com `.system(...)` no
lugar de `getcwd()`, é execução arbitrária de comando na máquina de quem gera.
A análise de AST não vê nada: a chamada tem `func` como `Attribute`, não como
`Name`, e nenhum atributo começa com `__`. A premissa "o LLM só tem `re`" é
falsa — a superfície real é o grafo de atributos de `re`.

Mais dois furos da mesma família, achados na sequência e também confirmados por
execução: `f = "{0.__class__}".format` seguido de `f(valor)` devolvia
`<class 'str'>`, porque a proibição só olhava chamada e não leitura; e
`re.sub = len` **executava**, envenenando o proxy compartilhado, de modo que a
função materializada depois quebrava. Esse último é o mais grave para a POC, e
não por ser vazamento: o crivo aprova ou reprova regra **executando-a**, então um
proxy envenenado faria regras seguintes falharem ou devolverem valor errado, e a
POC registraria isso como propriedade da regra.

**Este buraco existe na POC 1**, que está publicada em
`github.com/gustavocamargo1996/AgenteLimpezaDeDados`. Aqui a POC 1 é somente
leitura, então a correção lá é decisão do usuário.

**Garantia por sondagem, não prova.** Depois das correções, 29 sondas foram
executadas contra o portão: `re.enum`, `re.functools` e `re.sys` dão
`AttributeError`; `.format` e `.format_map` são barrados em leitura e em chamada;
escrita de atributo é barrada; e nada alcançou módulo nem caminho de arquivo.
Os atributos não-dunder de `Pattern`, de `Match` e dos tipos nativos da allowlist
foram sondados e não levam a lugar nenhum. Isso é evidência, não demonstração: a
superfície de um sandbox em processo nunca é provada segura por teste.

**Limite conhecido: sem limite de tempo nem de memória.** `while True: pass`,
recursão profunda e regex com backtracking catastrófico passam no portão e travam
a geração. A POC 1 também não tinha. O modelo de ameaça aqui é LLM desastrado,
não adversário, então é limite declarado, não defeito.

**`corrigir` tem de devolver `str`.** `testar_fumaca` rejeita gerador, `None` e
lista: a POC 1 checava isso no modo série e a checagem se perdeu ao não portar
aquele modo. Sem ela, o `repr` de um gerador chegaria à célula.

`re` chega ao namespace como proxy e `pd` fica fora — o que casa com a decisão de
o LLM escrever só funções escalares.

**O limpador gerado roda sem o portão** na máquina do usuário. O cabeçalho dele
avisa isso.

**O limpador entregue importa o `re` inteiro.** O portão dá ao LLM um proxy de `re`
com as funções permitidas e as flags; o limpador, que roda sem portão por desenho,
faz `import re`. Não é inconsistência: o portão protege a geração, e o cabeçalho
do limpador avisa que ele roda sem portão.

---

## O par do guia exige o valor exato {#par-exige-valor-exato}

**O furo.** `_reprovar_reparo` só verificava o par do guia quando o reparo havia
alterado a célula (`reparada` verdadeiro). Reparo que não tocava o par passava,
embora "não alterou" signifique exatamente "continua errado na única célula que
um humano rotulou". Reproduzido: detecção `dominio` marcando as linhas 4 (XX) e 9
(YY), par `4, estado, XX → MA`, reparo `{"YY": "MA"}`; resultado aprovado.

**A correção.** O piso vale sobre as células de que o reparo é responsável. Na
coluna-alvo da candidata, vale sempre: toda linha de par que esteja na máscara
exige `novo == limpo`, sem consultar `reparada`. Em coluna determinante (só na
`moda_condicionada`), vale somente onde o reparo escreveu, isto é, onde
`novo` difere do sujo naquela célula; ali o valor escrito tem de ser o `limpo`.
Razão: a exceção do determinante altera a coluna determinante, mas exigir o par
dela sem condição reprovaria reparo válido por célula que ele nunca toca (par em
`cidade`, reparo que só conserta `estado`). O filtro por coluna impede ainda que
um par de `onca` reprove um reparo de `estado`. Linha de par fora da máscara não
é verificada: a detecção não a marcou.

**Células sujas do guia valem como par.** Na coluna-alvo, célula do guia com
`sujo != guia` que esteja na máscara exige `novo == guia`, mesmo que o reparo não
tenha escrito: é o mesmo piso do par explícito, com o mesmo motivo
(`perde_par_do_guia`). Só a coluna **determinante** é poupada quando o reparo não
escreveu nela. Na **detecção** as células sujas do guia não entram no piso: isso
exigiria marcar todas e rejeitaria regra que pega só um dos tipos de erro da
coluna. É decisão, e não pendência: o piso da detecção em `e3_crivo._reprovar`
cobre só os pares explícitos do guia.

**O preço.** Mudança de comportamento: estratégias como `esvaziar` e
`vizinho_no_dominio`, que não alcançam o valor exato do par, passam a ser
reprovadas. Troca deliberada de precisão a mais por recall a menos.

---

## Provedor desconhecido falha alto {#provedor}

**Decisão.** `provedor.py` levanta exceção se `PROVEDOR` não for reconhecido.
Nunca cai para OpenAI por omissão.

**Por quê.** O destino desta linha de pesquisa é rodar com dados de estatísticas
públicas que não podem sair da rede. Um typo que caísse silenciosamente para
OpenAI mandaria a tabela do usuário para fora.

**Provedor desta POC.** OpenAI, modelo `gpt-6-luna` com `reasoning_effort="none"`,
nome e chave no `.env`. Escolhido em 12/10/2026 por ser o da faixa barata na
página oficial de comparação da OpenAI nessa data; o `gpt-5.6-luna`, escolhido no
design, já não aparecia nela e custa o dobro. Raciocínio em `none` porque só assim
o modelo aceita `temperature` e não gasta tokens ocultos que podem cortar a
resposta. O terceiro valor de `PROVEDOR`, `gravado`, reproduz um run a partir do
`respostas.jsonl`.

**Ressalva de método, obrigatória ao reportar.** A POC 1 rodou com `gpt-4o-mini` e
é somente leitura. Toda comparação com o placar dela muda método e modelo ao mesmo
tempo; a diferença não se atribui só ao método.

---

## Conformidade de schema {#conformidade-de-schema}

**Problema.** Um único juiz, o teto estatístico de marcação, servia a todo tipo
de erro. Para coluna de tipo claro (numérico com uma decimal, inteiro, data) a
pergunta é lógica, não estatística: "este valor obedece ao formato da coluna?".
Rotear esse caso fácil por um juiz desenhado para o difícil custou meia sessão
tentando tirar um `℃` de uma coluna numérica.

**O que o mapeamento prescreve.** Os três estudos concordam: inferir o tipo da
coluna primeiro e derivar a restrição dele. O **BClean+** usa o LLM só para
rotular o tipo semântico e sintetiza a regex; a ablação sem isso derruba o F1 em
0,36 e o leva a zero no `flights`. O **CatDB** deriva as regras de forma
determinística de um catálogo por coluna. O **Cocoon** põe caractere e padrão
antes da dependência funcional e reporta F1 de 0,99 em tipo de coluna.

**Decisão.** `conformidade.py` deriva, das células que o guia certificou, o
conjunto de `padrao(v, 3)` de cada coluna e emite uma `Candidata` de tipo
`conformidade`. `motor.detectar` marca a célula cujo padrão não está no conjunto.
Não há LLM, e a etapa só detecta: a correção fica com o especificador. `padrao`
mora em `motor.py`, e não em `e1_perfil.py`, porque o limpador gerado leva só o
texto do motor e o tipo precisa dela em tempo de execução. O nível vem de
`motor.NIVEL_SCHEMA`, uma só constante para derivar e para aplicar.

**Por que o nível 3 e não o 2.** O nível 2 codifica a quantidade de caracteres:
`index`, que vai de `0` a `299`, tem os padrões `9`, `92` e `929`, e 20 linhas
amostram algumas larguras, não todas. O schema ficava sensível a um acidente da
amostra, não a uma propriedade da coluna, e a coluna limpa era marcada com
precisão 0,000. O nível 3 descarta a contagem (`0`, `12` e `299` viram `9`), e o
argumento independe do gabarito. *Confirmação posterior, com o gabarito:* nível 2
alcança 634 de 829 erros com precisão 0,924; nível 3, 678 de 829 com 0,943.
`ibu` sobe a precisão de 0,957 para 1,000, `city` passa a ser alcançada inteira
(9 de 9) e `index`, `id`, `brewery_id` e `PM2.5` deixam de ser marcadas.

**O corte de um terço.** A coluna tem schema se os padrões distintos forem no
máximo um terço das linhas do guia (6 em 20). É limiar a priori, declarado em
`config.FRACAO_PADROES_SCHEMA`.

**Medição no nível 3 (guia canônico, gabarito só para medir).** Precisão e
recall: `ounces` 1,000 e 1,000; `state` 1,000 e 1,000; `abv` 0,972 e 1,000; `ibu`
1,000 e 1,000; `Temperature`, `Measurement_Date` e `Monitoring_Station_ID` 1,000
e 1,000; `city` 0,562 e 1,000 (16 marcadas, 9 erradas). `State` e `Climate_Zone`
têm schema apertado e marcam zero, porque os erros são siglas válidas: a
abstenção é o sinal de roteamento para a dependência funcional. `Project_Name`
ganha schema de 3 padrões e marca 36 células, 35 erradas (precisão 0,972, recall
0,625), mas o crivo a reprova por `perde_par_do_guia`.

**O custo, e uma opção não aplicada.** `brewery-name` passa a ter schema com 6
padrões e marca 31 células, todas certas (precisão 0,000), e o crivo a aprova.
Apertar o corte para um quarto (5 em 20) excluiria `brewery-name` e levaria a
precisão a 0,985 com recall de 678 de 829. **Não foi aplicado:** não há argumento
independente do gabarito para escolher um quarto e não um terço, e aplicá-lo seria
ajustar o limiar olhando a resposta. Fica como decisão do usuário.

**Por que o teto não se aplica.** A restrição vem de dado que o humano
certificou, não de chute do LLM, então limitar por taxa não faz sentido: se a
coluna está 98% fora do schema, 98% é a verdade (em `ounces` o teto chega a
1,224 e seria vácuo de todo jeito). Continuam valendo a não-vacuidade e o piso do
par. `marca_celula_correta` e o veto por valor certificado não disparam por
construção, já que célula certificada conforma ao schema derivado dela mesma; o
crivo os mantém ativos para `conformidade` como alarme de que o schema não está
saindo das células certificadas.

**O corte fica em um terço, com custo conhecido.** `brewery-name` passa a ter
schema (6 padrões) e a conformidade marca 31 células com precisão 0,000 na
detecção. Um corte de um quarto a excluiria, mas seria o primeiro limiar do
projeto escolhido olhando a resposta, e contaminaria a defesa de `TETO_MARCACAO`,
`DET_MINIMO` e da margem do teto. A métrica é de reparo: marcação que ninguém
reescreve vira flag e não entra na precisão. No primeiro run mede-se o destino
das 31, pela decomposição por fonte. **Ideia registrada, não implementada:** o
que distingue `brewery-name` de `ounces` é a forma dos padrões (`Aa Aa Aa` contra
`9`); schema com espaço ou muitas alternâncias de classe é texto livre, e isso se
observa sem gabarito.

---

## Roteamento do detector pela conformidade aprovada {#roteamento-do-detector}

**Decisão.** Na coluna cuja conformidade foi **aprovada pelo crivo**, o detector
não recebe o tipo `formato`; nas outras, recebe o catálogo inteiro. `dependencia`
só entra onde a coluna é lado determinado de algum par minerado.

**Por quê.** A conformidade responde "o valor tem a forma certa?" a partir de dado
certificado, e um `formato` do LLM faria a mesma pergunta com resposta pior; sem o
portão da união, ele só somaria falso positivo. `dominio`, `faixa` e
`ausente_disfarcado` perguntam outra coisa (`Freedonia` tem forma de país, `9999`
conforma a `9`, `0` também) e ficam. O critério é a aprovação, e não ter schema: a
conformidade de `Project_Name` é reprovada (`perde_par_do_guia`), e com "ter
schema" a coluna ficaria sem regra de forma nenhuma. A abstenção da conformidade
vai ao prompt como frase (aprovada, reprovada com motivo, vácua) e orienta sem
restringir.

---

## Reprodutível dadas as respostas {#determinismo-da-geracao}

**Decisão.** `temperature=0` e `seed` fixa quando o provedor aceita, e cada
resposta crua gravada em `respostas.jsonl`. `PROVEDOR=gravado` refaz a geração a
partir dele.

**A origem viaja com as respostas.** O primeiro registro do `respostas.jsonl` é
`{"origem": {"provedor", "modelo", "esforco"}}`, gravado ao abrir a geração. No
replay, o cliente lê a origem dali e a regrava no novo arquivo, e o cabeçalho do
limpador e o `.md` imprimem essa origem, não o `config` corrente. Assim o replay
reproduz o limpador byte a byte (`tests/test_espinha.py`).

**Por quê.** A geração por LLM não é reprodutível bit a bit, nem com temperatura
zero. O invariante do `CLAUDE.md` §8 trava o **artefato congelado** e a geração a
partir das respostas congeladas; diferença entre dois runs pagos não é regressão.

---

## Falha de API tem nome {#falha-de-api}

**Decisão.** O provedor converte o que a API devolve em `FalhaDoLLM` com um de
cinco motivos: `rede` (tentativas do SDK esgotadas), `cortada`
(`finish_reason == "length"`, o `LengthFinishReasonError` que quebrou o
`Eco_Status` na POC 1), `recusada`, `json_invalido` e `teto` (`TETO_CHAMADAS`
atingido). Cada agente tem um `except FalhaDoLLM`, e a unidade fica sem regra.
Autenticação e modelo inexistente **não** viram `FalhaDoLLM`: derrubam o run.

**Por quê.** Degradar coluna por coluna gastaria 60 chamadas para descobrir uma
chave errada. Um run truncado pelo teto carrega a marca no próprio limpador
(`GERACAO_TRUNCADA`), no `.md` e na saída do `medir.py`.

---

## `reparada` significa "o valor mudou" {#reparada-e-mudanca}

**Decisão.** Em toda estratégia, `reparar` só marca `reparada` onde o valor mudou.

**Por quê.** Antes, `dicionario` com `{v: v}` e `vizinho_no_dominio` que devolvia o
próprio valor contavam como reparo sem mudar nada, e uma regra assim passaria pelo
`nao_repara` do crivo. Mudança de comportamento num caso de borda, feita junto com
a simplificação do `reparar` na parte 2.

---

## A função que lança numa célula vira flag {#funcao-que-lanca}

**Decisão.** Em `motor.reparar`, se a função escalar (`corrigir_<n>`, ou outra
estratégia escalar) lança numa célula, a célula fica marcada e não reparada, isto
é, vira flag. A tabela segue. Na geração, o codificador passa a função na fumaça
com **todos** os valores marcados distintos da tabela de origem, mais os exemplos
do guia; o prompt continua levando só os `VALORES_NO_PROMPT` primeiros.

**Por quê.** O limpador é aplicado a tabelas novas, e nelas um valor inédito pode
fazer a função lançar. Derrubar a tabela inteira por uma célula perde tudo o que as
outras regras corrigiram. Na tabela de origem, a degradação nunca acontece em
silêncio: a função que lança em algum valor marcado é rejeitada pelo portão antes
de chegar ao crivo. A fumaça final do limpador continua pegando o que quebra ao
carregar o módulo. Uma função que lança em **toda** célula marcada não repara nada
e cai no crivo como `nao_repara`; `lancou` fica para o que lança fora da célula
(função ausente, coluna inexistente).

---

## As decisões do usuário entram pela pasta do guia {#decisoes-do-usuario}

**Decisão (17/10/2026, para o orquestrador).** Um `decisoes.json` opcional na pasta
do guia, ao lado de `guia_linhas.csv` e `guia_pares.csv`, é uma lista de
`{coluna, tipo, parametros, decisao, instrucao, origem, versao}`. `e1_perfil` o lê
para `Entrada.decisoes`; a assinatura de `gerar_limpador` e a espinha não mudam.
Sem o arquivo, o gerador é byte a byte o de antes
(`tests/test_decisoes_gerador.py`, com `[]` e com o invariante).

- **A chave de uma regra** é `(coluna, tipo, parametros)`, por igualdade. É o que
  liga a decisão à regra entre versões.
- **`rejeitar`** vira o motivo `rejeitada_pelo_usuario`, o primeiro teste do crivo.
  No residual, a entrada `{"tipo": "residual", "parametros": {"sujo": X}}` tira `X`
  do dicionário com o mesmo motivo.
- **`aprovar`** dispensa os testes estatísticos (`marca_demais`, `ambigua`) e faz a
  regra vencer a disputa de `superada`. **Não dispensa os testes contra o guia**
  (`marca_celula_correta`, `marca_valor_certificado`, `perde_par_do_guia` e o crivo
  do reparo): é o gerador, e não só a interface, que impede o usuário de contradizer
  o guia que ele mesmo forneceu, e isso vale também para quem usa o gerador sem o
  orquestrador.
- **Uma `aprovar` cuja regra o detector não propôs de novo** entra como candidata
  herdada (`e2_detector.herdadas`) e passa pelo crivo como qualquer outra.
- **`instrucao`** é acrescentada ao fim do prompt do especificador daquela regra, só
  quando existe. A instrução de sistema não muda.

**Rejeitar a vencedora deixa a próxima variante vencer.** A decisão vale para uma
regra, não para o tipo. Rejeitar o `dominio` aprovado de `ounces` no MVP faz a
variante que tinha ficado `superada` assumir o lugar, e a coluna continua com um
`dominio` em `REGRAS`. É o comportamento coerente com o crivo; o relatório de
geração o mostra, e o usuário pode rejeitar a nova vencedora no ciclo seguinte.

**Custo medido sobre o MVP, sem API.** Rejeitar a dependência
`brewery_id → moda_condicionada` (a que trocou `95` por `12` numa coluna sem erro)
não muda prompt nenhum: zero chamadas novas. Rejeitar uma conformidade custa de 1
a 4, porque o catálogo do detector daquela coluna muda. Uma instrução numa regra
aprovada custa a chamada do especificador dela e, se o reparo mudar, a do lote do
residual que passa a ver outras células.

**Teto.** As inserções levaram `e3_crivo.py` a 211 linhas e o gerador a 1.879,
acima do 200 por arquivo e dos 1.850. O usuário decidiu em 17/10/2026 que não
corromper o código que funciona vale mais que o teto: nada foi refatorado para
caber, e o estouro está declarado no `CLAUDE.md` §2.

---

## O ciclo reaproveita as respostas gravadas {#reaproveitar}

**Decisão.** `PROVEDOR=reaproveitar` responde do `RESPOSTAS_GRAVADAS` toda chamada
cujo prompt já foi gravado e chama `PROVEDOR_VIVO` (`openai` ou `ollama`) só para o
que falta. As respostas novas e as reaproveitadas vão juntas para o
`respostas.jsonl` da versão nova, que serve de base para o ciclo seguinte.

**Por quê.** Gerações repetidas variam de 5 a 7 pontos de recall. Regenerar tudo ao
vivo a cada aperfeiçoamento misturaria o efeito da decisão do usuário com a
variação do LLM, e o usuário não saberia o que a decisão dele fez. Reaproveitando,
a diferença entre duas versões vem só das decisões, e o ciclo custa poucas
chamadas.

**Duas travas.** `PROVEDOR_VIVO` desconhecido falha alto, pela mesma razão de
privacidade do `#provedor`. E `MODELO` diferente do modelo gravado na origem falha
alto: uma versão com respostas de dois modelos seria inexplicável.

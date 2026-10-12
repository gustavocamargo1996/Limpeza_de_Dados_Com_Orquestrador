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
controle negativo das linhas limpas do guia, não-vacuidade, teto de marcação,
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

## O teto de marcação é fixado a priori {#teto-de-marcacao}

**Decisão.** `TETO_MARCACAO = 0,30`, em `config.py`, escolhido sem olhar os
dados.

**Por quê.** Calibrar esse número exigiria medir a taxa real de erro por coluna,
o que exige o gabarito. Seria vazamento. O valor está acima da taxa de erro por
coluna dos datasets em uso e muito abaixo do que permitiria marcar a coluna
inteira.

**Consequência declarada.** Coluna com mais de 30% de erro é subdetectada. É
limite do método. Trocar o número depois de ver um resultado ruim seria ajustar
ao gabarito pela porta dos fundos.

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

---

## Uma única implementação da aplicação de regra {#motor-unico}

**Decisão.** `motor.py` é a única implementação. O crivo o importa; o codificador
copia o texto-fonte dele inteiro para dentro do limpador. Um teste assevera a
igualdade byte a byte.

**Por quê.** Na POC 1 a lógica existia duas vezes, uma na POC e uma cópia
congelada dentro do limpador, e as duas divergiram. Um run publicou F1 de 100%
numa coluna em que o limpador entregue marcava zero células. Consertar custou um
projeto inteiro (lição 8).

**Por que copiar em vez de importar.** O limpador tem de rodar sem depender deste
repositório. A cópia é mecânica e verificada por igualdade, não mantida à mão —
é isso que a diferencia do defeito da POC 1.

---

## Medição em dois lugares {#duas-medicoes}

**Decisão.** Publicar o F1 nas linhas em que o limpador foi gerado **e** nas
linhas da mesma tabela que a geração nunca viu, mais a decomposição do recall por
fonte.

**Por quê.** O dicionário residual é construído a partir da tabela em que depois
se mede. Não é vazamento de gabarito — o LLM nunca vê a resposta certa — mas é
ajustar o artefato à tabela em que ele é avaliado. Com um número só, memorização
e capacidade ficariam somadas e indistinguíveis.

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

**Sobre o sorteio.** Decisão do usuário: 20 linhas sorteadas entre as que estão
100% corretas, e até 2 pares `sujo → limpo` por coluna que tem erro. A cota por
coluna imita o humano varrendo coluna a coluna e garante exemplo onde o sorteio
puro não chegaria. Gerado uma vez, commitado, igual entre runs.

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
a distância de edição 1 com grupo de suporte ≥ 2, corrige-se o determinante.

**Por quê.** A dependência orientada perde erro de digitação na chave. O BClean+
resolve isso reinferindo cada célula a partir da linha inteira, por máximo a
posteriori, mas isso exigiria congelar tabelas de probabilidade grandes no
limpador e reduziria o papel dos três agentes a quase nada.

**Alternativa recusada.** O grafo bayesiano completo do BClean+ (arquitetura C do
brainstorming).

---

## Portão AST {#portao-ast}

**Decisão.** Adaptado de `../POC_Limpeza_de_Dados/limpeza/sandbox.py`: allowlist
de builtins, proibição de `import`, dunder, `eval`, `exec`, `compile`, `open`,
`getattr` e companhia, execução em namespace descartável, nunca `globals()`.

**Por quê.** Já é implementação testada, e cabe no orçamento com 142 linhas.
`re` fica disponível no namespace e `pd` fora — o que casa com a decisão de o
LLM escrever só funções escalares.

**O limpador gerado roda sem o portão** na máquina do usuário. O cabeçalho dele
avisa isso.

---

## Provedor desconhecido falha alto {#provedor}

**Decisão.** `provedor.py` levanta exceção se `PROVEDOR` não for reconhecido.
Nunca cai para OpenAI por omissão.

**Por quê.** O destino desta linha de pesquisa é rodar com dados de estatísticas
públicas que não podem sair da rede. Um typo que caísse silenciosamente para
OpenAI mandaria a tabela do usuário para fora.

**Provedor desta POC.** OpenAI, modelo `gpt-5.6-luna`, nome e chave no `.env`.

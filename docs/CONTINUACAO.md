# Continuação: estado em 12/10/2026

Escrito para a próxima sessão, e para mim mesmo depois de a conversa ser
resumida. Leia junto com o `CLAUDE.md` e o `docs/DECISOES.md`.

---

## 1. O que existe e está em `main`

A **fundação determinística** da POC 2, mesclada em `main`, com 174 testes
passando e saída limpa (hoje 186 após as duas mudanças da seção 3 e 4). Onze arquivos `.py` fora de `tests/`, 940 linhas, maior
com 179.

| Arquivo | Função |
|---|---|
| `limpeza2/tipos.py` | o que viaja entre etapas |
| `limpeza2/config.py` | caminhos, limiares, semente |
| `limpeza2/portao.py` | valida o Python gerado por LLM antes de deixá-lo rodar |
| `limpeza2/motor.py` | única implementação de aplicação de regra: 5 tipos de detecção, 5 estratégias de reparo |
| `limpeza2/limites.py` | o que o guia sustenta para uma coluna |
| `limpeza2/e1_perfil.py` | etapa 1: perfila a tabela suja |
| `limpeza2/e3_crivo.py` | etapa 3: reprova a regra candidata que não se sustenta |
| `preparar_guia.py` | sorteia o guia com semente fixa |
| `medir.py` | executa o limpador gerado e mede |

**Nada chama LLM ainda.** Os três agentes são a parte 2.

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
células certificadas do guia**, com o `padrao(v, 2)` que já existe em
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

### O desenho aprovado pelo usuário, implementado

Implementado em `limpeza2/conformidade.py` (`schema_da_coluna`,
`candidatas_de_conformidade`), no tipo `conformidade` de `motor.py` (com `padrao`
movida para lá) e na exceção do teto em `e3_crivo.py`. Âncora:
`docs/DECISOES.md#conformidade-de-schema`. A espinha ainda não existe: a parte 2
chama `candidatas_de_conformidade` antes do crivo. Reproduziu todos os números
da tabela acima. Atenção: coluna sem erro e de largura variável (`index`, `id`,
`brewery_id`, `PM2.5`) tem schema e é marcada com precisão 0,000 (9 a 15
células), e o crivo a aprova.

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
- `limpeza2/__init__.py` está vazio e a suíte passa sem ele: é a vaga livre se a
  parte 2 precisar de um 17º arquivo.

## 7. O que vem depois, em ordem

1. **A parte 2:** `provedor.py`, `e2_detector.py`, `e4_especificador.py`,
   `e5_residual.py`, `e6_codificador.py`, `espinha.py`. Seis arquivos, teto de 16.
2. Duas recomendações da revisão final para a parte 2: o teste de vazamento **em
   tempo de execução**, instrumentando `pandas.read_csv` e exigindo que todo
   caminho aberto seja o sujo ou o guia; e o codificador deve **ler `motor.py` do
   disco** e concatenar, nunca guardar template com o texto do motor dentro, para
   a identidade byte a byte ser verdadeira por construção.
3. O primeiro run pago. **Nenhuma chamada de API foi feita nesta sessão.**
   Estimativa: cerca de 60 chamadas por dataset por braço, com `gpt-5.6-luna`.
   Anunciar antes.
4. A espinha deve chamar `candidatas_de_conformidade` e entregar as candidatas ao
   crivo junto com as do detector; o detector só é chamado para as colunas sem
   schema. Decidir o que fazer com coluna de schema sem erro (precisão 0,000).

## 8. Como o usuário trabalha

Português do Brasil em tudo. Honestidade acima de número bonito: ele prefere
ouvir que o limpador corrige 13% a ouvir um número inflado. Run pago é decisão
dele, anunciada antes. Merge e push só quando ele pedir — nesta sessão ele pediu
merge local em `main`, sem remoto.

Ele aprovou cada mudança de limiar separadamente, e corrigiu o rumo três vezes de
forma decisiva: tirou a POC 1 do papel de alvo, mandou o guia vir do limpo, e
apontou que conformidade de schema deveria ser a parte fácil. **Nas três ele
estava certo e eu não tinha visto.**

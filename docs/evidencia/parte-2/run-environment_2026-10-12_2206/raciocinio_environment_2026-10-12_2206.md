# Raciocinio do limpador environment_2026-10-12_2206

- modelo: gpt-6-luna (openai), raciocinio none
- supervisao: 220 celulas do guia + 14 pares
- chamadas: 28; tokens: 51354
- unidades sem regra pelo teto de chamadas: 0

## City

### conformidade: vacua

- parametros: `{'padroes': ['Aa', 'Aa Aa']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 2 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### dependencia: marca_celula_correta

- parametros: `{'determinantes': ['State']}`
- raciocinio: A relação minerada entre State e City tem 54 divergências; a regra pode sinalizar inconsistências contextuais sem contrariar os exemplos corrigidos do guia.
- marcadas: 54
- taxa: 0.18
- motivo: marca_celula_correta
- teto: 0.3

## State

### conformidade: vacua

- parametros: `{'padroes': ['A']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.32360679774997897

### dependencia: aprovada

- parametros: `{'determinantes': ['City']}`
- raciocinio: A cidade determina o estado nos pares minerados, e o guia mostra divergências contextuais entre City e State.
- marcadas: 54
- taxa: 0.18
- motivo: aprovada
- teto: 0.32360679774997897
- taxa_uniao: 0.18
- reparadas: 54
- motivo_reparo: aprovada
- reparo: moda_condicionada
- raciocinio do reparo: Cada City determina um State consistente. Os valores marcados divergem do State associado à cidade; o guia confirma correções contextuais. Substituir cada valor pelo State mais comum entre as linhas com a mesma City.

## Country

### conformidade: vacua

- parametros: `{'padroes': ['Aa', 'Aa Aa']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 2 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### dominio: vacua

- parametros: `{'valores': ['United States', 'Germany', 'India']}`
- raciocinio: Os três valores observados formam o domínio completo e são compatíveis com as linhas corrigidas do guia.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### dependencia: vacua

- parametros: `{'determinantes': ['City']}`
- raciocinio: City determina Country sem divergências nos nove grupos minerados, permitindo detectar países incompatíveis com a cidade.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## Climate_Zone

### conformidade: vacua

- parametros: `{'padroes': ['Aa']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.423606797749979

### dependencia: aprovada

- parametros: `{'determinantes': ['City']}`
- raciocinio: A cidade determina fortemente a zona climática, e o guia mostra que a zona pode ser contextual; a regra sinaliza divergências em relação à zona associada à cidade.
- marcadas: 26
- taxa: 0.08666666666666667
- motivo: aprovada
- teto: 0.423606797749979
- taxa_uniao: 0.08666666666666667
- reparadas: 26
- motivo_reparo: aprovada
- reparo: moda_condicionada
- raciocinio do reparo: Cada cidade está associada à zona climática mais comum nas linhas correspondentes. Os valores marcados são zonas válidas, mas divergem da zona associada à cidade. Substituir cada valor pela zona climática mais comum entre as linhas com a mesma City.

## Monitoring_Station_ID

### conformidade: aprovada

- parametros: `{'padroes': ['AaAa_9', 'Aa_9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 2 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 44
- taxa: 0.14666666666666667
- motivo: aprovada
- teto: 0.37360679774997896
- taxa_uniao: 0.14666666666666667
- reparadas: 44
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: Os identificadores seguem o formato NomeDaCidade_ seguido de três dígitos. Os valores marcados têm o nome da cidade e os três dígitos concatenados, sem o sublinhado exigido. Inserir um sublinhado antes dos três dígitos finais.

```python
def corrigir_1(valor):
    if re.fullmatch('[A-Za-z]+\\d{3}', valor):
        novo_valor = valor[:-3] + '_' + valor[-3:]
    else:
        novo_valor = valor
    return novo_valor
```

## PM2.5

### conformidade: vacua

- parametros: `{'padroes': ['9.9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### formato: vacua

- parametros: `{'regex': '\\d{2,3}\\.\\d{1,2}'}`
- raciocinio: Os valores observados são números decimais com uma ou duas casas; o formato é compatível com os exemplos corretos do guia.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### faixa: vacua

- parametros: `{'minimo': 0, 'maximo': 200}`
- raciocinio: Uma faixa não negativa até 200 é plausível para PM2.5 e não marca nenhum valor correto mostrado no guia.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## Temperature

### conformidade: aprovada

- parametros: `{'padroes': ['-9.9', '9.9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 2 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 56
- taxa: 0.18666666666666668
- motivo: aprovada
- teto: 0.32360679774997897
- taxa_uniao: 0.18666666666666668
- reparadas: 56
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: Temperaturas são representadas como números decimais sem unidade. Os valores marcados têm o sufixo '℃', ausente nos valores certificados. Remover o sufixo '℃' de cada valor marcado.

```python
def corrigir_2(valor):
    if valor.endswith('℃'):
        return valor[:-1]
    return valor
```

### faixa: vacua

- parametros: `{'minimo': -15, 'maximo': 50}`
- raciocinio: A faixa ampla acomoda as temperaturas válidas mostradas no guia e pode sinalizar magnitudes implausíveis sem marcar os exemplos corretos.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.32360679774997897

### ausente_disfarcado: vacua

- parametros: `{'sentinelas': ['92.9', '92.9℃', '9.9', '9.9℃', '-9.9', '-9.9℃']}`
- raciocinio: Esses valores concentram 300 ocorrências em padrões repetidos e parecem códigos de ausência disfarçados, não temperaturas observadas.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.32360679774997897

## Measurement_Date

### conformidade: aprovada

- parametros: `{'padroes': ['9-9-9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 48
- taxa: 0.16
- motivo: aprovada
- teto: 0.47360679774997894
- taxa_uniao: 0.16
- reparadas: 48
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: As datas válidas seguem o formato YYYY-MM-DD. Os valores marcados estão no formato M/D/YYYY, com mês antes do dia. Interpretar cada valor como mês/dia/ano e convertê-lo para YYYY-MM-DD.

```python
def corrigir_3(valor):
    partes = valor.split('/')
    if len(partes) == 3 and all((parte.isdigit() for parte in partes)):
        mes, dia, ano = partes
        if len(ano) == 4 and 1 <= int(mes) <= 12 and (1 <= int(dia) <= 31):
            return f'{ano}-{int(mes):02d}-{int(dia):02d}'
    return valor
```

### faixa: vacua

- parametros: `{'minimo': 2020, 'maximo': 2025}`
- raciocinio: As datas válidas mostradas estão entre 2020 e 2025; a faixa detecta anos fora desse intervalo sem marcar os exemplos do guia.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.47360679774997894

## Project_Name

### conformidade: perde_par_do_guia

- parametros: `{'padroes': ['Aa Aa Aa 9', 'AaAa Aa Aa 9', 'AaAaAa Aa Aa 9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 3 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 36
- taxa: 0.12
- motivo: perde_par_do_guia
- teto: 0.3

### formato: perde_par_do_guia

- parametros: `{'regex': '[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+){2} 20[0-2][0-9]'}`
- raciocinio: Os exemplos corretos seguem o padrão de duas palavras em Title Case, “Initiative” e um ano de quatro dígitos; a regra é permissiva quanto a erros internos de grafia mostrados pelo guia.
- marcadas: 36
- taxa: 0.12
- motivo: perde_par_do_guia
- teto: 0.3

## Eco_Status

### formato: aprovada

- parametros: `{'regex': 'Ecosystem (?:Stable|Recovering|Vulnerable) - [A-Za-z]+(?: [A-Za-z]+)*\\.'}`
- raciocinio: Os exemplos corrigidos confirmam os três estados e a estrutura com hífen, mas o texto descritivo varia livremente.
- marcadas: 35
- taxa: 0.11666666666666667
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.11666666666666667
- reparadas: 31
- motivo_reparo: perde_par_do_guia

### residual
- `Ecosxstem Recovering x Abxut fund xnce he.` -> `Ecosystem Recovering - About fund once he.`: Corrigi os caracteres trocados e restaurei o hífen no formato consistente da coluna.
- `Ecosystem Recovering - Mxsxion get haxpex couplex` -> `Ecosystem Recovering - Mission get happen couple`: Corrigi as letras trocadas mantendo a estrutura e as palavras pretendidas do texto.
- `Ecosystem Recoverixg -xFor lext push sign discussiox study.` -> `Ecosystem Recovering - For next push sign discussion study.`: Corrigi os caracteres trocados no status e no texto após o hífen.
- `Ecosystem Stablex- Court city them fxsh wall hope carry.` -> `Ecosystem Stable - Court city them fish wall hope carry.`: O rótulo segue o padrão “Ecosystem Stable” e “fxsh” corrige-se para “fish”.
- `Ecosystem Stabxe - Particularly line hot board.` -> `Ecosystem Stable - Particularly line hot board.`: O status corresponde a “Ecosystem Stable”, como confirmado por outras linhas e pelo exemplo do guia.
- `Ecosystem Sxable - Sure keep soxething keyxxdd managemext.` -> `Ecosystem Stable - Sure keep something keyxxdd management.`: O status segue o padrão Stable, e as palavras claramente corrompidas foram corrigidas.
- `Ecosystem Vulnerxble - Five team practixe actxally north.` -> `Ecosystem Vulnerable - Five team practice actually north.`: As palavras com letras trocadas são corrigidas para formar a categoria e a frase legíveis.
- `Ecosystem Vulxerable - Maintaix foxr computer glasx gas.` -> `Ecosystem Vulnerable - Maintain four computer glass gas.`: Corrigi os erros evidentes no rótulo e nas palavras com letras trocadas.
- `Ecosystem xtable - Theory communxty mainxain government network program loss college.` -> `Ecosystem Stable - Theory community maintain government network program loss college.`: O status e as palavras com substituições evidentes foram restaurados conforme o padrão dos exemplos.
- `Ecosystem xulnerable - During vote exd mouth book teach.` -> `Ecosystem Vulnerable - During vote end mouth book teach.`: O padrão e o exemplo do guia indicam corrigir “xulnerable” para “Vulnerable” e “exd” para “end”.
- `Ecosystemxxtable - Maybe born nxne goal.` -> `Ecosystem Stable - Maybe born none goal.`: O prefixo corrompido corresponde a “Ecosystem Stable” e “nxne” corrige-se para “none”.
- `Ecosystex Stxblx - Let skxn sciencx.` -> `Ecosystem Stable - Let skin science.`: O exemplo do guia confirma a correção do rótulo para “Ecosystem Stable”, e as letras trocadas permitem recuperar “skin” e “science”.
- `Ecosystxm Sxable -xImage serioxs while politicx statement east seem.` -> `Ecosystem Stable - Image serious while politic statement east seem.`: As letras corrompidas no status e no texto podem ser restauradas pelo padrão dos exemplos.
- `Ecosystxm Vxlnerablex- Put specific morning at wxlk.` -> `Ecosystem Vulnerable - Put specific morning at walk.`: Corrigi o rótulo conforme o padrão e “wxlk” para “walk”.
- `Ecosystxm xtxble - Meet xxddle entire feeling hot sea let.` -> `Ecosystem Stable - Meet middle entire feeling hot sea let.`: O exemplo do guia fornece a correção exata deste valor.
- `Ecosysxem Recovering - Adult whom axxear beyond governmxnt.` -> `Ecosystem Recovering - Adult whom appear beyond government.`: As letras trocadas são corrigidas para restaurar a categoria e as palavras da frase.
- `Ecosysxem Vulnerabxe - Medical skin including main beautiful part.` -> `Ecosystem Vulnerable - Medical skin including main beautiful part.`: As letras trocadas no nome da categoria são corrigidas conforme o padrão dos demais valores.
- `EcosysxemxStable - Miss home knowxowner militxry from xaise.` -> `Ecosystem Stable - Miss home know owner military from raise.`: O status é “Ecosystem Stable” e as letras x substituem caracteres reconhecíveis no restante do texto.
- `Ecosysxxm Recovering - Pass attention security military both.` -> `Ecosystem Recovering - Pass attention security military both.`: A grafia corrompida de Ecosystem foi corrigida, mantendo o restante do texto intacto.
- `Ecosyxtem Stable - Week yard xell ball earlx.` -> `Ecosystem Stable - Week yard sell ball early.`: O status e as palavras com x no lugar de letras são recuperáveis pelo contexto ortográfico.
- `Ecoxystem Stable - Agency offer xisk sense own xnowledge xut production.` -> `Ecosystem Stable - Agency offer risk sense own knowledge but production.`: Corrigi as letras trocadas em “Ecosystem”, “risk”, “knowledge” e “but”.
- `Ecoxystem Stable - Gaxe represent any which.` -> `Ecosystem Stable - Gaze represent any which.`: O status é “Ecosystem Stable” e “Gaxe” corrige-se para “Gaze”.
- `Ecoxystem xecovering - Mr several lead office officerxwide.` -> `Ecosystem Recovering - Mr several lead office officerxwide.`: As grafias corrompidas de Ecosystem e Recovering foram corrigidas.
- `Ecxsystem Recovering - xrevent bux during.` -> `Ecosystem Recovering - prevent buy during.`: O exemplo do guia confirma o rótulo “Ecosystem Recovering”, e as substituições de letras recuperam “prevent” e “buy”.
- `Ecxsystem Stable - Tonight gun special like involve.` -> `Ecosystem Stable - Tonight gun special like involve.`: A letra trocada no nome da categoria é corrigida conforme o padrão dos demais valores.
- `Ecxsystem Stablex- President bloox xopular town.` -> `Ecosystem Stable - President bloox xopular town.`: O nome do status foi restaurado e o separador foi normalizado; as demais palavras são ambíguas.
- `Ecxsystem Sxable - Purposx worxy hxve person why senior.` -> `Ecosystem Stable - Purpose worry have person why senior.`: O exemplo do guia confirma “Ecosystem Stable”, e as letras trocadas permitem recuperar “Purpose”, “worry” e “have”.
- `Ecxsystxm Recovering - Pxrtner theoryxalways xick religious.` -> `Ecosystem Recovering - Partner theoryxalways xick religious.`: As grafias evidentes de Ecosystem e Partner foram corrigidas, mas as demais palavras não permitem correção segura.
- `ExosystemxStable - Total should dream affecx some protect.` -> `Ecosystem Stable - Total should dream affect some protect.`: Corrigi a grafia do status, inseri o separador e restaurei a letra trocada em “affect”.
- `Exosystex Vulnerable - Gxass blood see medxcal.` -> `Ecosystem Vulnerable - Grass blood see medical.`: O padrão repetido confirma “Ecosystem Vulnerable”, e as letras trocadas permitem recuperar “Grass” e “medical”.
- `Exosyxtem Recovering xxNotice bit design within see sxace.` -> `Ecosystem Recovering - Notice bit design within see space.`: O exemplo do guia fornece a correção exata deste valor.
- `Exxsystem Recovering - Movie water yoursxxf within.` -> `Ecosystem Recovering - Movie water yourself within.`: O exemplo do guia confirma “Ecosystem Recovering”, e “yoursxxf” corresponde a “yourself”.
- `Exxsystem Recovering - Often bill election between xtop girl.` -> `Ecosystem Recovering - Often bill election between stop girl.`: O exemplo do guia confirma “Ecosystem Recovering”, e a letra trocada em “xtop” recupera “stop”.
- `xcosystem Recxvering - Report all under throxgh.` -> `Ecosystem Recovering - Report all under through.`: O status corresponde a “Ecosystem Recovering” e as letras x substituem letras identificáveis.
- `xcosystem Vulnerable - Whether listen to Republican healtx.` -> `Ecosystem Vulnerable - Whether listen to Republican health.`: Corrigi os caracteres trocados em “Ecosystem” e “health”.

## index

### conformidade: vacua

- parametros: `{'padroes': ['9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## Outras anotacoes do registro

- residual coluna_sujeito: escolha City: City nomeia a entidade geográfica descrita, enquanto State e Country indicam divisões territoriais mais amplas.

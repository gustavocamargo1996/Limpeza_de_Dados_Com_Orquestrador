# Raciocinio do limpador environment_sem_guia_2026-10-12_2209

- modelo: gpt-6-luna (openai), raciocinio none
- supervisao: 0 celulas do guia + 0 pares
- chamadas: 13; tokens: 12544
- unidades sem regra pelo teto de chamadas: 0

## City

### dependencia: aprovada

- parametros: `{'determinantes': ['State']}`
- raciocinio: State determina City em 82% dos casos, mas a dependência é imperfeita; a regra pode sinalizar divergências para revisão, sem exceder 30% da coluna.
- marcadas: 54
- taxa: 0.18
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.18
- reparadas: 54
- motivo_reparo: aprovada
- reparo: moda_condicionada
- raciocinio do reparo: A cidade mais comum pode variar conforme o State. Os valores marcados podem divergir da cidade mais comum para seu State. Substituir cada valor pela moda de City entre as linhas com o mesmo State.

## State

### formato: vacua

- parametros: `{'regex': '[A-Z]{2}'}`
- raciocinio: Todos os valores observados têm duas letras maiúsculas; a regra não marca nenhum valor observado.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### dependencia: aprovada

- parametros: `{'determinantes': ['City']}`
- raciocinio: A relação minerada entre City e State tem 54 divergências em 300 linhas, indicando possíveis inconsistências, embora a dependência não seja perfeita.
- marcadas: 54
- taxa: 0.18
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.18
- reparadas: 54
- motivo_reparo: aprovada
- reparo: moda_condicionada
- raciocinio do reparo: Cada cidade tende a corresponder ao estado mais frequente nas linhas com essa mesma cidade. Os estados marcados aparecem em divergências da dependência minerada entre City e State. Substituir cada valor marcado pela moda de State entre as linhas com a mesma City.

## Country

### dominio: vacua

- parametros: `{'valores': ['United States', 'Germany', 'India']}`
- raciocinio: Os três valores observados cobrem as 300 linhas e formam um domínio consistente para Country.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### dependencia: vacua

- parametros: `{'determinantes': ['City']}`
- raciocinio: City determina Country sem divergências nos nove grupos minerados, com cobertura total.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## Climate_Zone

### dominio: vacua

- parametros: `{'valores': ['Temperate', 'Tropical']}`
- raciocinio: Os dois valores observados formam um domínio consistente e a regra não marca nenhum deles.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## Monitoring_Station_ID

### formato: vacua

- parametros: `{'regex': '[A-Za-z]+_?\\d{3}'}`
- raciocinio: Os padrões observados indicam nomes de cidades seguidos por três dígitos, com ou sem sublinhado; esta regra cobre as variantes de formato sem marcar valores observados como inválidos.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## PM2.5

### formato: vacua

- parametros: `{'regex': '\\d{1,3}\\.\\d{1,2}'}`
- raciocinio: Os valores observados são números decimais com uma ou duas casas; o padrão aceita todos os valores listados.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### faixa: vacua

- parametros: `{'minimo': 0, 'maximo': 500}`
- raciocinio: Uma faixa ampla e não negativa é plausível para concentração de PM2.5 e não marca os valores observados.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## Temperature

### formato: vacua

- parametros: `{'regex': '-?\\d+(?:\\.\\d+)?(?:℃)?'}`
- raciocinio: Os valores observados são números decimais, às vezes acompanhados de ℃; esta regra aceita ambos os formatos sem marcar valores observados.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### ausente_disfarcado: vacua

- parametros: `{'sentinelas': ['92.9', '92.9℃', '9.9', '9.9℃', '-9.9', '-9.9℃']}`
- raciocinio: A concentração desses poucos valores em padrões repetidos sugere possíveis códigos de ausência, mas a hipótese é incerta e deve ser validada antes de sinalizar células.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## Measurement_Date

### formato: vacua

- parametros: `{'regex': '(?:\\d{4}-\\d{2}-\\d{2}|\\d{1,2}/\\d{1,2}/\\d{4})'}`
- raciocinio: Os padrões observados indicam datas nos formatos ISO e mês/dia/ano; a regra aceita ambos sem rejeitar valores observados.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## Project_Name

## Eco_Status

## index

## Outras anotacoes do registro


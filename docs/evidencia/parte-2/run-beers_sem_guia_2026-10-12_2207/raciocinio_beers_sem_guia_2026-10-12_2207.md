# Raciocinio do limpador beers_sem_guia_2026-10-12_2207

- modelo: gpt-6-luna (openai), raciocinio none
- supervisao: 0 celulas do guia + 0 pares
- chamadas: 27; tokens: 23580
- unidades sem regra pelo teto de chamadas: 0

## index

## id

### formato: aprovada

- parametros: `{'regex': '\\d{2,4}'}`
- raciocinio: Todos os 300 valores são identificadores numéricos com 1 a 4 dígitos; esta regra permissiva não marca nenhum valor observado.
- marcadas: 1
- taxa: 0.0033333333333333335
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.0033333333333333335
- reparadas: 0
- motivo_reparo: nao_repara

## beer-name

## style

### formato: marca_demais

- parametros: `{'regex': '[A-Za-zÀ-ÿ]+(?:[ /()\\-][A-Za-zÀ-ÿ]+)*'}`
- raciocinio: Os estilos observados são nomes textuais com palavras e separadores como espaços, barras, parênteses e hífens; a regra sinaliza valores com estrutura incompatível.
- marcadas: 93
- taxa: 0.31
- motivo: marca_demais
- teto: 0.3

## ounces

### formato: aprovada

- parametros: `{'regex': '(?:12(?:\\.0)?|16(?:\\.0)?|8\\.4)(?:\\s*(?:oz\\.?|ounce))(?:\\s+(?:Alumi-Tek|Silo Can))?'}`
- raciocinio: Os valores observados representam volumes de 8.4, 12 ou 16 ounces, com variações de unidade, caixa e nome de embalagem; a regra aceita essas variantes sem marcar valores observados como erro.
- marcadas: 32
- taxa: 0.10666666666666667
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.10666666666666667
- reparadas: 27
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: Os volumes são representados numericamente em ounces, como 8.4, 12 ou 16. Os valores marcados incluem unidade e decimal redundante, ou já estão sem unidade. Remover a unidade e o decimal redundante, preservando o volume.

```python
def corrigir_2(valor):
    novo_valor = valor
    if novo_valor.endswith(' OZ.'):
        novo_valor = novo_valor[:-4]
    if novo_valor.endswith('.0'):
        novo_valor = novo_valor[:-2]
    return novo_valor
```

### dominio: vacua

- parametros: `{'valores': ['12.0 oz.', '12.0 ounce', '12.0 oz', '16.0 oz.', '12.0 OZ.', '16.0 ounce', '16.0 oz', '12.0 oz. Alumi-Tek', '16.0 OZ.', '12', '16.0 oz. Alumi-Tek', '8.4 ounce', '12.0 oz. Silo Can', '16.0 oz. Silo Can']}`
- raciocinio: A lista cobre os 14 valores distintos observados, sem rejeitar células presentes no perfil.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## abv

### formato: aprovada

- parametros: `{'regex': '(?:0\\.0[0-9]{1,2}%?|0\\.1[0-9]{1,2}%?)'}`
- raciocinio: Os valores de ABV aparecem como proporções decimais, às vezes com sinal de porcentagem; esta regra identifica formatos numéricos plausíveis sem marcar os valores observados.
- marcadas: 15
- taxa: 0.05
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.05
- reparadas: 13
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: ABV é representado como proporção decimal, com ou sem sinal de porcentagem. Os valores não vazios têm artefatos de precisão de ponto flutuante e um sufixo de porcentagem; há também células vazias. Remover o sufixo e arredondar os valores não vazios para três casas decimais.

```python
def corrigir_3(valor):
    if valor == '' or not valor.endswith('%'):
        return valor
    try:
        return f'{float(valor[:-1]):.3f}'
    except ValueError:
        return valor
```

### faixa: vacua

- parametros: `{'minimo': 0, 'maximo': 0.2}`
- raciocinio: Os ABVs observados estão concentrados entre aproximadamente 0,04 e 0,10, e a faixa permissiva de 0 a 0,2 evita marcar valores válidos comuns.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## ibu

### formato: marca_demais

- parametros: `{'regex': '\\d{1,3}'}`
- raciocinio: Os valores numéricos observados têm de um a três dígitos; a regra não marca os valores não numéricos observados.
- marcadas: 117
- taxa: 0.39
- motivo: marca_demais
- teto: 0.3

### faixa: aprovada

- parametros: `{'minimo': 0, 'maximo': 108}`
- raciocinio: Os valores numéricos observados vão de 9 a 108; esta faixa ampla evita marcar valores observados como erro.
- marcadas: 2
- taxa: 0.006666666666666667
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.006666666666666667
- reparadas: 2
- motivo_reparo: aprovada
- reparo: vizinho_no_dominio
- raciocinio do reparo: Os valores de IBU observados variam de 9 a 108. 138 e 115 excedem o máximo permitido de 108. Substituir cada valor pelo valor válido mais parecido, a até uma edição de distância.

### ausente_disfarcado: marca_demais

- parametros: `{'sentinelas': ['N/A', 'A/A']}`
- raciocinio: N/A e A/A aparecem como representações frequentes de ausência, não como valores de IBU.
- marcadas: 112
- taxa: 0.37333333333333335
- motivo: marca_demais
- teto: 0.3

## brewery_id

### formato: vacua

- parametros: `{'regex': '\\d{1,3}'}`
- raciocinio: Os valores observados são identificadores numéricos de 1 a 3 dígitos; a regra não marca nenhum valor observado.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### dependencia: aprovada

- parametros: `{'determinantes': ['brewery-name']}`
- raciocinio: O nome da cervejaria determina brewery_id com alta consistência (0,997) e cobertura de 0,963.
- marcadas: 1
- taxa: 0.0033333333333333335
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.0033333333333333335
- reparadas: 1
- motivo_reparo: aprovada
- reparo: moda_condicionada
- raciocinio do reparo: Cada brewery-name corresponde consistentemente a um brewery_id. O valor 1 foi marcado como inconsistente com o nome da cervejaria na linha. Substituir pelo brewery_id mais comum entre as linhas com o mesmo brewery-name.

## brewery-name

### dependencia: vacua

- parametros: `{'determinantes': ['brewery_id']}`
- raciocinio: brewery_id determina brewery-name sem divergências nos grupos minerados e cobre 96% das linhas; a regra pode apontar nomes inconsistentes para o mesmo identificador.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## city

### dependencia: aprovada

- parametros: `{'determinantes': ['brewery_id']}`
- raciocinio: A cervejaria determina a cidade com alta consistência e cobertura; a regra pode apontar divergências sem presumir que cidades raras sejam inválidas.
- marcadas: 5
- taxa: 0.016666666666666666
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.016666666666666666
- reparadas: 5
- motivo_reparo: aprovada
- reparo: moda_condicionada
- raciocinio do reparo: Cada brewery_id corresponde consistentemente a uma cidade. Os valores marcados podem divergir da cidade associada ao mesmo brewery_id. Substituir cada valor pela cidade mais comum entre as linhas com o mesmo brewery_id.

### dependencia: superada

- parametros: `{'determinantes': ['brewery-name']}`
- raciocinio: O nome da cervejaria determina a cidade com alta consistência e cobertura; divergências podem indicar células incorretas.
- marcadas: 5
- taxa: 0.016666666666666666
- motivo: superada
- teto: 0.3

## state

### formato: aprovada

- parametros: `{'regex': '[A-Z]{2}'}`
- raciocinio: Os valores não vazios observados seguem o formato de duas letras maiúsculas; a regra não marca nenhum valor mostrado como correto.
- marcadas: 9
- taxa: 0.03
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.03333333333333333
- reparadas: 0
- motivo_reparo: nao_repara

### ausente_disfarcado: aprovada

- parametros: `{'sentinelas': ['']}`
- raciocinio: A string vazia aparece em 9 linhas e representa ausência de estado.
- marcadas: 9
- taxa: 0.03
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.03333333333333333
- reparadas: 0
- motivo_reparo: nao_repara

### dependencia: aprovada

- parametros: `{'determinantes': ['city']}`
- raciocinio: A cidade determina o estado com alta consistência (0,996) e apenas um grupo divergente.
- marcadas: 1
- taxa: 0.0033333333333333335
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.03333333333333333
- reparadas: 1
- motivo_reparo: aprovada
- reparo: moda_condicionada
- raciocinio do reparo: Cada cidade corresponde consistentemente a um estado. O valor marcado diverge do estado mais comum para sua cidade. Substituir pelo estado mais comum entre as linhas com a mesma cidade.

### residual
- `` -> `CA`: A cervejaria 21st Amendment Brewery está localizada em San Francisco, Califórnia, e as demais linhas confirmam CA.

## Outras anotacoes do registro

- residual coluna_sujeito: escolha brewery-name: O nome da cervejaria identifica a entidade descrita; a cidade é compartilhada por várias entidades e brewery_id é apenas um identificador.

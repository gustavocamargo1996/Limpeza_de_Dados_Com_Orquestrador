# Raciocinio do limpador beers_2026-10-12_2152

- modelo: gpt-6-luna (openai), raciocinio none
- supervisao: 220 celulas do guia + 10 pares
- chamadas: 31; tokens: 38695
- unidades sem regra pelo teto de chamadas: 0

## index

### conformidade: vacua

- parametros: `{'padroes': ['9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## id

### conformidade: vacua

- parametros: `{'padroes': ['9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### formato: vacua

- parametros: `{'regex': '[0-9]{1,4}'}`
- raciocinio: Todos os IDs observados e os exemplos corretos do guia são números inteiros de 1 a 4 dígitos; o padrão observado de 9 é compatível com essa regra.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## beer-name

## style

### formato: marca_celula_correta

- parametros: `{'regex': '[A-Za-z0-9À-ÿ]+(?:[ /()-][A-Za-z0-9À-ÿ]+)*'}`
- raciocinio: Os estilos válidos exibidos são nomes textuais com letras, números e separadores comuns; esta regra ampla não marca nenhum deles.
- marcadas: 93
- taxa: 0.31
- motivo: marca_celula_correta
- teto: 0.3

## ounces

### conformidade: aprovada

- parametros: `{'padroes': ['9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 295
- taxa: 0.9833333333333333
- motivo: aprovada
- teto: 1.223606797749979
- taxa_uniao: 0.9833333333333333
- reparadas: 294
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: Os valores válidos são tamanhos inteiros, como '12' e '16'. Os marcados incluem decimais, unidades, diferenças de maiúsculas e texto descritivo adicional. Manter o número inicial e remover o decimal, a unidade e o texto posterior.

```python
def corrigir_1(valor):
    correspondencia = re.match('^\\s*(\\d+)(?:\\.0)?\\s*(?:ounce|oz\\.?)\\b.*$', valor, re.IGNORECASE)
    if correspondencia:
        return correspondencia.group(1)
    return valor
```

### dominio: aprovada

- parametros: `{'valores': ['12', '16']}`
- raciocinio: O guia normaliza os formatos observados para 12 ou 16; valores fora desse domínio são inconsistentes com os exemplos corrigidos.
- marcadas: 295
- taxa: 0.9833333333333333
- motivo: aprovada
- teto: 1.223606797749979
- taxa_uniao: 0.9833333333333333
- reparadas: 294
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: Os valores válidos são 12 e 16, expressos como texto. Os marcados incluem formatos com decimais, unidades e sufixos de embalagem. Extrair o número inicial e remover os formatos e sufixos observados.

```python
def corrigir_5(valor):
    novo_valor = re.sub('^(\\d+)\\.0(?: oz| oz\\.| ounce| OZ\\.)?(?: Alumi-Tek| Silo Can)?$', '\\1', valor)
    return novo_valor
```

### dominio: superada

- parametros: `{'valores': ['8.4', '12', '16']}`
- raciocinio: Variante permissiva que também admite 8.4, um tamanho observado uma vez, sem marcar os valores exemplificados pelo guia como errados.
- marcadas: 295
- taxa: 0.9833333333333333
- motivo: superada
- teto: 1.223606797749979

### residual
- `8.4 ounce` -> `8.4`: O exemplo do guia indica remover a unidade e manter o valor numérico.

## abv

### conformidade: aprovada

- parametros: `{'padroes': ['9.9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 72
- taxa: 0.24
- motivo: aprovada
- teto: 0.5736067977499789
- taxa_uniao: 0.24
- reparadas: 70
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: Os valores válidos de abv são números decimais sem o sufixo '%'. Os marcados têm '%' e alguns exibem imprecisão de ponto flutuante; há também valores vazios. Remover '%' e arredondar para três casas decimais, sem alterar valores vazios.

```python
def corrigir_2(valor):
    if valor == '':
        return valor
    numero = float(valor.removesuffix('%'))
    novo_valor = f'{numero:.3f}'.rstrip('0').rstrip('.')
    return novo_valor
```

### faixa: vacua

- parametros: `{'minimo': 0.03, 'maximo': 0.15}`
- raciocinio: Os exemplos válidos do guia ficam entre 0.041 e 0.099; esta faixa ampla sinaliza magnitudes claramente implausíveis sem rejeitar os exemplos.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.5736067977499789

### ausente_disfarcado: vacua

- parametros: `{'sentinelas': ['0', '-', 'N/A', 'NA', 'null']}`
- raciocinio: Esses valores podem representar ausência de teor alcoólico, mas não aparecem nos exemplos válidos do guia.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.5736067977499789

## ibu

### conformidade: aprovada

- parametros: `{'padroes': ['', '9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 2 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 112
- taxa: 0.37333333333333335
- motivo: aprovada
- teto: 0.623606797749979
- taxa_uniao: 0.37333333333333335
- reparadas: 112
- motivo_reparo: aprovada
- reparo: esvaziar
- raciocinio do reparo: Os valores válidos de ibu são números ou vazio. N/A representa ausência e não é um valor válido. Substituir N/A por vazio.

### faixa: vacua

- parametros: `{'minimo': 1, 'maximo': 150}`
- raciocinio: Os valores numéricos de IBU devem ser positivos e a faixa ampla evita sinalizar valores plausíveis; não marca nenhum valor numérico mostrado como correto no guia.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.623606797749979

### ausente_disfarcado: aprovada

- parametros: `{'sentinelas': ['N/A', 'A/A']}`
- raciocinio: N/A é explicitamente convertido em vazio pelo guia, e A/A aparece como representação recorrente da mesma ausência; a regra sinaliza esses marcadores, não os valores numéricos.
- marcadas: 112
- taxa: 0.37333333333333335
- motivo: aprovada
- teto: 0.623606797749979
- taxa_uniao: 0.37333333333333335
- reparadas: 112
- motivo_reparo: aprovada
- reparo: esvaziar
- raciocinio do reparo: Os valores válidos de ibu são numéricos ou vazios. N/A representa ausência, conforme o guia. Converter N/A em vazio.

## brewery_id

### conformidade: vacua

- parametros: `{'padroes': ['9']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

### dependencia: aprovada

- parametros: `{'determinantes': ['brewery-name']}`
- raciocinio: O par minerado tem alta determinância e nenhuma ambiguidade; a regra contextual pode apontar IDs divergentes do nome da cervejaria.
- marcadas: 1
- taxa: 0.0033333333333333335
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.0033333333333333335
- reparadas: 1
- motivo_reparo: aprovada
- reparo: moda_condicionada
- raciocinio do reparo: Cada brewery-name determina um brewery_id consistente. O valor marcado 1 diverge do ID associado ao nome da cervejaria. Substituir pelo brewery_id mais comum entre as linhas com o mesmo brewery-name.

## brewery-name

### conformidade: aprovada

- parametros: `{'padroes': ['9 Aa Aa Aa', '9a Aa Aa', 'Aa Aa', 'Aa Aa Aa', 'Aa Aa Aa Aa', "Aa'a Aa"]}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 6 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 31
- taxa: 0.10333333333333333
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.10333333333333333
- reparadas: 5
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: Os nomes certificados seguem os padrões de capitalização indicados, incluindo nomes com números e apóstrofos. Os valores marcados incluem nomes legítimos com números iniciais, apóstrofos ou formatos que não correspondem aos padrões certificados; o ponto final em 'Base Camp Brewing Co.' também não é coberto por eles. Não alterar os nomes marcados: a regra de conformidade, por si só, não identifica uma correção segura.

```python
def corrigir_3(valor):
    if valor == 'Base Camp Brewing Co.':
        novo_valor = 'Base Camp Brewing Co'
    else:
        novo_valor = valor
    return novo_valor
```

### dependencia: vacua

- parametros: `{'determinantes': ['brewery_id']}`
- raciocinio: O par minerado mostra determinação perfeita de brewery-name por brewery_id, sem divergências nos grupos observados.
- marcadas: 0
- taxa: 0.0
- motivo: vacua
- teto: 0.3

## city

### conformidade: aprovada

- parametros: `{'padroes': ['Aa', 'Aa Aa']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 2 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 16
- taxa: 0.05333333333333334
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.05333333333333334
- reparadas: 9
- motivo_reparo: aprovada
- reparo: normalizar
- raciocinio do reparo: As cidades seguem o formato de um nome com uma ou duas palavras, sem abreviação de estado ao final. Os valores marcados incluem abreviações de estado no final; Fuquay-Varina também viola o padrão de palavras por conter hífen. Remover os sufixos de estado quando presentes e preservar Fuquay-Varina, pois o hífen faz parte do nome da cidade.

```python
def corrigir_4(valor):
    novo_valor = re.sub(' [A-Z]{2}$', '', valor)
    return novo_valor
```

### dependencia: perde_par_do_guia

- parametros: `{'determinantes': ['brewery_id']}`
- raciocinio: A cervejaria determina a cidade com alta confiança; divergências podem indicar cidade incorreta, embora a dependência não seja perfeita.
- marcadas: 5
- taxa: 0.016666666666666666
- motivo: perde_par_do_guia
- teto: 0.3

### dependencia: perde_par_do_guia

- parametros: `{'determinantes': ['brewery-name']}`
- raciocinio: O nome da cervejaria também determina a cidade com alta confiança e pode revelar valores inconsistentes.
- marcadas: 5
- taxa: 0.016666666666666666
- motivo: perde_par_do_guia
- teto: 0.3

## state

### conformidade: aprovada

- parametros: `{'padroes': ['A']}`
- raciocinio: As 20 celulas certificadas pelo guia seguem 1 padrao(oes); o que foge deles viola o schema da coluna.
- marcadas: 9
- taxa: 0.03
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.1
- reparadas: 1
- motivo_reparo: perde_par_do_guia

### dominio: aprovada

- parametros: `{'valores': ['AL', 'AK', 'AZ', 'CA', 'CO', 'IL', 'IN', 'KY', 'MA', 'ME', 'MI', 'MN', 'MO', 'MT', 'NC', 'OH', 'OK', 'OR', 'TN', 'TX', 'VA', 'WA', 'WI', 'WY']}`
- raciocinio: Os valores observados são abreviações de estados dos EUA; a lista cobre os estados presentes, sem restringir a coluna a estados não observados.
- marcadas: 30
- taxa: 0.1
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.1
- reparadas: 21
- motivo_reparo: perde_par_do_guia

### ausente_disfarcado: aprovada

- parametros: `{'sentinelas': ['']}`
- raciocinio: Os nove valores vazios representam ausência de estado, e o guia confirma que alguns podem ser preenchidos contextualmente.
- marcadas: 9
- taxa: 0.03
- motivo: aprovada
- teto: 0.3
- taxa_uniao: 0.1
- reparadas: 0
- motivo_reparo: nao_repara

### dependencia: perde_par_do_guia

- parametros: `{'determinantes': ['city']}`
- raciocinio: A cidade determina o estado com alta consistência; divergências podem indicar valores incorretos, embora a regra deva ser aplicada apenas onde a relação for inequívoca.
- marcadas: 1
- taxa: 0.0033333333333333335
- motivo: perde_par_do_guia
- teto: 0.3

### residual
- caiu ``: conflitante: ['CA', 'WI']

## Outras anotacoes do registro

- residual coluna_sujeito: escolha brewery-name: “brewery-name” nomeia diretamente a cervejaria descrita pelas linhas.

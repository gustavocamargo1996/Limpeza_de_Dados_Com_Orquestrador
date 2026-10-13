"""Limpador gerado pela POC 2 de limpeza de dados: beers_2026-10-12_2152.

Modelo gpt-6-luna (openai), 31 chamadas; guia de 20 linhas e 10 pares.

AVISO: este arquivo roda SEM o portao AST que validou as funcoes corrigir_* na geracao.
Revise antes de usar em producao.

Memoria congelada: RESIDUAL e o dominio de vizinho_no_dominio valem para valores
ja vistos na tabela de geracao; nao cobrem valor inedito.
"""
import argparse
import re

# o motor traz o proprio import de pandas
# --- motor.py, copia byte a byte: inicio ---
"""Unica implementacao de aplicacao de regra; o limpador gerado embute este texto."""
import pandas as pd

NIVEL_SCHEMA = 3
TIPOS = (
    "conformidade", "formato", "dominio", "faixa", "ausente_disfarcado", "dependencia"
)


def padrao(valor, nivel=1):
    """Generaliza o valor em classes de caractere; 2 comprime com contagem, 3 sem."""
    classes = "".join(
        "A" if c.isupper() else "a" if c.islower() else "9" if c.isdigit() else c
        for c in valor
    )
    if nivel == 1:
        return classes
    comprimido = []
    for c in classes:
        if comprimido and comprimido[-1][0] == c:
            comprimido[-1][1] += 1
        else:
            comprimido.append([c, 1])
    if nivel == 3:
        return "".join(c for c, _ in comprimido)
    return "".join(f"{c}{n}" if n > 1 else c for c, n in comprimido)


def detectar(df, coluna, tipo, parametros, dominancia=0.70):
    """Devolve a mascara booleana das celulas que a regra considera erradas."""
    if tipo == "dependencia":
        return divergentes_da_moda(df, parametros["determinantes"], coluna, dominancia)
    serie = df[coluna].astype(str)
    if tipo == "conformidade":
        return ~serie.map(lambda v: padrao(v, NIVEL_SCHEMA)).isin(parametros["padroes"])
    if tipo == "formato":
        return ~serie.str.fullmatch(parametros["regex"], na=False)
    if tipo == "dominio":
        return ~serie.isin(parametros["valores"])
    if tipo == "faixa":
        numeros = pd.to_numeric(serie, errors="coerce")
        # Comparacao com NaN ja devolve False, entao o que nao e numero nunca entra.
        fora = (numeros < parametros["minimo"]) | (numeros > parametros["maximo"])
        return fora
    if tipo == "ausente_disfarcado":
        return serie.isin(parametros["sentinelas"])
    raise ValueError(f"tipo de regra desconhecido: {tipo}")


def moda_dominante(serie, dominancia):
    """O valor majoritario da serie, ou None quando nao existe maioria clara."""
    if len(serie) < 2:
        return None
    contagem = serie.value_counts()
    if contagem.iloc[0] / len(serie) < dominancia:
        return None
    return contagem.index[0]


def divergentes_da_moda(df, determinantes, coluna, dominancia):
    """Marca quem discorda da moda do grupo, pulando grupo sem maioria clara."""
    mascara = pd.Series(False, index=df.index)
    for _, grupo in df.groupby(determinantes, sort=False):
        moda = moda_dominante(grupo[coluna], dominancia)
        if moda is None:
            continue
        mascara.loc[grupo.index[grupo[coluna] != moda]] = True
    return mascara


ESTRATEGIAS = (
    "normalizar", "moda_condicionada", "vizinho_no_dominio", "dicionario", "esvaziar"
)


def distancia_edicao(a, b):
    """Damerau-Levenshtein restrita: transposicao de adjacentes custa uma edicao."""
    anterior2, anterior = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        atual = [i]
        for j, cb in enumerate(b, start=1):
            custo = min(
                anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (ca != cb)
            )
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                custo = min(custo, anterior2[j - 2] + 1)
            atual.append(custo)
        anterior2, anterior = anterior, atual
    return anterior[-1]


def reparar(df, coluna, estrategia, parametros, mascara, funcoes=None, dominancia=0.70):
    """Aplica a estrategia onde a mascara e True; devolve (df novo, mascara do que mudou)."""
    novo = df.copy()
    reparada = pd.Series(False, index=df.index)
    alvos = df.index[mascara.fillna(False)]
    if estrategia == "moda_condicionada":
        return _reparar_por_moda(
            novo, df, coluna, parametros["determinantes"], alvos, dominancia, reparada
        )
    escalar = _escalar(estrategia, parametros, funcoes)
    for linha in alvos:
        antes = str(df.at[linha, coluna])
        try:
            depois = escalar(antes)
        except Exception:
            # Degradacao nomeada: a celula fica flag. Ver docs/DECISOES.md#funcao-que-lanca.
            depois = None
        # None e "nao sei reparar"; devolver o mesmo valor nao conta como reparo.
        if depois is not None and depois != antes:
            novo.at[linha, coluna] = depois
            reparada.loc[linha] = True
    return novo, reparada


def _escalar(estrategia, parametros, funcoes):
    """A funcao valor -> valor novo, ou None para nao reparar, de cada estrategia escalar."""
    if estrategia == "normalizar":
        return (funcoes or {})[parametros["funcao"]]
    if estrategia == "vizinho_no_dominio":
        return lambda v: _mais_proximo(v, parametros["dominio"], parametros["distancia"])
    if estrategia == "dicionario":
        return parametros["mapa"].get
    if estrategia == "esvaziar":
        return lambda v: ""
    raise ValueError(f"estrategia de reparo desconhecida: {estrategia}")


def _mais_proximo(valor, dominio, distancia_maxima):
    """O valor do dominio mais proximo dentro do limite, ou None."""
    melhor, menor = None, distancia_maxima + 1
    for candidato in dominio:
        d = distancia_edicao(valor, candidato)
        if d < menor:
            melhor, menor = candidato, d
    return melhor


def vizinhos_ordenados(frequencia):
    """Valores com 2+ ocorrencias, do mais frequente ao menos; empate em ordem alfabetica."""
    # A ordem total faz o reparo ser deterministico, sem depender do hash das strings.
    ordem = sorted(frequencia.items(), key=lambda par: (-par[1], par[0]))
    return [v for v, n in ordem if n >= 2]


def _reparar_por_moda(novo, original, coluna, determinantes, alvos, dominancia, reparada):
    """Corrige o determinante quando ele e um erro de digitacao, depois usa a moda do grupo."""
    for det in determinantes:
        frequencia = original[det].value_counts()
        raros = {v for v, n in frequencia.items() if n == 1}
        comuns = vizinhos_ordenados(frequencia)
        for linha in alvos:
            valor = original.at[linha, det]
            if valor not in raros:
                continue
            vizinho = next(
                (c for c in comuns if distancia_edicao(str(valor), str(c)) == 1), None
            )
            if vizinho is not None:
                novo.at[linha, det] = vizinho
                reparada.loc[linha] = True

    for _, grupo in novo.groupby(determinantes, sort=False):
        pendentes = grupo.index.intersection(alvos)
        if pendentes.empty:
            continue
        moda = moda_dominante(grupo[coluna], dominancia)
        if moda is None:
            continue
        for linha in pendentes:
            if novo.at[linha, coluna] != moda:
                novo.at[linha, coluna] = moda
                reparada.loc[linha] = True
    return novo, reparada


def aplicar_regras(df, regras, residual, funcoes, dominancia=0.70):
    """Aplica as regras lendo sempre o original; devolve (df novo, flags, fontes)."""
    novo = df.copy()
    marcadas = pd.DataFrame(False, index=df.index, columns=df.columns)
    fontes = pd.DataFrame("", index=df.index, columns=df.columns)
    for regra in regras:
        coluna, estrategia = regra["coluna"], regra["estrategia"]
        mascara = detectar(df, coluna, regra["tipo"], regra["deteccao"], dominancia).fillna(False)
        marcadas[coluna] = marcadas[coluna] | mascara
        if estrategia is None:
            continue
        reparado, _ = reparar(df, coluna, estrategia, regra["reparo"], mascara, funcoes, dominancia)
        # Quem escreve primeiro vence; a moda pode escrever tambem no determinante.
        livre = (reparado != df) & (fontes == "")
        novo = novo.mask(livre, reparado)
        fontes = fontes.mask(livre, f"{regra['tipo']}/{estrategia}")
    for coluna, mapa in residual.items():
        alvo = marcadas[coluna] & (fontes[coluna] == "") & df[coluna].isin(list(mapa))
        novo.loc[alvo, coluna] = df.loc[alvo, coluna].map(mapa)
        fontes.loc[alvo, coluna] = "residual"
    return novo, marcadas & (fontes == ""), fontes
# --- motor.py: fim ---

GERACAO_TRUNCADA = False
UNIDADES_DEGRADADAS_POR_TETO = 0
DOMINANCIA = 0.7
REGRAS = [{'coluna': 'ounces',
  'deteccao': {'padroes': ['9']},
  'estrategia': 'normalizar',
  'reparo': {'funcao': 'corrigir_1',
             'transformacao': 'Extrair o número inteiro inicial e remover o sufixo de unidade '
                              "(como ' ounce', ' oz' ou ' oz.') e qualquer texto descritivo "
                              "posterior, como ' Alumi-Tek' ou ' Silo Can'; remover também o "
                              "decimal '.0'."},
  'tipo': 'conformidade'},
 {'coluna': 'abv',
  'deteccao': {'padroes': ['9.9']},
  'estrategia': 'normalizar',
  'reparo': {'funcao': 'corrigir_2',
             'transformacao': "Remover o sufixo '%' e arredondar o valor numérico resultante para "
                              'três casas decimais, removendo zeros finais desnecessários; '
                              'preservar valores vazios como vazios.'},
  'tipo': 'conformidade'},
 {'coluna': 'ibu',
  'deteccao': {'padroes': ['', '9']},
  'estrategia': 'esvaziar',
  'reparo': {},
  'tipo': 'conformidade'},
 {'coluna': 'brewery-name',
  'deteccao': {'padroes': ['9 Aa Aa Aa',
                           '9a Aa Aa',
                           'Aa Aa',
                           'Aa Aa Aa',
                           'Aa Aa Aa Aa',
                           "Aa'a Aa"]},
  'estrategia': 'normalizar',
  'reparo': {'funcao': 'corrigir_3',
             'transformacao': "Remover o ponto final de 'Base Camp Brewing Co.'; para os demais "
                              'valores, preservar o texto exatamente como está.'},
  'tipo': 'conformidade'},
 {'coluna': 'city',
  'deteccao': {'padroes': ['Aa', 'Aa Aa']},
  'estrategia': 'normalizar',
  'reparo': {'funcao': 'corrigir_4',
             'transformacao': 'Remover do final da cidade um sufixo de espaço seguido por duas '
                              'letras maiúsculas que representam a abreviação do estado; preservar '
                              'o nome da cidade, incluindo hífens.'},
  'tipo': 'conformidade'},
 {'coluna': 'state',
  'deteccao': {'padroes': ['A']},
  'estrategia': None,
  'reparo': None,
  'tipo': 'conformidade'},
 {'coluna': 'ounces',
  'deteccao': {'valores': ['12', '16']},
  'estrategia': 'normalizar',
  'reparo': {'funcao': 'corrigir_5',
             'transformacao': 'Extrair o número inicial e remover a parte decimal .0 e o sufixo de '
                              "unidade (' oz', ' oz.', ' ounce' ou ' OZ.'); ignorar também os "
                              "sufixos ' Alumi-Tek' e ' Silo Can'. Manter o número extraído como "
                              'texto.'},
  'tipo': 'dominio'},
 {'coluna': 'state',
  'deteccao': {'valores': ['AL',
                           'AK',
                           'AZ',
                           'CA',
                           'CO',
                           'IL',
                           'IN',
                           'KY',
                           'MA',
                           'ME',
                           'MI',
                           'MN',
                           'MO',
                           'MT',
                           'NC',
                           'OH',
                           'OK',
                           'OR',
                           'TN',
                           'TX',
                           'VA',
                           'WA',
                           'WI',
                           'WY']},
  'estrategia': None,
  'reparo': None,
  'tipo': 'dominio'},
 {'coluna': 'ibu',
  'deteccao': {'sentinelas': ['N/A', 'A/A']},
  'estrategia': 'esvaziar',
  'reparo': {},
  'tipo': 'ausente_disfarcado'},
 {'coluna': 'state',
  'deteccao': {'sentinelas': ['']},
  'estrategia': None,
  'reparo': None,
  'tipo': 'ausente_disfarcado'},
 {'coluna': 'brewery_id',
  'deteccao': {'determinantes': ['brewery-name']},
  'estrategia': 'moda_condicionada',
  'reparo': {'determinantes': ['brewery-name']},
  'tipo': 'dependencia'}]
RESIDUAL = {'ounces': {'8.4 ounce': '8.4'}}


def corrigir_1(valor):
    correspondencia = re.match('^\\s*(\\d+)(?:\\.0)?\\s*(?:ounce|oz\\.?)\\b.*$', valor, re.IGNORECASE)
    if correspondencia:
        return correspondencia.group(1)
    return valor


def corrigir_2(valor):
    if valor == '':
        return valor
    numero = float(valor.removesuffix('%'))
    novo_valor = f'{numero:.3f}'.rstrip('0').rstrip('.')
    return novo_valor


def corrigir_3(valor):
    if valor == 'Base Camp Brewing Co.':
        novo_valor = 'Base Camp Brewing Co'
    else:
        novo_valor = valor
    return novo_valor


def corrigir_4(valor):
    novo_valor = re.sub(' [A-Z]{2}$', '', valor)
    return novo_valor


def corrigir_5(valor):
    novo_valor = re.sub('^(\\d+)\\.0(?: oz| oz\\.| ounce| OZ\\.)?(?: Alumi-Tek| Silo Can)?$', '\\1', valor)
    return novo_valor

FUNCOES = {'corrigir_1': corrigir_1, 'corrigir_2': corrigir_2, 'corrigir_3': corrigir_3, 'corrigir_4': corrigir_4, 'corrigir_5': corrigir_5}


def aplicar_detalhado(df):
    """Aplica as regras congeladas; devolve (df corrigido, flags, fontes)."""
    return aplicar_regras(df, REGRAS, RESIDUAL, FUNCOES, DOMINANCIA)


def aplicar(df):
    """Aplica as regras congeladas; devolve (df corrigido, flags)."""
    corrigido, flags, _ = aplicar_detalhado(df)
    return corrigido, flags


def main():
    ap = argparse.ArgumentParser(description="Aplica este limpador a um CSV")
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--flags", help="CSV booleano das celulas marcadas e nao reparadas")
    args = ap.parse_args()
    df = pd.read_csv(args.entrada, dtype=str, keep_default_na=False, na_values=[])
    corrigido, flags = aplicar(df)
    corrigido.to_csv(args.saida, index=False)
    if args.flags:
        flags.to_csv(args.flags, index=False)


if __name__ == "__main__":
    main()

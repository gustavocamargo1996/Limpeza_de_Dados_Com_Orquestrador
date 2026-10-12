"""Unica implementacao de aplicacao de regra; o limpador gerado embute este texto."""
import pandas as pd

TIPOS = ("formato", "dominio", "faixa", "ausente_disfarcado", "dependencia")


def detectar(df, coluna, tipo, parametros, dominancia=0.70):
    """Devolve a mascara booleana das celulas que a regra considera erradas."""
    if tipo == "dependencia":
        return divergentes_da_moda(df, parametros["determinantes"], coluna, dominancia)
    serie = df[coluna].astype(str)
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
    """Aplica a estrategia onde a mascara e True; devolve (df novo, mascara reparada)."""
    novo = df.copy()
    reparada = pd.Series(False, index=df.index)
    alvos = df.index[mascara.fillna(False)]

    if estrategia == "normalizar":
        funcao = (funcoes or {})[parametros["funcao"]]
        for linha in alvos:
            novo.at[linha, coluna] = funcao(str(df.at[linha, coluna]))
            reparada.loc[linha] = novo.at[linha, coluna] != df.at[linha, coluna]
        return novo, reparada

    if estrategia == "moda_condicionada":
        return _reparar_por_moda(
            novo, df, coluna, parametros["determinantes"], alvos, dominancia, reparada
        )

    if estrategia == "vizinho_no_dominio":
        for linha in alvos:
            vizinho = _mais_proximo(
                str(df.at[linha, coluna]), parametros["dominio"], parametros["distancia"]
            )
            if vizinho is not None:
                novo.at[linha, coluna] = vizinho
                reparada.loc[linha] = True
        return novo, reparada

    if estrategia == "dicionario":
        mapa = parametros["mapa"]
        for linha in alvos:
            valor = str(df.at[linha, coluna])
            if valor in mapa:
                novo.at[linha, coluna] = mapa[valor]
                reparada.loc[linha] = True
        return novo, reparada

    if estrategia == "esvaziar":
        for linha in alvos:
            novo.at[linha, coluna] = ""
            reparada.loc[linha] = df.at[linha, coluna] != ""
        return novo, reparada

    raise ValueError(f"estrategia de reparo desconhecida: {estrategia}")


def _mais_proximo(valor, dominio, distancia_maxima):
    """O valor do dominio mais proximo, ou None se nenhum estiver perto o bastante."""
    melhor, menor = None, distancia_maxima + 1
    for candidato in dominio:
        d = distancia_edicao(valor, candidato)
        if d < menor:
            melhor, menor = candidato, d
    return melhor if menor <= distancia_maxima else None


def _reparar_por_moda(novo, original, coluna, determinantes, alvos, dominancia, reparada):
    """Corrige o determinante quando ele e um erro de digitacao, depois usa a moda do grupo."""
    for det in determinantes:
        frequencia = original[det].value_counts()
        raros = [v for v, n in frequencia.items() if n == 1]
        comuns = [v for v, n in frequencia.items() if n >= 2]
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

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

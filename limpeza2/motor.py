"""Unica implementacao de aplicacao de regra; o limpador gerado embute este texto."""
import pandas as pd

NIVEL_SCHEMA = 3
TIPOS = (
    "formato", "dominio", "faixa", "ausente_disfarcado", "dependencia", "conformidade"
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

"""Calcula os limites que o guia sustenta para uma coluna, sem olhar a candidata."""
from math import sqrt

from limpeza2 import config


def guia_na_coluna(entrada, coluna):
    """O sujo e o guia da coluna nas linhas do guia, ou None se o guia nao tem a coluna."""
    if coluna not in entrada.guia_linhas.columns:
        return None
    linhas = entrada.guia_linhas.index.intersection(entrada.sujo.index)
    return entrada.sujo.loc[linhas, coluna], entrada.guia_linhas.loc[linhas, coluna]


def teto_da_coluna(entrada, coluna):
    """O teto de marcacao da coluna: o a priori, ou a taxa suja do guia mais 2 erros padrao."""
    par = guia_na_coluna(entrada, coluna)
    if par is None or len(par[0]) == 0:
        return config.TETO_MARCACAO
    sujo, certo = par
    # Margem de 2 erros padrao de uma proporcao no pior caso (p = 0,5).
    return max(config.TETO_MARCACAO, float((sujo != certo).mean()) + 2 * sqrt(0.25 / len(sujo)))


def valores_certificados(entrada, coluna):
    """Os valores que o guia mostra como corretos na coluna."""
    if coluna not in entrada.guia_linhas.columns:
        return set()
    return set(entrada.guia_linhas[coluna])


def celulas_sujas_do_guia(entrada, coluna):
    """As celulas da coluna em que o guia corrige o sujo, no formato (linha, coluna, limpo)."""
    par = guia_na_coluna(entrada, coluna)
    if par is None:
        return []
    sujo, certo = par
    return [(int(linha), coluna, certo[linha]) for linha in sujo.index[sujo != certo]]


def exemplos_do_guia(entrada, coluna):
    """Os pares (sujo, limpo) distintos que o guia mostra na coluna, das linhas e dos pares."""
    par = guia_na_coluna(entrada, coluna)
    vistos = set() if par is None else {(s, c) for s, c in zip(*par) if s != c}
    pares = entrada.guia_pares[entrada.guia_pares["coluna"] == coluna]
    return sorted(vistos | set(zip(pares["sujo"], pares["limpo"])))

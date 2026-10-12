"""Calcula os limites que o guia sustenta para uma coluna, sem olhar a candidata."""
from math import sqrt

import pandas as pd

from limpeza2 import config


def teto_da_coluna(entrada, coluna):
    """O teto de marcacao da coluna: o a priori, ou a taxa suja do guia mais 2 erros padrao."""
    linhas = entrada.guia_linhas.index.intersection(entrada.sujo.index)
    if coluna not in entrada.guia_linhas.columns or len(linhas) == 0:
        return config.TETO_MARCACAO
    certo = entrada.guia_linhas.loc[linhas, coluna]
    suja = float((entrada.sujo.loc[linhas, coluna] != certo).mean())
    # Margem de 2 erros padrao de uma proporcao no pior caso (p = 0,5).
    return max(config.TETO_MARCACAO, suja + 2 * sqrt(0.25 / len(linhas)))


def valores_certificados(entrada, coluna):
    """Os valores que o guia mostra como corretos na coluna."""
    if coluna not in entrada.guia_linhas.columns:
        return set()
    return set(entrada.guia_linhas[coluna])


def taxa_da_uniao(mascaras):
    """A fracao de celulas marcadas por ao menos uma das mascaras."""
    return float(pd.concat(mascaras, axis=1).any(axis=1).mean())


def celulas_sujas_do_guia(entrada, coluna):
    """As celulas da coluna em que o guia corrige o sujo, no formato (linha, coluna, limpo)."""
    if coluna not in entrada.guia_linhas.columns:
        return []
    linhas = entrada.guia_linhas.index.intersection(entrada.sujo.index)
    guia = entrada.guia_linhas.loc[linhas, coluna]
    return [(int(linha), coluna, guia[linha]) for linha in linhas[entrada.sujo.loc[linhas, coluna] != guia]]


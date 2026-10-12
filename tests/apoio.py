"""Apoio dos testes: entrada montada a mao e o duble do provedor de LLM."""
import pandas as pd

from limpeza2.tipos import Entrada, Perfil


def monta_entrada(sujo, linhas_guia=(), pares=(), corrigidos=None):
    """O guia traz o valor do sujo, salvo nas celulas de `corrigidos` {(linha, coluna): valor}."""
    guia_linhas = sujo.loc[list(linhas_guia)].copy() if linhas_guia else pd.DataFrame(
        columns=sujo.columns
    )
    for (linha, coluna), valor in (corrigidos or {}).items():
        guia_linhas.at[linha, coluna] = valor
    guia_pares = pd.DataFrame(
        list(pares), columns=["linha", "coluna", "sujo", "limpo"]
    ) if pares else pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"])
    return Entrada(
        sujo=sujo,
        guia_linhas=guia_linhas,
        guia_pares=guia_pares,
        perfil=Perfil(colunas={}, pares={}, candidatas_sujeito=[]),
    )

"""Deriva o schema de cada coluna das celulas que o guia certificou; ver docs/DECISOES.md#conformidade-de-schema."""
from limpeza2 import config
from limpeza2.motor import NIVEL_SCHEMA, padrao
from limpeza2.tipos import Candidata


def schema_da_coluna(entrada, coluna):
    """Os padroes de nivel 3 das celulas do guia na coluna, ou None quando ela nao tem schema."""
    guia = entrada.guia_linhas
    if coluna not in guia.columns or len(guia) == 0:
        return None
    padroes = {padrao(str(v), NIVEL_SCHEMA) for v in guia[coluna]}
    if len(padroes) > config.FRACAO_PADROES_SCHEMA * len(guia):
        return None
    return padroes


def candidatas_de_conformidade(entrada):
    """Uma candidata de conformidade por coluna do sujo que tem schema."""
    candidatas = []
    for coluna in entrada.sujo.columns:
        padroes = schema_da_coluna(entrada, coluna)
        if padroes is None:
            continue
        candidatas.append(Candidata(
            coluna=coluna, tipo="conformidade", parametros={"padroes": sorted(padroes)},
            raciocinio=(
                f"As {len(entrada.guia_linhas)} celulas certificadas pelo guia seguem "
                f"{len(padroes)} padrao(oes); o que foge deles viola o schema da coluna."
            ),
        ))
    return candidatas

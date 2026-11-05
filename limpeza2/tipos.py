"""O que viaja entre as etapas, ate o limpador gerado."""
from dataclasses import dataclass, field

import pandas as pd

from limpeza2.motor import TIPOS


@dataclass
class Perfil:
    """Estatisticas deterministicas do sujo, por coluna e por par de colunas."""

    colunas: dict
    pares: dict
    candidatas_sujeito: list


@dataclass
class Entrada:
    """O que a etapa 1 entrega para todas as outras."""

    sujo: pd.DataFrame
    guia_linhas: pd.DataFrame
    guia_pares: pd.DataFrame
    perfil: Perfil
    decisoes: list = field(default_factory=list)

    def decisao(self, coluna, tipo, parametros):
        """A decisao do usuario sobre a regra (coluna, tipo, parametros), ou None."""
        chave = (coluna, tipo, parametros)
        return next((d for d in self.decisoes
                     if (d["coluna"], d["tipo"], d["parametros"]) == chave), None)


@dataclass
class Candidata:
    """Uma regra de deteccao proposta pelo detector, antes do crivo."""

    coluna: str
    tipo: str
    parametros: dict
    raciocinio: str
    metricas: dict = field(default_factory=dict)


@dataclass
class Reparo:
    """Uma deteccao aprovada, com a estrategia de correcao escolhida."""

    candidata: Candidata
    estrategia: str
    parametros: dict
    raciocinio: str
    codigo: str | None = None


@dataclass
class Residual:
    """Dicionario de substituicao congelado no limpador, de uma coluna."""

    coluna: str
    mapa: dict
    justificativas: dict
    caidas: dict = field(default_factory=dict)


def regras_literais(deteccoes, reparos):
    """As regras na forma literal que o limpador embute, na ordem do catalogo de tipos."""
    reparo_de = {id(r.candidata): r for r in reparos}
    regras = []
    for c in sorted(deteccoes, key=lambda c: TIPOS.index(c.tipo)):
        r = reparo_de.get(id(c))
        regras.append({
            "coluna": c.coluna, "tipo": c.tipo, "deteccao": c.parametros,
            "estrategia": r.estrategia if r else None, "reparo": r.parametros if r else None,
        })
    return regras

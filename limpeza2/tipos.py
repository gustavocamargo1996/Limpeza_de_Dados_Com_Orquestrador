"""Os tipos que viajam entre as etapas da espinha."""
from dataclasses import dataclass, field

import pandas as pd


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

"""Etapa 1: perfila a tabela suja, lida como texto literal."""
import json
from pathlib import Path

import pandas as pd

from limpeza2 import config
from limpeza2.motor import padrao
from limpeza2.tipos import Entrada, Perfil

FREQUENTES = 15
RAROS = 10


def perfilar_coluna(serie):
    """Estatisticas de uma coluna: distintos, vazios, valores e padroes."""
    contagem = serie.value_counts()
    padroes = serie.map(lambda v: padrao(v, 2)).value_counts()
    comprimentos = serie.str.len()
    return {
        "n_distintos": int(serie.nunique()),
        "n_vazios": int((serie == "").sum()),
        "frequentes": [(v, int(n)) for v, n in contagem.head(FREQUENTES).items()],
        "raros": [(v, int(n)) for v, n in contagem.tail(RAROS).items()],
        "padroes": [(v, int(n)) for v, n in padroes.head(FREQUENTES).items()],
        "comprimentos": (int(comprimentos.min()), int(comprimentos.max())) if len(serie) else (0, 0),
    }


def perfilar_par(df, determinante, determinado, dominancia):
    """Os cinco numeros que medem se `determinante` determina `determinado`, so no sujo."""
    n_linhas = n_moda = n_grupos = n_ambiguos = 0
    for _, grupo in df.groupby(determinante, sort=False):
        if len(grupo) < 2:
            continue
        contagem = grupo[determinado].value_counts()
        n_grupos += 1
        n_linhas += len(grupo)
        n_moda += int(contagem.iloc[0])
        if contagem.iloc[0] / len(grupo) < dominancia:
            n_ambiguos += 1
    if n_grupos == 0:
        return {"det": 0.0, "n_grupos": 0, "n_divergentes": 0, "frac_ambiguos": 0.0, "cobertura": 0.0}
    return {
        "det": n_moda / n_linhas,
        "n_grupos": n_grupos,
        "n_divergentes": n_linhas - n_moda,
        "frac_ambiguos": n_ambiguos / n_grupos,
        "cobertura": n_linhas / len(df),
    }


def perfilar(caminho_sujo, caminho_guia):
    """Le o sujo e o guia e devolve a Entrada que as outras etapas consomem."""
    sujo = pd.read_csv(caminho_sujo, **config.LER_CSV)
    guia_linhas, guia_pares = _ler_guia(caminho_guia, sujo.columns)

    colunas = {c: perfilar_coluna(sujo[c]) for c in sujo.columns}
    pares, quantos_determina = {}, {c: 0 for c in sujo.columns}
    for determinante in sujo.columns:
        for determinado in sujo.columns:
            if determinante == determinado:
                continue
            p = perfilar_par(sujo, determinante, determinado, config.DOMINANCIA_MODA)
            if (
                p["det"] >= config.DET_MINIMO
                and p["cobertura"] >= config.COBERTURA_MINIMA
                and p["n_grupos"] >= config.GRUPOS_MINIMOS_PAR
            ):
                pares[(determinante, determinado)] = p
                quantos_determina[determinante] += 1

    qualificadas = [c for c in sujo.columns if quantos_determina[c] > 0]
    candidatas = sorted(
        qualificadas, key=lambda c: (-quantos_determina[c], -colunas[c]["n_distintos"])
    )[:3]
    return Entrada(
        sujo=sujo,
        guia_linhas=guia_linhas,
        guia_pares=guia_pares,
        perfil=Perfil(colunas=colunas, pares=pares, candidatas_sujeito=candidatas),
        decisoes=_ler_decisoes(caminho_guia),
    )


def _ler_decisoes(caminho_guia):
    """As decisoes do usuario no decisoes.json da pasta do guia; sem arquivo, lista vazia."""
    arquivo = Path(caminho_guia) / "decisoes.json" if caminho_guia is not None else None
    if arquivo is None or not arquivo.exists():
        return []
    return json.loads(arquivo.read_text(encoding="utf-8"))


def _ler_guia(caminho_guia, colunas):
    """Le os dois CSVs do guia; ausentes viram tabelas vazias (braco sem guia)."""
    vazio_pares = pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"])
    if caminho_guia is None:
        return pd.DataFrame(columns=list(colunas)), vazio_pares
    pasta = Path(caminho_guia)
    arquivo_linhas = pasta / "guia_linhas.csv"
    arquivo_pares = pasta / "guia_pares.csv"
    linhas = pd.DataFrame(columns=list(colunas))
    if arquivo_linhas.exists():
        linhas = pd.read_csv(arquivo_linhas, index_col="_linha", **config.LER_CSV)
        # LER_CSV faz o indice virar texto, e o indice do sujo e inteiro;
        # sem esta conversao o intersection do crivo daria vazio em silencio.
        linhas.index = linhas.index.astype(int)
    pares = vazio_pares
    if arquivo_pares.exists():
        pares = pd.read_csv(arquivo_pares, **config.LER_CSV)
        if not pares.empty:
            pares["linha"] = pares["linha"].astype(int)
    return linhas, pares

"""Etapa 3: reprova a regra candidata que nao se sustenta, sem LLM e sem gabarito."""
from math import sqrt

import pandas as pd

from limpeza2 import config
from limpeza2.motor import detectar, reparar

MOTIVOS = (
    "aprovada", "marca_celula_correta", "vacua", "marca_demais", "perde_par_do_guia",
    "ambigua", "sem_perfil", "lancou", "nao_repara", "corrompe_celula_do_guia",
)


def crivar_deteccao(candidatas, entrada):
    """Aplica os cinco testes e devolve, por (coluna, tipo), a que marca menos."""
    sobreviventes = {}
    for candidata in candidatas:
        mascara = _mascara(candidata, entrada)
        if mascara is None:
            continue
        chave = (candidata.coluna, candidata.tipo)
        anterior = sobreviventes.get(chave)
        if anterior is None or candidata.metricas["taxa"] < anterior.metricas["taxa"]:
            sobreviventes[chave] = candidata
    return [c for c in candidatas if sobreviventes.get((c.coluna, c.tipo)) is c]


def _mascara(candidata, entrada):
    """A mascara da candidata, ou None quando ela e reprovada; grava sempre as metricas."""
    sujo = entrada.sujo
    try:
        mascara = detectar(
            sujo, candidata.coluna, candidata.tipo, candidata.parametros,
            config.DOMINANCIA_MODA,
        ).fillna(False)
    except Exception as erro:
        # Degradacao nomeada: a coluna fica sem esta regra.
        candidata.metricas = {"marcadas": 0, "taxa": 0.0, "motivo": "lancou",
                              "detalhe": f"{type(erro).__name__}: {erro}"}
        return None

    marcadas = int(mascara.sum())
    candidata.metricas = {
        "marcadas": marcadas, "taxa": marcadas / len(sujo), "motivo": "aprovada",
        "teto": teto_da_coluna(entrada, candidata.coluna),
    }
    motivo = _reprovar(candidata, entrada, mascara)
    if motivo:
        candidata.metricas["motivo"] = motivo
        return None
    return mascara


def _reprovar(candidata, entrada, mascara):
    """O primeiro dos cinco testes que a candidata falha, ou None se passar em todos."""
    if candidata.tipo == "dependencia":
        determinantes = candidata.parametros["determinantes"]
        # Sem entrada no perfil nao ha como medir a ambiguidade, e deixar
        # passar seria a vacuidade da licao 6 com nome novo.
        if len(determinantes) != 1:
            return "sem_perfil"
        par = entrada.perfil.pares.get((determinantes[0], candidata.coluna))
        if par is None:
            return "sem_perfil"
        if par["frac_ambiguos"] > config.TETO_AMBIGUIDADE:
            return "ambigua"
    if _celulas_certas(entrada, candidata.coluna, mascara):
        return "marca_celula_correta"
    if candidata.metricas["marcadas"] == 0:
        return "vacua"
    if candidata.metricas["taxa"] > candidata.metricas["teto"]:
        return "marca_demais"
    pares = entrada.guia_pares
    if not pares.empty:
        da_coluna = pares[pares["coluna"] == candidata.coluna]
        alvos = entrada.sujo.index.intersection(pd.Index(da_coluna["linha"].astype(int)))
        if len(alvos) and not bool(mascara.loc[alvos].all()):
            return "perde_par_do_guia"
    return None


def teto_da_coluna(entrada, coluna):
    """O teto de marcacao da coluna: o a priori, ou a taxa suja do guia mais 2 erros padrao."""
    linhas = entrada.guia_linhas.index.intersection(entrada.sujo.index)
    if coluna not in entrada.guia_linhas.columns or len(linhas) == 0:
        return config.TETO_MARCACAO
    certo = entrada.guia_linhas.loc[linhas, coluna]
    suja = float((entrada.sujo.loc[linhas, coluna] != certo).mean())
    # Margem de 2 erros padrao de uma proporcao no pior caso (p = 0,5).
    return max(config.TETO_MARCACAO, suja + 2 * sqrt(0.25 / len(linhas)))


def _celulas_certas(entrada, coluna, mascara):
    """Linhas do guia em que a celula ja estava certa no sujo e a mascara marca."""
    if coluna not in entrada.guia_linhas.columns:
        return False
    linhas = entrada.guia_linhas.index.intersection(entrada.sujo.index)
    certas = entrada.sujo.loc[linhas, coluna] == entrada.guia_linhas.loc[linhas, coluna]
    return bool(mascara.loc[linhas][certas].any())


def crivar_reparo(propostas, entrada, funcoes=None):
    """Reprova o reparo que corrompe o guia, perde par ou nao repara nada."""
    aprovados = []
    for proposta in propostas:
        candidata = proposta.candidata
        try:
            mascara = detectar(
                entrada.sujo, candidata.coluna, candidata.tipo, candidata.parametros,
                config.DOMINANCIA_MODA,
            ).fillna(False)
            novo, reparada = reparar(
                entrada.sujo, candidata.coluna, proposta.estrategia,
                proposta.parametros, mascara, funcoes, config.DOMINANCIA_MODA,
            )
        except Exception as erro:
            candidata.metricas["motivo_reparo"] = "lancou"
            candidata.metricas["detalhe_reparo"] = f"{type(erro).__name__}: {erro}"
            continue

        motivo = _reprovar_reparo(entrada, novo, reparada, proposta, mascara)
        candidata.metricas["reparadas"] = int(reparada.sum())
        candidata.metricas["motivo_reparo"] = motivo or "aprovada"
        if motivo is None:
            aprovados.append(proposta)
    return aprovados


def _reprovar_reparo(entrada, novo, reparada, proposta, mascara):
    """O motivo da reprovacao do reparo, ou None se ele passar."""
    if _escreveu_errado_no_guia(entrada, novo):
        return "corrompe_celula_do_guia"
    if int(reparada.sum()) == 0:
        return "nao_repara"
    # Ver docs/DECISOES.md#par-exige-valor-exato: nao consulta `reparada`.
    colunas = {proposta.candidata.coluna}
    if proposta.estrategia == "moda_condicionada":
        colunas |= set(proposta.parametros["determinantes"])
    pares = entrada.guia_pares
    for _, par in pares[pares["coluna"].isin(colunas)].iterrows():
        linha = int(par["linha"])
        if linha in novo.index and bool(mascara.get(linha, False)):
            coluna = par["coluna"]
            # Determinante so responde pela celula que o reparo escreveu.
            if coluna != proposta.candidata.coluna and novo.at[linha, coluna] == entrada.sujo.at[linha, coluna]:
                continue
            if novo.at[linha, coluna] != par["limpo"]:
                return "perde_par_do_guia"
    return None


def _escreveu_errado_no_guia(entrada, novo):
    """Ha celula do guia que o reparo escreveu com valor diferente do guia."""
    linhas = entrada.guia_linhas.index.intersection(entrada.sujo.index)
    colunas = entrada.guia_linhas.columns.intersection(entrada.sujo.columns)
    antes = entrada.sujo.loc[linhas, colunas]
    guia = entrada.guia_linhas.loc[linhas, colunas]
    escreveu = novo.loc[linhas, colunas] != antes
    return bool((escreveu & (novo.loc[linhas, colunas] != guia)).any(axis=None))

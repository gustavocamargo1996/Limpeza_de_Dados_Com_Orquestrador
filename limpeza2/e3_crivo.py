"""Etapa 3: reprova a regra candidata que nao se sustenta, sem LLM e sem gabarito."""
import pandas as pd

from limpeza2 import config
from limpeza2.limites import (
    celulas_sujas_do_guia, teto_da_coluna, valores_certificados,
)
from limpeza2.motor import detectar, reparar

MOTIVOS = (
    "aprovada", "marca_celula_correta", "vacua", "marca_demais", "perde_par_do_guia",
    "ambigua", "sem_perfil", "lancou", "nao_repara", "corrompe_celula_do_guia",
    "marca_valor_certificado",
)
TIPOS_DE_VALOR = ("formato", "dominio", "faixa", "ausente_disfarcado", "conformidade")


def crivar_deteccao(candidatas, entrada):
    """Crivo da deteccao: menor taxa por (coluna, tipo); a taxa da uniao vai a metricas."""
    vencedoras = {}
    for candidata in candidatas:
        mascara = _mascara(candidata, entrada)
        if mascara is None:
            continue
        chave = (candidata.coluna, candidata.tipo)
        anterior = vencedoras.get(chave)
        if anterior is None or candidata.metricas["taxa"] < anterior[0].metricas["taxa"]:
            vencedoras[chave] = (candidata, mascara)
    for coluna in {c for c, _ in vencedoras}:
        _gravar_uniao([v for (c, _), v in vencedoras.items() if c == coluna])
    finais = {id(c) for c, _ in vencedoras.values()}
    return [c for c in candidatas if id(c) in finais]


def _gravar_uniao(vencedoras):
    """Grava em cada candidata a fracao de celulas que as regras da coluna marcam somadas."""
    uniao = float(pd.concat([m for _, m in vencedoras], axis=1).any(axis=1).mean())
    for candidata, _ in vencedoras:
        candidata.metricas["taxa_uniao"] = uniao


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
    if candidata.tipo in TIPOS_DE_VALOR and _marca_valor_certificado(
        entrada, candidata.coluna, mascara
    ):
        return "marca_valor_certificado"
    if candidata.metricas["marcadas"] == 0:
        return "vacua"
    # Conformidade vem de dado certificado: a taxa alta e a verdade da coluna, sem teto.
    if candidata.tipo != "conformidade" and candidata.metricas["taxa"] > candidata.metricas["teto"]:
        return "marca_demais"
    pares = entrada.guia_pares
    if not pares.empty:
        da_coluna = pares[pares["coluna"] == candidata.coluna]
        alvos = entrada.sujo.index.intersection(pd.Index(da_coluna["linha"].astype(int)))
        if len(alvos) and not bool(mascara.loc[alvos].all()):
            return "perde_par_do_guia"
    return None


def _marca_valor_certificado(entrada, coluna, mascara):
    """A mascara marca celula cujo valor o guia mostra como correto na coluna."""
    if coluna not in entrada.guia_linhas.columns:
        return False
    return bool(entrada.sujo[coluna][mascara].isin(valores_certificados(entrada, coluna)).any())


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
    alvo = proposta.candidata.coluna
    celulas = [(int(p.linha), p.coluna, p.limpo)
               for p in pares[pares["coluna"].isin(colunas)].itertuples()]
    for linha, coluna, limpo in celulas + celulas_sujas_do_guia(entrada, alvo):
        if linha in novo.index and bool(mascara.get(linha, False)):
            # Determinante so responde pela celula que o reparo escreveu.
            if coluna != alvo and novo.at[linha, coluna] == entrada.sujo.at[linha, coluna]:
                continue
            if novo.at[linha, coluna] != limpo:
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

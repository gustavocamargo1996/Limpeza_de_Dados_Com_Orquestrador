"""Monta o decisoes.json do guia e recusa a decisao que contradiz o guia."""
import json
from pathlib import Path

from orquestrador.relatorio_geracao import CONTRADIZ

APROVAVEIS = {"marca_demais", "superada", "ambigua"}
TENTAVEIS = {"sem_especificacao", "especificacao_invalida", "codigo_rejeitado", "lancou"}


def opcoes(candidata):
    """O que o usuario pode decidir sobre a candidata; vazio quando nada cabe."""
    motivo, reparo = candidata["motivo"], candidata["metricas"].get("motivo_reparo")
    if motivo == "rejeitada_pelo_usuario":
        return ["desfazer"]
    if motivo == "aprovada":
        return ["rejeitar", "tentar"] if reparo in TENTAVEIS else ["rejeitar"]
    return ["aprovar"] if motivo in APROVAVEIS else []


def _entrada(coluna, tipo, parametros, decisao, instrucao, versao):
    """Uma entrada do decisoes.json no formato que o gerador le."""
    return {"coluna": coluna, "tipo": tipo, "parametros": parametros, "decisao": decisao,
            "instrucao": (instrucao or "").strip() or None, "origem": "usuario", "versao": versao}


def decidir(candidata, coluna, escolha, instrucao, versao):
    """A entrada da escolha do usuario; escolha que nao cabe levanta ValueError."""
    if escolha not in opcoes(candidata):
        razao = "contradiz o guia" if candidata["motivo"] in CONTRADIZ else "nao tem efeito"
        raise ValueError(f"{coluna}/{candidata['tipo']}: {escolha} recusado, a regra {razao}")
    if escolha == "tentar" and not (instrucao or "").strip():
        raise ValueError(f"{coluna}/{candidata['tipo']}: nova tentativa exige instrucao")
    decisao = {"rejeitar": "rejeitar", "desfazer": "desfazer"}.get(escolha, "aprovar")
    return _entrada(coluna, candidata["tipo"], candidata["parametros"], decisao, instrucao, versao)


def decidir_residual(coluna, sujo, versao):
    """A entrada que tira `sujo` do dicionario residual da coluna."""
    return _entrada(coluna, "residual", {"sujo": sujo}, "rejeitar", None, versao)


def chave(decisao):
    """A chave da regra a que a decisao se refere: coluna, tipo e parametros."""
    return decisao["coluna"], decisao["tipo"], json.dumps(decisao["parametros"], sort_keys=True)


def acumular(anteriores, novas, regras=None, versao=None):
    """As anteriores, as herdadas de `regras` e as novas por cima; `desfazer` remove."""
    por_chave = {chave(d): d for d in anteriores}
    for regra in regras or []:
        herdada = {**_entrada(regra["coluna"], regra["tipo"], regra["deteccao"], "aprovar", None,
                              versao), "origem": "herdada"}
        por_chave.setdefault(chave(herdada), herdada)
    for d in novas:
        por_chave[chave(d)] = d
    return [d for d in por_chave.values() if d["decisao"] != "desfazer"]


def ler(pasta):
    """As decisoes do decisoes.json da pasta; sem arquivo, lista vazia."""
    arquivo = Path(pasta) / "decisoes.json"
    return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else []


def gravar(pasta, decisoes):
    """Grava o decisoes.json na pasta do guia."""
    Path(pasta).mkdir(parents=True, exist_ok=True)
    (Path(pasta) / "decisoes.json").write_text(
        json.dumps(decisoes, ensure_ascii=False, indent=1), encoding="utf-8")

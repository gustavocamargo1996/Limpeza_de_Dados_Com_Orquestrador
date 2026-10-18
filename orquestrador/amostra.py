"""Sorteia, valida e renumera a amostra-guia e a amostra de geracao."""
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from orquestrador import config

COLUNAS_PARES = ["linha", "coluna", "sujo", "limpo"]


def _ordem(sorteio):
    """A permutacao inteira de que o sorteio tira as linhas, refeita pela semente."""
    return np.random.default_rng(sorteio["semente"]).permutation(sorteio["n_total"]).tolist()


def sortear(n_total, n, semente):
    """As `n` primeiras linhas de uma permutacao com semente, sem trocas ainda."""
    sorteio = {"semente": semente, "n_total": n_total, "linhas": [], "trocas": []}
    return {**sorteio, "linhas": _ordem(sorteio)[:n]}


def trocar(sorteio, posicao):
    """Troca a linha da `posicao` pela proxima livre da mesma permutacao e registra a troca."""
    usadas = set(sorteio["linhas"]) | {t["saiu"] for t in sorteio["trocas"]}
    livres = [i for i in _ordem(sorteio) if i not in usadas]
    if not livres:
        raise ValueError("nao ha linha livre para sortear")
    linhas = list(sorteio["linhas"])
    troca = {"posicao": posicao, "saiu": linhas[posicao], "entrou": livres[0]}
    linhas[posicao] = livres[0]
    return {**sorteio, "linhas": linhas, "trocas": [*sorteio["trocas"], troca]}


def template(sujo, sorteio):
    """As linhas sorteadas com os valores sujos e a coluna _linha, na ordem do sorteio."""
    tabela = sujo.loc[sorteio["linhas"]].copy()
    tabela.insert(0, "_linha", sorteio["linhas"])
    return tabela.reset_index(drop=True)


def divergencias(guia, sujo, sorteio):
    """O que impede o guia devolvido de valer: colunas ou _linha diferentes do sorteio."""
    esperadas = {"_linha", *sujo.columns}
    if set(guia.columns) != esperadas:
        faltam, sobram = esperadas - set(guia.columns), set(guia.columns) - esperadas
        return [f"colunas diferentes do template: faltam {sorted(faltam)}, sobram {sorted(sobram)}"]
    linhas = pd.to_numeric(guia["_linha"], errors="coerce")
    if linhas.isna().any() or sorted(linhas.astype(int)) != sorted(sorteio["linhas"]):
        return ["a coluna _linha nao e a do sorteio: nao altere, nao apague nem acrescente linhas"]
    return []


def completar_pares(pares, sujo):
    """Os pares validos com `sujo` tirado da celula, e a lista dos problemas dos outros."""
    validos, problemas = [], []
    for par in pares.to_dict("records"):
        linha = pd.to_numeric(str(par.get("linha", "")), errors="coerce")
        if pd.isna(linha) or int(linha) not in sujo.index:
            problemas.append(f"par com linha inexistente: {par.get('linha')!r}")
        elif par.get("coluna") not in sujo.columns:
            problemas.append(f"par com coluna inexistente: {par.get('coluna')!r}")
        else:
            validos.append({"linha": int(linha), "coluna": par["coluna"],
                            "sujo": sujo.at[int(linha), par["coluna"]],
                            "limpo": "" if pd.isna(par.get("limpo")) else str(par["limpo"])})
    return pd.DataFrame(validos, columns=COLUNAS_PARES), problemas


def gravar_guia(pasta, guia, pares, sujo, sorteio):
    """Grava os quatro arquivos da Amostra_Guia, preservando a ordem das linhas."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    guia = guia[["_linha", *sujo.columns]].astype(str)
    pares = pares[COLUNAS_PARES].astype(str)
    guia.to_csv(pasta / "guia_linhas.csv", index=False)
    pares.to_csv(pasta / "guia_pares.csv", index=False)
    citadas = sorted({int(v) for v in guia["_linha"]} | {int(v) for v in pares["linha"]})
    sujas = sujo.loc[citadas].copy()
    sujas.insert(0, "_linha", citadas)
    sujas.to_csv(pasta / "linhas_sujas.csv", index=False)
    (pasta / "sorteio.json").write_text(json.dumps(sorteio, indent=1), encoding="utf-8")


def linhas_sujas(pasta_guia):
    """As linhas sujas que o guia cita, indexadas pela linha da extracao de origem."""
    sujas = pd.read_csv(Path(pasta_guia) / "linhas_sujas.csv", **config.LER_CSV)
    return sujas.set_index(sujas["_linha"].astype(int)).drop(columns="_linha").rename_axis(None)


def _amostrar(indices, obrigatorias, base, tamanho, semente):
    """Os indices da amostra em ordem crescente: as obrigatorias e um sorteio com semente."""
    if base == "inteira" or tamanho >= len(indices):
        return list(indices)
    resto = [i for i in indices if i not in obrigatorias]
    vagas = min(max(tamanho - len(obrigatorias), 0), len(resto))
    sorteadas = np.random.default_rng(semente).choice(resto, size=vagas, replace=False)
    return sorted(set(obrigatorias) | {int(i) for i in sorteadas})


def montar_entrada(sujo, pasta_guia, destino, base, tamanho, semente, antigas=None):
    """Grava o sujo da geracao e o guia renumerado em `destino`; devolve os parametros."""
    pasta_guia, destino = Path(pasta_guia), Path(destino)
    guia = pd.read_csv(pasta_guia / "guia_linhas.csv", **config.LER_CSV)
    pares = pd.read_csv(pasta_guia / "guia_pares.csv", **config.LER_CSV)
    citadas = {int(v) for v in guia["_linha"]} | {int(v) for v in pares["linha"]}
    # Guia feito noutra extracao: as linhas dele vem de `antigas` e entram na frente.
    frente = [] if antigas is None else list(antigas.index)
    escolhidas = _amostrar(sujo.index, set() if frente else citadas, base, tamanho, semente)
    partes = ([antigas.loc[frente]] if frente else []) + [sujo.loc[escolhidas]]
    origem = ([{"fonte": "guia", "linha": int(i)} for i in frente]
              + [{"fonte": "dados", "linha": int(i)} for i in escolhidas])
    posicao = {i: k for k, i in enumerate(frente or escolhidas)}
    guia["_linha"] = [posicao[int(v)] for v in guia["_linha"]]
    pares["linha"] = [posicao[int(v)] for v in pares["linha"]]
    (destino / "guia").mkdir(parents=True, exist_ok=True)
    pd.concat(partes)[list(sujo.columns)].to_csv(destino / "sujo.csv", index=False)
    guia.to_csv(destino / "guia" / "guia_linhas.csv", index=False)
    pares.to_csv(destino / "guia" / "guia_pares.csv", index=False)
    if (pasta_guia / "decisoes.json").exists():
        shutil.copy(pasta_guia / "decisoes.json", destino / "guia" / "decisoes.json")
    return {"base": base, "tamanho": len(origem), "semente": semente, "origem": origem}

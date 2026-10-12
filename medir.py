"""Executa o limpador gerado e mede precisao, recall e F1 de reparo."""
import argparse
import importlib.util
import warnings
from pathlib import Path

import pandas as pd

from limpeza2 import config


def carregar(caminho):
    """Importa o limpador gerado como modulo solto, sem instalar nada."""
    spec = importlib.util.spec_from_file_location("limpador_gerado", str(caminho))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def f1_reparo(sujo, corrigido, limpo):
    """Precisao, recall e F1 de reparo de uma coluna; formula identica a da POC 1."""
    n_erro = int((sujo != limpo).sum())
    mudanca = corrigido != sujo
    n_mud = int(mudanca.sum())
    tp = int((mudanca & (corrigido == limpo)).sum())
    if n_erro == 0:
        return {"mensuravel": False, "erros": 0, "mudancas": n_mud, "tp": tp,
                "precisao": None, "recall": None, "f1": None}
    p = tp / n_mud if n_mud else None
    r = tp / n_erro
    f1 = 2 * p * r / (p + r) if (p and (p + r)) else 0.0
    return {"mensuravel": True, "erros": n_erro, "mudancas": n_mud, "tp": tp,
            "precisao": p, "recall": r, "f1": f1}


def linhas_do_guia(caminho_linhas, caminho_pares):
    """Os indices de linha que apareceram no guia e saem da metrica."""
    fora = set()
    if Path(caminho_linhas).exists():
        fora |= set(pd.read_csv(caminho_linhas, index_col="_linha").index)
    if Path(caminho_pares).exists():
        fora |= set(pd.read_csv(caminho_pares)["linha"])
    return fora


def avaliar(caminho_limpador, caminho_sujo, caminho_limpo, holdout=None):
    """Aplica o limpador e mede por coluna e no total, descontando o holdout."""
    sujo = pd.read_csv(caminho_sujo, **config.LER_CSV)
    limpo = pd.read_csv(caminho_limpo, **config.LER_CSV)
    with warnings.catch_warnings():
        # O LLM escreve regex nao-raw e com grupos: SyntaxWarning ao importar, UserWarning ao aplicar.
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        modulo = carregar(caminho_limpador)
        if hasattr(modulo, "aplicar_detalhado"):
            corrigido, flags, fontes = modulo.aplicar_detalhado(sujo)
        else:
            corrigido, flags = modulo.aplicar(sujo)
            fontes = None
        truncada = bool(getattr(modulo, "GERACAO_TRUNCADA", False))
        degradadas = int(getattr(modulo, "UNIDADES_DEGRADADAS_POR_TETO", 0))

    manter_fora = sujo.index.intersection(pd.Index(sorted(holdout or [])))
    manter = sujo.index.difference(manter_fora)
    colunas, por_fonte = {}, {}
    tp = n_erro = n_mud = n_flag = 0
    for coluna in sujo.columns:
        if coluna not in corrigido.columns:
            continue
        m = f1_reparo(
            sujo.loc[manter, coluna],
            corrigido.loc[manter, coluna],
            limpo.loc[manter, coluna],
        )
        m["flags"] = int(flags.loc[manter, coluna].sum()) if coluna in flags.columns else 0
        n_flag += m["flags"]
        colunas[coluna] = m
        if m["mensuravel"]:
            tp += m["tp"]
            n_erro += m["erros"]
            n_mud += m["mudancas"]
        if fontes is not None and coluna in fontes.columns:
            acertou = (corrigido.loc[manter, coluna] == limpo.loc[manter, coluna]) & (
                corrigido.loc[manter, coluna] != sujo.loc[manter, coluna]
            )
            for fonte, n in fontes.loc[manter, coluna][acertou].value_counts().items():
                por_fonte[fonte] = por_fonte.get(fonte, 0) + int(n)

    p = tp / n_mud if n_mud else None
    r = tp / n_erro if n_erro else 0.0
    f1 = 2 * p * r / (p + r) if (p and (p + r)) else 0.0
    return {
        "colunas": colunas,
        "holdout": len(manter_fora),
        "fontes": por_fonte,
        "truncada": truncada,
        "degradadas": degradadas,
        "total": {"erros": n_erro, "mudancas": n_mud, "tp": tp, "flags": n_flag,
                  "precisao": p, "recall": r, "f1": f1},
    }


def _pct(v):
    return "n/d" if v is None else f"{v:.1%}"


def main():
    ap = argparse.ArgumentParser(description="F1 de reparo de um limpador gerado")
    ap.add_argument("--limpador", required=True)
    ap.add_argument("--sujo", required=True)
    ap.add_argument("--limpo", required=True)
    ap.add_argument("--guia", help="pasta com guia_linhas.csv e guia_pares.csv")
    args = ap.parse_args()

    fora = set()
    if args.guia:
        fora = linhas_do_guia(
            Path(args.guia) / "guia_linhas.csv", Path(args.guia) / "guia_pares.csv"
        )
    r = avaliar(args.limpador, args.sujo, args.limpo, holdout=fora)

    print(f"limpador: {Path(args.limpador).name}")
    print(f"holdout:  {r['holdout']} linhas fora da metrica\n")
    if r["truncada"]:
        print(f"AVISO: geracao TRUNCADA pelo teto de chamadas ({r['degradadas']} unidade(s) sem regra); "
              "estes numeros nao sao de uma geracao completa\n")
    print(f"{'coluna':22s}| {'erros':>6s} | {'mudou':>6s} | {'TP':>5s} | "
          f"{'precisao':>8s} | {'recall':>6s} | {'F1':>6s} | flags")
    print("-" * 88)
    for coluna, m in r["colunas"].items():
        print(f"{coluna:22s}| {m['erros']:6d} | {m['mudancas']:6d} | {m['tp']:5d} | "
              f"{_pct(m['precisao']):>8s} | {_pct(m['recall']):>6s} | "
              f"{_pct(m['f1']):>6s} | {m['flags']}")
    t = r["total"]
    print("-" * 88)
    print(f"{'TOTAL':22s}| {t['erros']:6d} | {t['mudancas']:6d} | {t['tp']:5d} | "
          f"{_pct(t['precisao']):>8s} | {_pct(t['recall']):>6s} | "
          f"{_pct(t['f1']):>6s} | {t['flags']}")
    if r["fontes"]:
        print("\nacertos por fonte:")
        for fonte, n in sorted(r["fontes"].items(), key=lambda kv: -kv[1]):
            print(f"  {fonte:24s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

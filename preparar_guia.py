"""Sorteia o guia com semente fixa: linhas certas e pares sujo->limpo."""
import argparse

import pandas as pd

from limpeza2 import config


def sortear(sujo, limpo, semente, n_linhas, pares_por_coluna):
    """Devolve (guia_linhas, guia_pares) sorteados com semente fixa."""
    diferentes = sujo != limpo
    corretas = pd.Series(list(sujo.index[~diferentes.any(axis=1)]))
    escolhidas = corretas.sample(
        n=min(n_linhas, len(corretas)), random_state=semente
    ).tolist()
    # As linhas escolhidas sao identicas nos dois arquivos por construcao,
    # entao tomar do sujo torna o guia derivavel do sujo mais os indices.
    guia_linhas = sujo.loc[sorted(escolhidas)].copy()

    registros = []
    for coluna in sujo.columns:
        erradas = pd.Series(list(sujo.index[diferentes[coluna]]))
        if erradas.empty:
            continue
        for linha in sorted(
            erradas.sample(
                n=min(pares_por_coluna, len(erradas)), random_state=semente
            ).tolist()
        ):
            registros.append(
                {
                    "linha": linha,
                    "coluna": coluna,
                    "sujo": sujo.at[linha, coluna],
                    "limpo": limpo.at[linha, coluna],
                }
            )
    guia_pares = pd.DataFrame(registros, columns=["linha", "coluna", "sujo", "limpo"])
    return guia_linhas, guia_pares


def gravar(dataset, sujo, limpo):
    """Grava os CSVs do guia em dados/guia/<dataset>/ e devolve caminhos e contagens."""
    linhas, pares = sortear(
        sujo, limpo, config.SEMENTE, config.LINHAS_GUIA, config.PARES_POR_COLUNA
    )
    destino = config.GUIA / dataset
    destino.mkdir(parents=True, exist_ok=True)
    caminho_linhas = destino / "guia_linhas.csv"
    caminho_pares = destino / "guia_pares.csv"
    linhas.to_csv(caminho_linhas, index=True, index_label="_linha", encoding="utf-8")
    pares.to_csv(caminho_pares, index=False, encoding="utf-8")
    return caminho_linhas, caminho_pares, len(linhas), len(pares)


def main():
    ap = argparse.ArgumentParser(description="Sorteia o guia de um dataset")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--sujo", required=True)
    ap.add_argument("--limpo", required=True)
    args = ap.parse_args()

    sujo = pd.read_csv(args.sujo, **config.LER_CSV)
    limpo = pd.read_csv(args.limpo, **config.LER_CSV)
    caminho_linhas, caminho_pares, n_linhas, n_pares = gravar(args.dataset, sujo, limpo)
    print(f"guia de {args.dataset}: {n_linhas} linhas, {n_pares} pares")
    print(f"  {caminho_linhas}")
    print(f"  {caminho_pares}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Sorteia o guia com semente fixa: linhas corrigidas e pares sujo->limpo."""
import argparse

import pandas as pd

from limpeza2 import config


def sortear(sujo, limpo, semente, n_linhas, pares_por_coluna):
    """Devolve (guia_linhas, guia_pares) sorteados com semente fixa."""
    diferentes = sujo != limpo
    todas = pd.Series(list(sujo.index))
    escolhidas = todas.sample(n=min(n_linhas, len(todas)), random_state=semente).tolist()
    # Os valores vem do limpo: o guia e referencia corrigida, nao copia do sujo.
    guia_linhas = limpo.loc[sorted(escolhidas)].copy()

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


def gravar(dataset, sujo, limpo, semente, n_linhas, pares_por_coluna, destino=None):
    """Grava os CSVs e a receita do guia em dados/guia/<destino ou dataset>/."""
    linhas, pares = sortear(sujo, limpo, semente, n_linhas, pares_por_coluna)
    pasta = config.GUIA / (destino or dataset)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho_linhas = pasta / "guia_linhas.csv"
    caminho_pares = pasta / "guia_pares.csv"
    linhas.to_csv(caminho_linhas, index=True, index_label="_linha", encoding="utf-8")
    pares.to_csv(caminho_pares, index=False, encoding="utf-8")
    receita = {"dataset": dataset, "semente": semente, "linhas": n_linhas,
               "pares_por_coluna": pares_por_coluna}
    texto = "".join(f"{chave}={valor}\n" for chave, valor in receita.items())
    (pasta / "guia_receita.txt").write_text(texto, encoding="utf-8", newline="\n")
    return caminho_linhas, caminho_pares, len(linhas), len(pares)


def main():
    ap = argparse.ArgumentParser(description="Sorteia o guia de um dataset")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--sujo", required=True)
    ap.add_argument("--limpo", required=True)
    ap.add_argument("--linhas", type=int, default=config.LINHAS_GUIA)
    ap.add_argument("--pares", type=int, default=config.PARES_POR_COLUNA)
    ap.add_argument("--destino", help="pasta sob dados/guia/; padrao: o dataset")
    args = ap.parse_args()

    sujo = pd.read_csv(args.sujo, **config.LER_CSV)
    limpo = pd.read_csv(args.limpo, **config.LER_CSV)
    caminho_linhas, caminho_pares, n_linhas, n_pares = gravar(
        args.dataset, sujo, limpo, config.SEMENTE, args.linhas, args.pares, args.destino
    )
    print(f"guia de {args.dataset}: {n_linhas} linhas, {n_pares} pares")
    print(f"  {caminho_linhas}")
    print(f"  {caminho_pares}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Executa o limpador gerado em subprocesso e resume no relatorio de limpeza o que ele mudou."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from orquestrador import config


def aplicar(limpador, entrada, pasta):
    """Roda o limpador sobre `entrada` num filho e devolve o que ele gravou em `pasta`."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    feito = subprocess.run(
        [config.PYTHON, "-m", "orquestrador.relatorio_limpeza", str(limpador), str(entrada),
         str(pasta)], cwd=config.RAIZ, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=config.TIMEOUT_APLICACAO)
    if feito.returncode != 0:
        raise RuntimeError(f"o limpador falhou: {feito.stderr.strip()[-2000:]}")
    literais = json.loads((pasta / "regras.json").read_text(encoding="utf-8"))
    tabelas = {nome: pd.read_csv(pasta / f"{nome}.csv", **config.LER_CSV)
               for nome in ("dados", "flags", "fontes")}
    return {"original": pd.read_csv(entrada, **config.LER_CSV), "corrigido": tabelas["dados"],
            "flags": tabelas["flags"] == "True", "fontes": tabelas["fontes"], **literais}


def resumir(aplicacao):
    """Por regra, as celulas alteradas e uma amostra antes e depois; e residual, flags e totais."""
    original, corrigido, fontes = aplicacao["original"], aplicacao["corrigido"], aplicacao["fontes"]
    regras = []
    for numero, regra in enumerate(aplicacao["regras"], 1):
        fonte = f"{regra['tipo']}/{regra['estrategia']}" if regra["estrategia"] else None
        linhas = list(fontes.index[fontes[regra["coluna"]] == fonte]) if fonte else []
        amostra = [(int(i), original.at[i, regra["coluna"]], corrigido.at[i, regra["coluna"]])
                   for i in linhas[:config.CELULAS_POR_REGRA]]
        regras.append({"id": f"R{numero}", **regra, "alteradas": len(linhas), "amostra": amostra})
    residual = {c: int(n) for c, n in (fontes == "residual").sum().items() if n}
    flags = {c: int(n) for c, n in aplicacao["flags"].sum().items() if n}
    escritas = fontes != ""
    return {"regras": regras, "residual": residual, "flags": flags,
            "celulas": int(escritas.sum().sum()), "linhas": int(escritas.any(axis=1).sum()),
            "truncada": aplicacao["truncada"]}


def montar(resumo, versao):
    """O relatorio de limpeza em Markdown."""
    linhas = [f"# Relatório de limpeza: {versao}", "",
              f"- células alteradas: {resumo['celulas']}, em {resumo['linhas']} linhas",
              "", "## Regras validadas", ""]
    for r in resumo["regras"]:
        acao = f"reparo `{r['estrategia']}`" if r["estrategia"] else "só marca, não corrige"
        linhas += [f"### {r['id']}: `{r['coluna']}`, {r['tipo']}, {acao}", "",
                   f"- células alteradas: {r['alteradas']}"]
        if r["amostra"]:
            linhas += ["", "| linha | antes | depois |", "|---|---|---|"]
            linhas += [f"| {i} | `{a}` | `{d}` |" for i, a, d in r["amostra"]]
        linhas.append("")
    linhas += ["## Dicionário residual", ""]
    linhas += [f"- `{c}`: {n} células" for c, n in resumo["residual"].items()] or ["- nenhuma célula"]
    linhas += ["", "## Marcadas e não corrigidas", ""]
    linhas += [f"- `{c}`: {n} células" for c, n in resumo["flags"].items()] or ["- nenhuma célula"]
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    # O filho: importa o limpador gerado, que roda sem o portao, fora do processo da interface.
    limpador, entrada, pasta = sys.argv[1:4]
    spec = importlib.util.spec_from_file_location("limpador", limpador)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    corrigido, flags, fontes = modulo.aplicar_detalhado(pd.read_csv(entrada, **config.LER_CSV))
    destino = Path(pasta)
    corrigido.to_csv(destino / "dados.csv", index=False)
    flags.to_csv(destino / "flags.csv", index=False)
    fontes.to_csv(destino / "fontes.csv", index=False)
    literais = {"regras": modulo.REGRAS, "residual": modulo.RESIDUAL,
                "truncada": modulo.GERACAO_TRUNCADA}
    (destino / "regras.json").write_text(json.dumps(literais, ensure_ascii=False), encoding="utf-8")

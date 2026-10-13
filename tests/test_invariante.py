"""Invariante: os numeros do limpador congelado e a geracao a partir das respostas congeladas."""
from pathlib import Path

from limpeza2 import config
from limpeza2.espinha import gerar_limpador
from medir import avaliar, linhas_do_guia

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
GUIA = RAIZ / "dados" / "guia" / "beers"
SUJO = FIXTURES / "beers_dirty_300.csv"
# Nome da pasta do run pago de 12/10/2026: entra no cabecalho do limpador.
PASTA_DO_RUN = "beers_2026-10-12_2152"


def sem_cr(caminho):
    """Os bytes do arquivo com fim de linha normalizado: o git pode converter LF em CRLF no checkout."""
    return caminho.read_bytes().replace(b"\r\n", b"\n")


def test_numeros_do_limpador_congelado():
    fora = linhas_do_guia(GUIA / "guia_linhas.csv", GUIA / "guia_pares.csv")
    r = avaliar(FIXTURES / "limpador_beers_poc2.py", SUJO, FIXTURES / "beers_clean_300.csv", holdout=fora)
    t = r["total"]
    # Copiados do medir.py no run de 12/10/2026; mudar e bug, ver CLAUDE.md secao 8.
    assert (r["holdout"], t["erros"], t["mudancas"], t["tp"], t["flags"]) == (26, 445, 438, 438, 62)
    assert r["fontes"] == {"conformidade/normalizar": 336, "conformidade/esvaziar": 101, "residual": 1}
    # Alteracoes em coluna sem erro, que a formula da POC 1 nao conta na precisao.
    assert (r["colunas"]["brewery-name"]["mudancas"], r["colunas"]["brewery_id"]["mudancas"]) == (5, 1)


def test_geracao_a_partir_das_respostas_reproduz_o_limpador(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(FIXTURES / "respostas_beers_poc2.jsonl"))
    caminho = gerar_limpador(SUJO, GUIA, tmp_path / PASTA_DO_RUN)
    assert sem_cr(caminho) == sem_cr(FIXTURES / "limpador_beers_poc2.py")

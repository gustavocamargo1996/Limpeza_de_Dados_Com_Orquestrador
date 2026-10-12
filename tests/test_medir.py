"""A metrica, ancorada no placar da POC 1 que o HANDOFF registra."""
import numbers
from pathlib import Path

import pandas as pd
import pytest

from medir import avaliar, f1_reparo, linhas_do_guia

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Numeros reproduzidos com avaliar_limpador.py da POC 1 em 12/10/2026.
# Ver HANDOFF.md secao 3.
PLACAR = {
    "beers": {"erros": 495, "mudancas": 121, "tp": 121, "recall": 0.244, "flags": 71},
    "environment": {"erros": 334, "mudancas": 44, "tp": 44, "recall": 0.132, "flags": 663},
}


def test_f1_reparo_conta_so_a_mudanca_que_acertou():
    sujo = pd.Series(["a", "b", "c", "d"])
    limpo = pd.Series(["A", "B", "c", "d"])
    corrigido = pd.Series(["A", "Z", "c", "D"])
    m = f1_reparo(sujo, corrigido, limpo)
    assert m["erros"] == 2
    assert m["mudancas"] == 3
    assert m["tp"] == 1
    assert m["precisao"] == pytest.approx(1 / 3, abs=1e-4)
    assert m["recall"] == pytest.approx(0.5, abs=1e-4)


def test_coluna_sem_erro_e_marcada_como_nao_mensuravel():
    serie = pd.Series(["a", "b"])
    m = f1_reparo(serie, serie, serie)
    assert m["mensuravel"] is False
    assert m["erros"] == 0


@pytest.mark.parametrize("dataset", ["beers", "environment"])
def test_reproduz_o_placar_da_poc_1(dataset):
    esperado = PLACAR[dataset]
    r = avaliar(
        FIXTURES / f"limpador_{dataset}_congelado.py",
        FIXTURES / f"{dataset}_dirty_300.csv",
        FIXTURES / f"{dataset}_clean_300.csv",
    )
    total = r["total"]
    assert total["erros"] == esperado["erros"]
    assert total["mudancas"] == esperado["mudancas"]
    assert total["tp"] == esperado["tp"]
    assert total["flags"] == esperado["flags"]
    assert total["precisao"] == pytest.approx(1.0, abs=1e-4)
    assert total["recall"] == pytest.approx(esperado["recall"], abs=5e-4)


def test_holdout_reduz_os_erros_contados():
    sem = avaliar(
        FIXTURES / "limpador_beers_congelado.py",
        FIXTURES / "beers_dirty_300.csv",
        FIXTURES / "beers_clean_300.csv",
    )
    com = avaliar(
        FIXTURES / "limpador_beers_congelado.py",
        FIXTURES / "beers_dirty_300.csv",
        FIXTURES / "beers_clean_300.csv",
        holdout={0, 1, 2, 3, 4},
    )
    assert com["holdout"] == 5
    assert sem["total"]["erros"] == 495
    assert com["total"]["erros"] == 491
    assert com["total"]["mudancas"] == 119


LIMPADOR_MINIMO = """
import pandas as pd

def aplicar_detalhado(df):
    out = df.copy()
    flags = pd.DataFrame(False, index=df.index, columns=df.columns)
    fontes = pd.DataFrame("", index=df.index, columns=df.columns)
    out.loc[0, "a"], fontes.loc[0, "a"] = "c0", "regra1"
    out.loc[1, "a"], fontes.loc[1, "a"] = "zz", "regra2"
    out.loc[4, "b"], fontes.loc[4, "b"] = "q4", "regra1"
    flags.loc[2, "a"] = True
    return out, flags, fontes

def aplicar(df):
    out, flags, _ = aplicar_detalhado(df)
    return out, flags
"""


@pytest.fixture
def minimo(tmp_path):
    """Limpador de 3 alteracoes (2 certas, 1 errada) e 1 flag, com sujo e limpo."""
    (tmp_path / "limpador.py").write_text(LIMPADOR_MINIMO, encoding="utf-8")
    sujo = pd.DataFrame({"a": ["s0", "s1", "s2", "s3", "s4", "s5"],
                         "b": ["p0", "p1", "p2", "p3", "p4", "p5"]})
    limpo = sujo.copy()
    limpo.loc[[0, 1, 2], "a"] = ["c0", "c1", "c2"]
    limpo.loc[[0, 4], "b"] = ["q0", "q4"]
    sujo.to_csv(tmp_path / "sujo.csv", index=False)
    limpo.to_csv(tmp_path / "limpo.csv", index=False)
    return tmp_path / "limpador.py", tmp_path / "sujo.csv", tmp_path / "limpo.csv"


def test_total_soma_acertos_e_erros_com_limpador_que_erra(minimo):
    t = avaliar(*minimo)["total"]
    assert (t["erros"], t["mudancas"], t["tp"], t["flags"]) == (5, 3, 2, 1)
    assert t["precisao"] == pytest.approx(2 / 3)
    assert t["recall"] == pytest.approx(2 / 5)


def test_fonte_so_conta_quando_a_alteracao_acertou(minimo):
    assert avaliar(*minimo)["fontes"] == {"regra1": 2}


def test_holdout_respeitado_em_totais_e_fontes(minimo):
    r = avaliar(*minimo, holdout={0})
    t = r["total"]
    assert (t["erros"], t["mudancas"], t["tp"], t["flags"]) == (3, 2, 1, 1)
    assert t["precisao"] == pytest.approx(0.5)
    assert r["fontes"] == {"regra1": 1}


def _ints(conjunto):
    return all(isinstance(x, numbers.Integral) for x in conjunto)


def test_linhas_do_guia_devolve_inteiros(tmp_path):
    (tmp_path / "l.csv").write_text("_linha,x\n3,a\n7,b\n", encoding="utf-8")
    (tmp_path / "p.csv").write_text("linha,coluna,sujo,limpo\n9,x,a,b\n3,x,c,d\n", encoding="utf-8")
    fora = linhas_do_guia(tmp_path / "l.csv", tmp_path / "p.csv")
    assert fora == {3, 7, 9}
    assert _ints(fora)


def test_linhas_do_guia_pares_so_com_cabecalho(tmp_path):
    (tmp_path / "l.csv").write_text("_linha,x\n3,a\n", encoding="utf-8")
    (tmp_path / "p.csv").write_text("linha,coluna,sujo,limpo\n", encoding="utf-8")
    assert linhas_do_guia(tmp_path / "l.csv", tmp_path / "p.csv") == {3}


def test_linhas_do_guia_arquivos_ausentes(tmp_path):
    assert linhas_do_guia(tmp_path / "l.csv", tmp_path / "p.csv") == set()

"""O guia sorteado: 20 linhas certas, poucos pares, e reprodutivel."""
import pandas as pd
import pytest

from preparar_guia import sortear


@pytest.fixture
def tabelas():
    limpo = pd.DataFrame(
        {
            "cidade": ["Boston", "Austin", "Boston", "Denver", "Austin", "Denver"],
            "estado": ["MA", "TX", "MA", "CO", "TX", "CO"],
            "pais": ["US"] * 6,
        }
    )
    sujo = limpo.copy()
    sujo.loc[1, "estado"] = "TXX"
    sujo.loc[3, "cidade"] = "Denvr"
    sujo.loc[5, "estado"] = "C0"
    return sujo, limpo


def test_so_entram_linhas_sem_erro_nenhum(tabelas):
    sujo, limpo = tabelas
    linhas, _ = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    assert set(linhas.index) <= {0, 2, 4}


def test_todo_par_tem_sujo_diferente_do_limpo(tabelas):
    sujo, limpo = tabelas
    _, pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    assert len(pares) > 0
    assert (pares["sujo"] != pares["limpo"]).all()


def test_respeita_a_cota_por_coluna(tabelas):
    sujo, limpo = tabelas
    _, pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=1)
    assert pares.groupby("coluna").size().max() == 1


def test_coluna_sem_erro_nao_rende_par(tabelas):
    sujo, limpo = tabelas
    _, pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    assert "pais" not in set(pares["coluna"])


def test_a_mesma_semente_da_o_mesmo_guia(tabelas):
    sujo, limpo = tabelas
    a_linhas, a_pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    b_linhas, b_pares = sortear(sujo, limpo, semente=7, n_linhas=3, pares_por_coluna=2)
    pd.testing.assert_frame_equal(a_linhas, b_linhas)
    pd.testing.assert_frame_equal(a_pares, b_pares)


def test_pede_mais_linhas_do_que_existe_sem_estourar(tabelas):
    sujo, limpo = tabelas
    linhas, _ = sortear(sujo, limpo, semente=7, n_linhas=99, pares_por_coluna=2)
    assert len(linhas) == 3


def test_a_semente_decide_quais_linhas_entram():
    limpo = pd.DataFrame({"v": [str(i) for i in range(60)]})
    sujo = limpo.copy()
    sujo.loc[0, "v"] = "x"
    a, _ = sortear(sujo, limpo, semente=7, n_linhas=5, pares_por_coluna=2)
    b, _ = sortear(sujo, limpo, semente=7, n_linhas=5, pares_por_coluna=2)
    assert list(a.index) == list(b.index)

"""O guia sorteado: linhas corrigidas, poucos pares, receita e reprodutivel."""
import pandas as pd
import pytest

from limpeza2 import config
from preparar_guia import gravar, sortear


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


def test_linhas_do_guia_tem_os_valores_do_limpo(tabelas):
    sujo, limpo = tabelas
    # Pede todas as linhas: as de erro (1, 3, 5) entram, e entram corrigidas.
    linhas, _ = sortear(sujo, limpo, semente=7, n_linhas=6, pares_por_coluna=2)
    assert {1, 3, 5} <= set(linhas.index)
    pd.testing.assert_frame_equal(linhas, limpo.loc[linhas.index])
    assert (linhas != sujo.loc[linhas.index]).any(axis=None)


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


def test_a_mesma_semente_da_o_mesmo_guia():
    limpo = pd.DataFrame({"v": [str(i) for i in range(60)], "w": ["a"] * 60})
    sujo = limpo.copy()
    sujo.loc[:39, "w"] = "b"
    a_linhas, a_pares = sortear(sujo, limpo, semente=7, n_linhas=5, pares_por_coluna=2)
    b_linhas, b_pares = sortear(sujo, limpo, semente=7, n_linhas=5, pares_por_coluna=2)
    pd.testing.assert_frame_equal(a_linhas, b_linhas)
    pd.testing.assert_frame_equal(a_pares, b_pares)


def test_pede_mais_linhas_do_que_existe_sem_estourar(tabelas):
    sujo, limpo = tabelas
    linhas, _ = sortear(sujo, limpo, semente=7, n_linhas=99, pares_por_coluna=2)
    assert len(linhas) == 6


def test_sempre_ha_o_numero_pedido_de_linhas_mesmo_com_tudo_errado():
    limpo = pd.DataFrame({"v": ["1"] * 30})
    sujo = pd.DataFrame({"v": ["x"] * 30})
    linhas, _ = sortear(sujo, limpo, semente=7, n_linhas=20, pares_por_coluna=2)
    assert len(linhas) == 20


def test_gravar_escreve_a_receita_e_respeita_o_destino(tabelas, tmp_path, monkeypatch):
    sujo, limpo = tabelas
    monkeypatch.setattr(config, "GUIA", tmp_path)
    gravar("cidades", sujo, limpo, 7, 4, 1, destino="cidades_l4")
    pasta = tmp_path / "cidades_l4"
    receita = (pasta / "guia_receita.txt").read_text(encoding="utf-8").splitlines()
    assert receita == ["dataset=cidades", "semente=7", "linhas=4", "pares_por_coluna=1"]
    assert len(pd.read_csv(pasta / "guia_linhas.csv")) == 4
    assert not (tmp_path / "cidades").exists()

"""A metrica, ancorada no placar da POC 1 que o HANDOFF registra."""
from pathlib import Path

import pandas as pd
import pytest

from medir import avaliar, f1_reparo

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
    assert com["total"]["erros"] < sem["total"]["erros"]

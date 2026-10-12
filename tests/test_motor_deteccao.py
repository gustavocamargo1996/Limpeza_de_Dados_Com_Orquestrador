"""Os cinco tipos de deteccao, cada um numa tabela feita a mao."""
import pandas as pd
import pytest

from limpeza2.motor import detectar


@pytest.fixture
def tabela():
    # O grupo Boston tem 4 linhas com moda MA em 3 delas, isto e 0,75: acima da
    # dominancia de 0,70, senao o grupo seria pulado e nada seria marcado.
    return pd.DataFrame(
        {
            "cidade": ["Boston", "Boston", "Boston", "Boston", "Austin", "Austin", "Bosotn"],
            "estado": ["MA", "MA", "MA", "TX", "TX", "TX", "MA"],
            "zona": ["Temperate", "Temperate", "Temperate", "Tropcial", "Tropical", "N/A", ""],
            "onca": ["12", "12.0", "16", "16", "99999", "16", "-3"],
        }
    )


def test_formato_marca_quem_nao_casa(tabela):
    m = detectar(tabela, "onca", "formato", {"regex": r"\d+"})
    assert list(m) == [False, True, False, False, False, False, True]


def test_dominio_marca_quem_esta_fora(tabela):
    m = detectar(tabela, "zona", "dominio", {"valores": ["Temperate", "Tropical"]})
    assert list(m) == [False, False, False, True, False, True, True]


def test_faixa_marca_fora_dos_limites(tabela):
    m = detectar(tabela, "onca", "faixa", {"minimo": 8, "maximo": 64})
    assert list(m) == [False, False, False, False, True, False, True]


def test_faixa_nao_marca_o_que_nao_e_numero(tabela):
    m = detectar(tabela, "zona", "faixa", {"minimo": 0, "maximo": 1})
    assert not m.any()


def test_ausente_disfarcado_marca_as_sentinelas(tabela):
    m = detectar(tabela, "zona", "ausente_disfarcado", {"sentinelas": ["N/A", ""]})
    assert list(m) == [False, False, False, False, False, True, True]


def test_dependencia_marca_quem_diverge_da_moda_do_grupo(tabela):
    m = detectar(tabela, "estado", "dependencia", {"determinantes": ["cidade"]})
    assert list(m) == [False, False, False, True, False, False, False]


def test_dependencia_pula_grupo_sem_maioria_clara():
    df = pd.DataFrame({"voo": ["AA1"] * 4, "hora": ["10:30", "10:31", "10:28", "10:39"]})
    m = detectar(df, "hora", "dependencia", {"determinantes": ["voo"]}, dominancia=0.70)
    assert not m.any()


def test_dependencia_pula_grupo_de_uma_linha():
    df = pd.DataFrame({"voo": ["AA1", "AA2"], "hora": ["10:30", "11:00"]})
    m = detectar(df, "hora", "dependencia", {"determinantes": ["voo"]})
    assert not m.any()


def test_tipo_desconhecido_falha_alto(tabela):
    with pytest.raises(ValueError, match="desconhecido"):
        detectar(tabela, "onca", "telepatia", {})

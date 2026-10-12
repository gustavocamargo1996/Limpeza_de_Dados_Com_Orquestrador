"""O perfil deterministico: padroes, estatisticas por coluna e os quatro numeros do par."""
import pandas as pd
import pytest

from limpeza2.e1_perfil import padrao, perfilar, perfilar_coluna, perfilar_par


@pytest.mark.parametrize(
    "valor,nivel,esperado",
    [
        ("AB12cd", 1, "AA99aa"),
        ("AB12cd", 2, "A292a2"),
        ("AB12cd", 3, "A9a"),
        ("12.0", 1, "99.9"),
        ("12.0", 2, "92.9"),
        ("", 1, ""),
    ],
)
def test_padrao(valor, nivel, esperado):
    assert padrao(valor, nivel) == esperado


def test_perfilar_coluna_conta_distintos_e_vazios():
    serie = pd.Series(["a", "a", "b", "", ""])
    p = perfilar_coluna(serie)
    assert p["n_distintos"] == 3
    assert p["n_vazios"] == 2
    assert p["frequentes"][0] == ("a", 2)


def test_perfilar_par_mede_determinacao_perfeita():
    df = pd.DataFrame(
        {"cidade": ["Boston"] * 3 + ["Austin"] * 3, "estado": ["MA"] * 3 + ["TX"] * 3}
    )
    p = perfilar_par(df, "cidade", "estado", dominancia=0.70)
    assert p["det"] == pytest.approx(1.0)
    assert p["n_grupos"] == 2
    assert p["n_divergentes"] == 0
    assert p["frac_ambiguos"] == pytest.approx(0.0)


def test_perfilar_par_conta_divergentes():
    df = pd.DataFrame(
        {"cidade": ["Boston"] * 4, "estado": ["MA", "MA", "MA", "TX"]}
    )
    p = perfilar_par(df, "cidade", "estado", dominancia=0.70)
    assert p["det"] == pytest.approx(0.75)
    assert p["n_divergentes"] == 1
    assert p["frac_ambiguos"] == pytest.approx(0.0)


def test_perfilar_par_acusa_grupo_ambiguo():
    df = pd.DataFrame({"voo": ["AA1"] * 4, "hora": ["10:30", "10:31", "10:28", "10:39"]})
    p = perfilar_par(df, "voo", "hora", dominancia=0.70)
    assert p["frac_ambiguos"] == pytest.approx(1.0)
    assert p["n_grupos"] == 1


def test_perfilar_par_ignora_grupo_de_uma_linha():
    df = pd.DataFrame({"a": ["x", "y"], "b": ["1", "2"]})
    p = perfilar_par(df, "a", "b", dominancia=0.70)
    assert p["n_grupos"] == 0
    assert p["det"] == pytest.approx(0.0)


def test_perfilar_le_o_sujo_como_texto_literal(tmp_path):
    sujo = tmp_path / "sujo.csv"
    sujo.write_text("a,b\nN/A,1\nx,2\n", encoding="utf-8")
    entrada = perfilar(sujo, None)
    assert list(entrada.sujo["a"]) == ["N/A", "x"]
    assert entrada.guia_linhas.empty
    assert entrada.guia_pares.empty


def test_perfilar_carrega_o_guia_quando_existe(tmp_path):
    sujo = tmp_path / "sujo.csv"
    sujo.write_text("a,b\nx,1\ny,2\n", encoding="utf-8")
    guia = tmp_path / "guia"
    guia.mkdir()
    (guia / "guia_linhas.csv").write_text("_linha,a,b\n0,x,1\n", encoding="utf-8")
    (guia / "guia_pares.csv").write_text("linha,coluna,sujo,limpo\n1,a,y,Y\n", encoding="utf-8")
    entrada = perfilar(sujo, guia)
    assert list(entrada.guia_linhas.index) == [0]
    assert entrada.guia_pares.iloc[0]["limpo"] == "Y"


def test_candidatas_sujeito_elegem_a_coluna_que_determina_mais():
    df = pd.DataFrame(
        {
            "id": [f"e{i}" for i in range(12)] * 2,
            "nome": [f"n{i}" for i in range(12)] * 2,
            "tipo": ["t"] * 24,
        }
    )
    pares = {}
    for a in df.columns:
        for b in df.columns:
            if a != b:
                pares[(a, b)] = perfilar_par(df, a, b, 0.70)
    assert pares[("id", "nome")]["det"] == pytest.approx(1.0)


def test_perfilar_par_mede_cobertura():
    df = pd.DataFrame({"a": ["x", "x", "y", "y", "z"], "b": ["1", "1", "2", "2", "3"]})
    p = perfilar_par(df, "a", "b", 0.70)
    assert p["cobertura"] == pytest.approx(0.8)
    assert p["n_grupos"] == 2


def test_perfilar_coluna_sem_linhas_tem_comprimento_zero():
    assert perfilar_coluna(pd.Series([], dtype=str))["comprimentos"] == (0, 0)

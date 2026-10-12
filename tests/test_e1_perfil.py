"""O perfil deterministico: padroes, estatisticas por coluna e os cinco numeros do par."""
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
    assert entrada.guia_pares["linha"].dtype.kind == "i"
    assert entrada.guia_linhas.index.dtype.kind == "i"


def _perfil_de(tmp_path, colunas):
    sujo = tmp_path / "sujo.csv"
    pd.DataFrame(colunas).to_csv(sujo, index=False)
    return perfilar(sujo, None).perfil


def test_candidatas_so_incluem_colunas_que_determinam_algo(tmp_path):
    n = 24
    perfil = _perfil_de(
        tmp_path,
        {
            "id": [f"e{i}" for i in range(n)],
            "cidade": [f"c{i % 6}" for i in range(n)],
            "estado": [f"s{(i % 6) // 2}" for i in range(n)],
            "tipo": ["t"] * n,
        },
    )
    assert perfil.candidatas_sujeito == ["cidade", "estado"]


def test_candidatas_desempatam_por_mais_distintos(tmp_path):
    n = 24
    perfil = _perfil_de(
        tmp_path,
        {"a": [f"a{i % 6}" for i in range(n)], "b": [f"b{i % 4}" for i in range(n)], "c": ["k"] * n},
    )
    assert perfil.candidatas_sujeito == ["a", "b"]


def test_perfilar_par_mede_cobertura():
    df = pd.DataFrame({"a": ["x", "x", "y", "y", "z"], "b": ["1", "1", "2", "2", "3"]})
    p = perfilar_par(df, "a", "b", 0.70)
    assert p["cobertura"] == pytest.approx(0.8)
    assert p["n_grupos"] == 2


def test_perfilar_coluna_sem_linhas_tem_comprimento_zero():
    assert perfilar_coluna(pd.Series([], dtype=str))["comprimentos"] == (0, 0)

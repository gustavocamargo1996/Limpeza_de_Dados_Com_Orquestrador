"""As cinco estrategias de reparo, e a excecao do lado errado da dependencia."""
import pandas as pd
import pytest

from limpeza2.motor import distancia_edicao, reparar


@pytest.fixture
def tabela():
    return pd.DataFrame(
        {
            "cidade": ["Boston", "Boston", "Boston", "Boston", "Austin", "Bosotn"],
            "estado": ["MA", "MA", "MA", "TX", "TX", "MA"],
            "zona": ["Temperate", "Temperate", "Tropcial", "Tropical", "N/A", ""],
            "onca": ["12", "12.0", "16", "16", "16", "12"],
        }
    )


def verdadeiro_em(tabela, posicoes):
    m = pd.Series(False, index=tabela.index)
    m.iloc[posicoes] = True
    return m


def test_normalizar_aplica_a_funcao_escalar(tabela):
    m = verdadeiro_em(tabela, [1])
    novo, reparada = reparar(
        tabela, "onca", "normalizar", {"funcao": "tira_ponto_zero"}, m,
        funcoes={"tira_ponto_zero": lambda v: v.replace(".0", "")},
    )
    assert novo.at[1, "onca"] == "12"
    assert list(reparada) == [False, True, False, False, False, False]


def test_normalizar_nao_toca_celula_fora_da_mascara(tabela):
    m = verdadeiro_em(tabela, [1])
    novo, _ = reparar(
        tabela, "onca", "normalizar", {"funcao": "f"}, m,
        funcoes={"f": lambda v: "ZZZ"},
    )
    assert list(novo["onca"]) == ["12", "ZZZ", "16", "16", "16", "12"]


def test_moda_condicionada_usa_a_maioria_do_grupo(tabela):
    m = verdadeiro_em(tabela, [3])
    novo, reparada = reparar(
        tabela, "estado", "moda_condicionada", {"determinantes": ["cidade"]}, m
    )
    assert novo.at[3, "estado"] == "MA"
    assert bool(reparada.iloc[3])


def test_moda_condicionada_nao_repara_grupo_ambiguo():
    df = pd.DataFrame({"voo": ["AA1"] * 4, "hora": ["10:30", "10:31", "10:28", "10:39"]})
    m = pd.Series(True, index=df.index)
    novo, reparada = reparar(df, "hora", "moda_condicionada", {"determinantes": ["voo"]}, m)
    assert list(novo["hora"]) == list(df["hora"])
    assert not reparada.any()


def test_corrige_o_determinante_quando_ele_e_o_erro_de_digitacao(tabela):
    m = verdadeiro_em(tabela, [5])
    novo, reparada = reparar(
        tabela, "estado", "moda_condicionada", {"determinantes": ["cidade"]}, m
    )
    assert novo.at[5, "cidade"] == "Boston"
    assert novo.at[5, "estado"] == "MA"
    assert bool(reparada.iloc[5])


def test_vizinho_no_dominio_troca_pelo_mais_parecido(tabela):
    m = verdadeiro_em(tabela, [2])
    novo, reparada = reparar(
        tabela, "zona", "vizinho_no_dominio",
        {"dominio": ["Temperate", "Tropical"], "distancia": 2}, m,
    )
    assert novo.at[2, "zona"] == "Tropical"
    assert bool(reparada.iloc[2])


def test_vizinho_no_dominio_desiste_quando_esta_longe(tabela):
    m = verdadeiro_em(tabela, [4])
    novo, reparada = reparar(
        tabela, "zona", "vizinho_no_dominio",
        {"dominio": ["Temperate", "Tropical"], "distancia": 2}, m,
    )
    assert novo.at[4, "zona"] == "N/A"
    assert not reparada.any()


def test_dicionario_substitui_o_que_esta_no_mapa(tabela):
    m = verdadeiro_em(tabela, [4])
    novo, reparada = reparar(
        tabela, "zona", "dicionario", {"mapa": {"N/A": "Desconhecida"}}, m
    )
    assert novo.at[4, "zona"] == "Desconhecida"
    assert bool(reparada.iloc[4])


def test_esvaziar_zera_a_celula(tabela):
    m = verdadeiro_em(tabela, [4])
    novo, reparada = reparar(tabela, "zona", "esvaziar", {}, m)
    assert novo.at[4, "zona"] == ""
    assert bool(reparada.iloc[4])


def test_reparar_nao_altera_o_dataframe_recebido(tabela):
    antes = tabela.copy()
    reparar(tabela, "zona", "esvaziar", {}, pd.Series(True, index=tabela.index))
    pd.testing.assert_frame_equal(tabela, antes)


@pytest.mark.parametrize(
    "a,b,esperado",
    [
        ("Boston", "Bosotn", 1),  # transposicao de adjacentes conta como uma edicao
        ("Boston", "Bostn", 1),
        ("Boston", "Boston", 0),
        ("ab", "xyzw", 4),
        ("Tropcial", "Tropical", 1),
    ],
)
def test_distancia_edicao(a, b, esperado):
    assert distancia_edicao(a, b) == esperado


def test_nao_reescreve_chave_legitima_e_frequente():
    df = pd.DataFrame(
        {"cidade": ["Boston"] * 3 + ["Bosotn"] * 2, "estado": ["MA"] * 5}
    )
    novo, reparada = reparar(
        df, "estado", "moda_condicionada", {"determinantes": ["cidade"]},
        pd.Series(True, index=df.index),
    )
    assert list(novo["cidade"]) == list(df["cidade"])
    assert not reparada.any()


def test_nao_corrige_chave_rara_para_outra_rara():
    df = pd.DataFrame({"cidade": ["Austin"] * 3 + ["Bosotn", "Boston"], "estado": ["MA"] * 5})
    m = verdadeiro_em(df, [3])
    novo, reparada = reparar(
        df, "estado", "moda_condicionada", {"determinantes": ["cidade"]}, m
    )
    assert novo.at[3, "cidade"] == "Bosotn"
    assert not reparada.any()


def test_dicionario_ignora_valor_fora_do_mapa(tabela):
    m = verdadeiro_em(tabela, [3, 4])
    novo, reparada = reparar(
        tabela, "zona", "dicionario", {"mapa": {"N/A": "Desconhecida"}}, m
    )
    assert novo.at[3, "zona"] == "Tropical"
    assert list(reparada) == [False, False, False, False, True, False]


def test_esvaziar_nao_conta_celula_ja_vazia(tabela):
    m = verdadeiro_em(tabela, [4, 5])
    _, reparada = reparar(tabela, "zona", "esvaziar", {}, m)
    assert list(reparada) == [False, False, False, False, True, False]


def test_vizinho_no_dominio_aceita_distancia_igual_ao_limite(tabela):
    m = verdadeiro_em(tabela, [2])
    novo, reparada = reparar(
        tabela, "zona", "vizinho_no_dominio",
        {"dominio": ["Tropical"], "distancia": 1}, m,
    )
    assert novo.at[2, "zona"] == "Tropical"
    assert bool(reparada.iloc[2])


def test_estrategia_desconhecida_falha_alto(tabela):
    with pytest.raises(ValueError):
        reparar(tabela, "zona", "inexistente", {}, verdadeiro_em(tabela, [0]))

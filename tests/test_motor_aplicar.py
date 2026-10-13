"""O laco que combina as regras: le sempre o original, primeiro a escrever vence."""
import pandas as pd

from limpeza2.motor import aplicar_regras


def regra(coluna, tipo, deteccao, estrategia=None, reparo=None):
    return {"coluna": coluna, "tipo": tipo, "deteccao": deteccao,
            "estrategia": estrategia, "reparo": reparo}


def cidades():
    return pd.DataFrame({"cidade": ["Boston", "Boston", "Boston", "Bostn"],
                         "estado": ["MA", "MA", "MA", "XX"]})


def oncas():
    return pd.DataFrame({"onca": ["12", "12 oz", "16", "N/A", "16"]})


def test_detecta_no_original_e_nao_no_que_outra_regra_escreveu():
    # Lendo o original, "Bostn" e grupo de uma linha so, e a dependencia nao marca nada.
    regras = [
        regra("cidade", "dominio", {"valores": ["Boston"]}, "dicionario", {"mapa": {"Bostn": "Boston"}}),
        regra("estado", "dependencia", {"determinantes": ["cidade"]},
              "moda_condicionada", {"determinantes": ["cidade"]}),
    ]
    novo, flags, fontes = aplicar_regras(cidades(), regras, {}, {})
    assert novo.at[3, "cidade"] == "Boston"
    assert novo.at[3, "estado"] == "XX"
    assert not flags.at[3, "estado"]
    assert fontes.at[3, "cidade"] == "dominio/dicionario"


def test_primeiro_a_escrever_vence():
    regras = [
        regra("onca", "dominio", {"valores": ["12", "16"]}, "dicionario", {"mapa": {"12 oz": "12"}}),
        regra("onca", "formato", {"regex": r"\d+"}, "dicionario", {"mapa": {"12 oz": "doze"}}),
    ]
    novo, _, fontes = aplicar_regras(oncas(), regras, {}, {})
    assert novo.at[1, "onca"] == "12"
    assert fontes.at[1, "onca"] == "dominio/dicionario"


def test_moda_escreve_tambem_no_determinante():
    regras = [regra("estado", "dominio", {"valores": ["MA"]},
                    "moda_condicionada", {"determinantes": ["cidade"]})]
    novo, flags, fontes = aplicar_regras(cidades(), regras, {}, {})
    assert (novo.at[3, "cidade"], novo.at[3, "estado"]) == ("Boston", "MA")
    assert fontes.at[3, "cidade"] == "dominio/moda_condicionada"
    assert not flags.any(axis=None)


def test_funcao_que_lanca_numa_celula_vira_flag_e_nao_derruba_a_tabela():
    def corrigir_1(valor):
        if valor == "N/A":
            raise ValueError("valor inedito")
        return valor.replace(" oz", "")
    regras = [regra("onca", "dominio", {"valores": ["12", "16"]}, "normalizar", {"funcao": "corrigir_1"})]
    novo, flags, fontes = aplicar_regras(oncas(), regras, {}, {"corrigir_1": corrigir_1})
    assert list(novo["onca"]) == ["12", "12", "16", "N/A", "16"]
    assert list(flags["onca"]) == [False, False, False, True, False]
    assert fontes.at[1, "onca"] == "dominio/normalizar"


def test_residual_age_so_em_celula_marcada_e_nao_reparada():
    regras = [regra("onca", "dominio", {"valores": ["12", "16"]})]
    residual = {"onca": {"12 oz": "12", "16": "dezesseis"}}
    novo, flags, fontes = aplicar_regras(oncas(), regras, residual, {})
    assert list(novo["onca"]) == ["12", "12", "16", "N/A", "16"]
    assert fontes.at[1, "onca"] == "residual"
    assert list(flags["onca"]) == [False, False, False, True, False]


def test_residual_nao_reescreve_o_que_a_regra_reparou():
    regras = [regra("onca", "dominio", {"valores": ["12", "16"]}, "dicionario", {"mapa": {"12 oz": "12"}})]
    novo, _, fontes = aplicar_regras(oncas(), regras, {"onca": {"12 oz": "XX"}}, {})
    assert novo.at[1, "onca"] == "12"
    assert fontes.at[1, "onca"] == "dominio/dicionario"


def test_nao_altera_o_dataframe_recebido():
    original = oncas()
    aplicar_regras(original, [regra("onca", "dominio", {"valores": ["12"]}, "esvaziar", {})], {}, {})
    assert original.equals(oncas())

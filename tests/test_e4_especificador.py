"""O especificador: estrategia de catalogo fechado, dominio deterministico, degradacao."""
import pandas as pd
import pytest

from limpeza2 import e4_especificador
from limpeza2.tipos import Candidata
from tests.apoio import CORTADA, monta_entrada


def sujo():
    return pd.DataFrame({
        "estado": ["MA", "MA", "TX", "TX", "XX", "MA", "TX", "MA", "MA", "YY"],
        "cidade": ["Boston", "Boston", "Austin", "Austin", "Boston",
                   "Boston", "Austin", "Boston", "Boston", "Austin"],
    })


def deteccao():
    return Candidata(coluna="estado", tipo="dominio", parametros={"valores": ["MA", "TX"]}, raciocinio="r")


def especificacao(estrategia, **campos):
    base = dict.fromkeys(["transformacao", "determinantes", "distancia", "mapa"])
    return {**base, **campos, "estrategia": estrategia,
            "raciocinio": {"padrao": "Duas letras.", "analise": "XX nao existe.", "acao": "Use a moda."}}


def test_dominio_e_deterministico_e_inclui_o_certificado():
    entrada = monta_entrada(sujo(), linhas_guia=[9], corrigidos={(9, "estado"): "RJ"})
    mascara = pd.Series([False] * 4 + [True] + [False] * 4 + [True])
    assert e4_especificador.dominio(entrada, "estado", mascara) == ["MA", "RJ", "TX"]


@pytest.mark.parametrize("resposta, esperado", [
    (especificacao("normalizar", transformacao="tirar o sufixo"), {"transformacao": "tirar o sufixo"}),
    (especificacao("moda_condicionada", determinantes=["cidade"]), {"determinantes": ["cidade"]}),
    (especificacao("dicionario", mapa=[{"sujo": "XX", "limpo": "MA"}]), {"mapa": {"XX": "MA"}}),
    (especificacao("esvaziar"), {}),
])
def test_converte_cada_estrategia_no_formato_do_motor(roteiro, resposta, esperado):
    roteiro(lambda instrucao, conteudo: resposta)
    [reparo] = e4_especificador.especificar([deteccao()], monta_entrada(sujo()))
    assert (reparo.estrategia, reparo.parametros) == (resposta["estrategia"], esperado)
    assert reparo.raciocinio == "Duas letras. XX nao existe. Use a moda."


def test_vizinho_recebe_o_dominio_calculado_e_nao_o_do_llm(roteiro):
    roteiro(lambda instrucao, conteudo: {**especificacao("vizinho_no_dominio", distancia=1),
                                         "dominio": ["inventado"]})
    [reparo] = e4_especificador.especificar([deteccao()], monta_entrada(sujo()))
    assert reparo.parametros == {"distancia": 1, "dominio": ["MA", "TX"]}


@pytest.mark.parametrize("resposta", [
    especificacao("normalizar", transformacao=""),
    especificacao("moda_condicionada", determinantes=["estado"]),
    especificacao("moda_condicionada", determinantes=["inexistente"]),
    especificacao("vizinho_no_dominio", distancia=7),
    especificacao("dicionario", mapa=[]),
    especificacao("inventada"),
])
def test_especificacao_invalida_nao_vira_proposta(roteiro, resposta):
    roteiro(lambda instrucao, conteudo: resposta)
    c = deteccao()
    assert e4_especificador.especificar([c], monta_entrada(sujo())) == []
    assert c.metricas["motivo_reparo"] == "especificacao_invalida"


def test_falha_do_llm_deixa_a_deteccao_sem_reparo(roteiro):
    roteiro(lambda instrucao, conteudo: CORTADA)
    c = deteccao()
    assert e4_especificador.especificar([c], monta_entrada(sujo())) == []
    assert c.metricas["motivo_reparo"] == "sem_especificacao"


def test_prompt_leva_os_valores_marcados_e_os_exemplos_do_guia(roteiro):
    api = roteiro(lambda instrucao, conteudo: especificacao("esvaziar"))
    entrada = monta_entrada(sujo(), pares=[(4, "estado", "XX", "MA")])
    e4_especificador.especificar([deteccao()], entrada)
    instrucao, conteudo = api.pedidos[0]
    assert instrucao == e4_especificador.INSTRUCAO
    assert "valores marcados (2 celulas): [('XX', 1), ('YY', 1)]" in conteudo
    assert "exemplo do guia: 'XX' -> 'MA'" in conteudo

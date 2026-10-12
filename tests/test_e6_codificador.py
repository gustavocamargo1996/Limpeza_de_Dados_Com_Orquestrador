"""O codificador: funcao escalar pelo portao, uma nova tentativa, e o limpador escrito."""
import pandas as pd

from limpeza2 import e6_codificador
from limpeza2.tipos import Candidata, Reparo
from tests.apoio import monta_entrada

BOM = "def corrigir(valor):\n    return valor.replace(' oz', '')"
RUIM = "def corrigir(valor):\n    import os\n    return valor"


def oncas():
    return pd.DataFrame({"onca": ["12", "12 oz", "16", "16 oz", "16"]})


def proposta(estrategia="normalizar", parametros=None):
    c = Candidata(coluna="onca", tipo="dominio", parametros={"valores": ["12", "16"]}, raciocinio="r")
    return Reparo(candidata=c, estrategia=estrategia,
                  parametros=parametros if parametros is not None else {"transformacao": "tirar ' oz'"},
                  raciocinio="r")


def test_funcao_aprovada_ganha_nome_unico_e_codigo(roteiro):
    roteiro(lambda instrucao, conteudo: {"codigo": BOM})
    primeira, segunda = proposta(), proposta()
    codificadas, funcoes = e6_codificador.codificar([primeira, segunda], monta_entrada(oncas()))
    assert codificadas == [primeira, segunda]
    assert [p.parametros["funcao"] for p in codificadas] == ["corrigir_1", "corrigir_2"]
    assert funcoes["corrigir_1"]("12 oz") == "12"
    assert primeira.codigo == BOM


def test_rejeitada_tenta_de_novo_com_a_mensagem_do_portao(roteiro):
    respostas = [{"codigo": RUIM}, {"codigo": BOM}]
    api = roteiro(lambda instrucao, conteudo: respostas.pop(0))
    codificadas, funcoes = e6_codificador.codificar([proposta()], monta_entrada(oncas()))
    assert len(codificadas) == 1 and "corrigir_1" in funcoes
    assert "A tentativa anterior foi rejeitada: import proibido" in api.pedidos[1][1]


def test_rejeitada_duas_vezes_cai(roteiro):
    api = roteiro(lambda instrucao, conteudo: {"codigo": RUIM})
    p = proposta()
    codificadas, funcoes = e6_codificador.codificar([p], monta_entrada(oncas()))
    assert (codificadas, funcoes) == ([], {})
    assert p.candidata.metricas["motivo_reparo"] == "codigo_rejeitado"
    assert "import proibido" in p.candidata.metricas["detalhe_reparo"]
    assert len(api.pedidos) == 2


def test_funcao_que_lanca_com_valor_real_e_rejeitada(roteiro):
    lanca = "def corrigir(valor):\n    return valor[10]"
    roteiro(lambda instrucao, conteudo: {"codigo": lanca})
    codificadas, _ = e6_codificador.codificar([proposta()], monta_entrada(oncas()))
    assert codificadas == []


def test_estrategia_sem_codigo_passa_sem_chamar_o_llm(roteiro):
    api = roteiro(lambda instrucao, conteudo: {"codigo": BOM})
    p = proposta("esvaziar", {})
    assert e6_codificador.codificar([p], monta_entrada(oncas())) == ([p], {})
    assert api.pedidos == []

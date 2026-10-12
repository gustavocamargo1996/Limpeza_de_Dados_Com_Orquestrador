"""O codificador: funcao escalar pelo portao, uma nova tentativa, e o limpador escrito."""
import pandas as pd
import pytest

from limpeza2 import e6_codificador, provedor
from limpeza2.tipos import Candidata, Reparo, Residual
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


def gerar(tmp_path, roteiro, nome="beers_teste", codigo=BOM, residual=(), tabela=None):
    """Escreve um limpador com uma deteccao de dominio reparada por uma funcao."""
    roteiro(lambda instrucao, conteudo: {})
    entrada = monta_entrada(oncas() if tabela is None else tabela)
    p = proposta(parametros={"transformacao": "tirar ' oz'", "funcao": "corrigir_1"})
    p.codigo = codigo
    destino = tmp_path / nome
    destino.mkdir(parents=True, exist_ok=True)
    caminho = e6_codificador.escrever([p.candidata], [p], list(residual), [p.candidata], entrada, destino)
    return caminho, entrada


def test_bloco_embutido_e_motor_byte_a_byte(tmp_path, roteiro):
    caminho, _ = gerar(tmp_path, roteiro)
    texto = caminho.read_bytes()
    inicio = (e6_codificador.INICIO + "\n").encode()
    bloco = texto.split(inicio, 1)[1].split(e6_codificador.FIM.encode(), 1)[0]
    assert bloco == e6_codificador.MOTOR.read_bytes()


def test_mesma_entrada_mesmo_texto(tmp_path, roteiro):
    a, _ = gerar(tmp_path / "a", roteiro)
    b, _ = gerar(tmp_path / "b", roteiro)
    assert a.read_bytes() == b.read_bytes()


def test_limpador_aplica_regras_e_residual(tmp_path, roteiro):
    tabela = pd.DataFrame({"onca": ["12", "12 oz", "16oz", "16"]})
    residual = [Residual(coluna="onca", mapa={"16oz": "16"}, justificativas={"16oz": "j"})]
    caminho, entrada = gerar(tmp_path, roteiro, residual=residual, tabela=tabela)
    modulo = carregar(caminho)
    corrigido, flags, fontes = modulo.aplicar_detalhado(entrada.sujo)
    assert list(corrigido["onca"]) == ["12", "12", "16", "16"]
    assert list(fontes["onca"]) == ["", "dominio/normalizar", "residual", ""]
    assert not flags.any(axis=None)
    assert modulo.FUNCOES["corrigir_1"]("12 oz") == "12"
    assert modulo.GERACAO_TRUNCADA is False


def test_cabecalho_avisa_do_portao_e_da_memoria_congelada(tmp_path, roteiro):
    caminho, _ = gerar(tmp_path, roteiro)
    texto = caminho.read_text(encoding="utf-8")
    assert "SEM o portao AST" in texto and "Memoria congelada" in texto


def test_teto_atingido_fica_marcado_no_artefato(tmp_path, roteiro):
    roteiro(lambda instrucao, conteudo: {})
    provedor.cliente().anotar("detector", "onca", "teto")
    entrada = monta_entrada(oncas())
    destino = tmp_path / "beers_teto"
    destino.mkdir()
    caminho = e6_codificador.escrever([], [], [], [], entrada, destino)
    modulo = carregar(caminho)
    assert (modulo.GERACAO_TRUNCADA, modulo.UNIDADES_DEGRADADAS_POR_TETO) == (True, 1)
    md = (destino / "raciocinio_beers_teto.md").read_text(encoding="utf-8")
    assert "unidades sem regra pelo teto de chamadas: 1" in md


def test_raciocinio_lista_a_reprovada(tmp_path, roteiro):
    reprovada = Candidata(coluna="onca", tipo="faixa", parametros={"minimo": 0, "maximo": 1},
                          raciocinio="chute")
    reprovada.metricas = {"motivo": "marca_demais", "marcadas": 5}
    roteiro(lambda instrucao, conteudo: {})
    destino = tmp_path / "beers_md"
    destino.mkdir()
    e6_codificador.escrever([], [], [], [reprovada], monta_entrada(oncas()), destino)
    md = (destino / "raciocinio_beers_md.md").read_text(encoding="utf-8")
    assert "### faixa: marca_demais" in md
    assert "- marcadas: 5" in md


def test_funcao_quebrada_derruba_a_fumaca_final(tmp_path, roteiro):
    with pytest.raises(NameError):
        gerar(tmp_path, roteiro, codigo="def corrigir(valor):\n    return valor + desconhecida")


def test_renomear_troca_so_o_nome_da_funcao():
    assert e6_codificador.renomear(BOM, "corrigir_7").startswith("def corrigir_7(valor):")


def carregar(caminho):
    import importlib.util
    spec = importlib.util.spec_from_file_location("limpador_teste", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo

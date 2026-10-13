"""O provedor: falha alto no desconhecido, degrada com nome no resto, e reproduz."""
import json

import httpx2
import openai
import pytest

from limpeza2 import config, provedor
from tests.apoio import CORTADA, em_fila, ok

REQUISICAO = httpx2.Request("POST", "http://x")


def pedir(c, conteudo="conteudo"):
    return c.pedir_json("detector", "estado", "instrucao", conteudo, {})


def test_provedor_desconhecido_falha_alto(monkeypatch):
    monkeypatch.setattr(config, "PROVEDOR", "opneai")
    with pytest.raises(ValueError, match="opneai"):
        provedor._construir_api()


def test_resposta_valida_vira_dict_e_entra_no_registro(tmp_path):
    c = provedor.Cliente(tmp_path, em_fila(ok({"regras": []})))
    assert pedir(c) == {"regras": []}
    assert c.registro == [{"etapa": "detector", "unidade": "estado", "status": "ok",
                           "detalhe": "", "tokens": 5}]


@pytest.mark.parametrize("bruto, motivo", [
    ({"texto": '{"a": 1', "fim": "stop", "tokens": 0, "recusa": None}, "json_invalido"),
    ({"texto": "[1, 2]", "fim": "stop", "tokens": 0, "recusa": None}, "json_invalido"),
    (CORTADA, "cortada"),
    ({"texto": None, "fim": "stop", "tokens": 0, "recusa": "nao posso"}, "recusada"),
])
def test_falha_vira_falha_do_llm_com_motivo(tmp_path, bruto, motivo):
    c = provedor.Cliente(tmp_path, em_fila(bruto))
    with pytest.raises(provedor.FalhaDoLLM) as erro:
        pedir(c)
    assert erro.value.motivo == motivo
    assert c.registro[-1]["status"] == motivo


def test_rede_esgotada_vira_falha_do_llm(tmp_path):
    c = provedor.Cliente(tmp_path, em_fila(openai.APIConnectionError(request=REQUISICAO)))
    with pytest.raises(provedor.FalhaDoLLM) as erro:
        pedir(c)
    assert erro.value.motivo == "rede"


def test_autenticacao_nao_degrada(tmp_path):
    negada = openai.AuthenticationError(
        "chave", response=httpx2.Response(401, request=REQUISICAO), body=None
    )
    with pytest.raises(openai.AuthenticationError):
        pedir(provedor.Cliente(tmp_path, em_fila(negada)))


def test_teto_de_chamadas(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TETO_CHAMADAS", 2)
    c = provedor.Cliente(tmp_path, em_fila(ok({}), ok({})))
    pedir(c)
    pedir(c)
    with pytest.raises(provedor.FalhaDoLLM) as erro:
        pedir(c)
    assert erro.value.motivo == "teto"
    assert [n["status"] for n in c.registro] == ["ok", "ok", "teto"]
    assert c.chamadas == 2


def test_gravado_reproduz_a_geracao_na_mesma_ordem(tmp_path, monkeypatch):
    original = provedor.Cliente(tmp_path / "a", em_fila(ok({"x": 1}), ok({"x": 2}), CORTADA))
    assert [pedir(original, "c1"), pedir(original, "c1")] == [{"x": 1}, {"x": 2}]
    with pytest.raises(provedor.FalhaDoLLM):
        pedir(original, "c2")
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(tmp_path / "a" / "respostas.jsonl"))
    copia = provedor.iniciar(tmp_path / "b")
    assert [pedir(copia, "c1"), pedir(copia, "c1")] == [{"x": 1}, {"x": 2}]
    with pytest.raises(provedor.FalhaDoLLM) as erro:
        pedir(copia, "c2")
    assert erro.value.motivo == "cortada"


def test_gravado_devolve_a_origem_gravada_e_a_regrava(tmp_path, monkeypatch):
    original = provedor.Cliente(tmp_path / "a", em_fila(ok({"x": 1})))
    pedir(original)
    monkeypatch.setattr(config, "MODELO", "outro-modelo")
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(tmp_path / "a" / "respostas.jsonl"))
    copia = provedor.iniciar(tmp_path / "b")
    assert copia.origem == original.origem
    assert copia.origem["modelo"] != "outro-modelo"
    assert pedir(copia) == {"x": 1}
    primeira = (tmp_path / "b" / "respostas.jsonl").read_text(encoding="utf-8").splitlines()[0]
    assert json.loads(primeira) == {"origem": original.origem}


def test_gravado_sem_a_resposta_levanta(tmp_path, monkeypatch):
    (tmp_path / "vazio.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(tmp_path / "vazio.jsonl"))
    with pytest.raises(KeyError):
        pedir(provedor.iniciar(tmp_path / "b"))


def test_cada_geracao_zera_registro_e_contador(tmp_path, monkeypatch):
    monkeypatch.setattr(provedor, "_construir_api", lambda: em_fila(ok({})))
    pedir(provedor.iniciar(tmp_path / "a"))
    segunda = provedor.iniciar(tmp_path / "b")
    assert (segunda.registro, segunda.chamadas) == ([], 0)
    assert provedor.cliente() is segunda


class SdkFalso:
    """Guarda os argumentos de chat.completions.create."""

    def __init__(self):
        self.chat = self
        self.completions = self

    def create(self, **argumentos):
        self.argumentos = argumentos
        raise openai.APIConnectionError(request=REQUISICAO)


def api_com_sdk_falso(esforco):
    api = provedor._Api.__new__(provedor._Api)
    api.sdk, api.esforco = SdkFalso(), esforco
    return api


def test_pedido_leva_esquema_estrito_temperatura_semente_e_esforco():
    api = api_com_sdk_falso("none")
    with pytest.raises(openai.APIConnectionError):
        api.responder("k", "instrucao", "conteudo", {"type": "object"})
    a = api.sdk.argumentos
    assert a["response_format"]["json_schema"]["strict"] is True
    assert (a["temperature"], a["seed"], a["reasoning_effort"]) == (0, config.SEMENTE, "none")
    assert a["model"] == config.MODELO


def test_parametro_none_sai_do_pedido(monkeypatch):
    monkeypatch.setattr(config, "TEMPERATURA", None)
    api = api_com_sdk_falso(None)
    with pytest.raises(openai.APIConnectionError):
        api.responder("k", "instrucao", "conteudo", {})
    assert "temperature" not in api.sdk.argumentos
    assert "reasoning_effort" not in api.sdk.argumentos


def test_plano_b_pede_json_object_e_descreve_o_esquema(monkeypatch):
    monkeypatch.setattr(config, "SAIDA_ESTRITA", False)
    api = api_com_sdk_falso("none")
    with pytest.raises(openai.APIConnectionError):
        api.responder("k", "instrucao", "conteudo", {"type": "object"})
    assert api.sdk.argumentos["response_format"] == {"type": "json_object"}
    assert '"type": "object"' in api.sdk.argumentos["messages"][0]["content"]

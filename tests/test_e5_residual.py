"""O residual: lotes por entidade deterministicos, consolidacao, teto de lotes."""
import pandas as pd

from limpeza2 import config, e5_residual, provedor
from limpeza2.tipos import Candidata, Perfil
from tests.apoio import CORTADA, monta_entrada


def tabela():
    return pd.DataFrame({
        # B aparece antes de A: a ordem da primeira linha difere da alfabetica.
        "cervejaria": ["B", "A", "B", "C", "A", "B"],
        "estado": ["MA", "TX", "XX", "CA", "YY", "MA"],
    })


def flags_em(df, celulas):
    flags = pd.DataFrame(False, index=df.index, columns=df.columns)
    for linha, coluna in celulas:
        flags.at[linha, coluna] = True
    return flags


def test_lotes_juntam_a_entidade_inteira_na_ordem_da_primeira_linha():
    df = tabela()
    flags = flags_em(df, [(2, "estado"), (4, "estado")])
    assert e5_residual.lotes_por_entidade(df, flags, "cervejaria") == [[0, 2, 5, 1, 4]]


def test_lote_cheio_abre_outro(monkeypatch):
    monkeypatch.setattr(config, "LINHAS_POR_LOTE", 3)
    df = tabela()
    flags = flags_em(df, [(2, "estado"), (4, "estado")])
    assert e5_residual.lotes_por_entidade(df, flags, "cervejaria") == [[0, 2, 5], [1, 4]]


def test_lote_exatamente_cheio_ainda_cabe(monkeypatch):
    monkeypatch.setattr(config, "LINHAS_POR_LOTE", 5)
    df = tabela()
    flags = flags_em(df, [(2, "estado"), (4, "estado")])
    assert e5_residual.lotes_por_entidade(df, flags, "cervejaria") == [[0, 2, 5, 1, 4]]


def test_entidade_maior_que_o_lote_guarda_as_linhas_com_flag(monkeypatch):
    monkeypatch.setattr(config, "LINHAS_POR_LOTE", 2)
    df = tabela()
    flags = flags_em(df, [(5, "estado")])
    assert e5_residual.lotes_por_entidade(df, flags, "cervejaria") == [[0, 5]]


def test_sem_sujeito_os_lotes_seguem_a_ordem_das_linhas():
    df = tabela()
    flags = flags_em(df, [(4, "estado"), (2, "estado")])
    assert e5_residual.lotes_por_entidade(df, flags, None) == [[2, 4]]


def test_consolidar_junta_iguais_e_derruba_divergentes():
    respostas = {
        ("estado", "XX"): {("MA", "a cervejaria A e de MA")},
        ("estado", "YY"): {("TX", "j1"), ("CA", "j2")},
    }
    [r] = e5_residual.consolidar(respostas)
    assert r.mapa == {"XX": "MA"}
    assert r.justificativas == {"XX": "a cervejaria A e de MA"}
    assert r.caidas == {"YY": "conflitante: ['CA', 'TX']"}


def entrada_com_deteccao():
    df = tabela()
    entrada = monta_entrada(df)
    entrada.perfil = Perfil(colunas={}, pares={}, candidatas_sujeito=["cervejaria"])
    deteccao = Candidata(coluna="estado", tipo="dominio",
                         parametros={"valores": ["MA", "TX", "CA"]}, raciocinio="r")
    return entrada, [deteccao]


def responder(sujeito, correcoes):
    def responde(instrucao, conteudo):
        if instrucao == e5_residual.INSTRUCAO_SUJEITO:
            return {"coluna": sujeito, "raciocinio": "nomeia a cervejaria"}
        return {"correcoes": correcoes}
    return responde


def test_resolver_ignora_null_igual_e_valor_nao_pedido(roteiro):
    roteiro(responder("cervejaria", [
        {"coluna": "estado", "sujo": "XX", "limpo": "MA", "justificativa": "j"},
        {"coluna": "estado", "sujo": "YY", "limpo": None, "justificativa": "j"},
        {"coluna": "estado", "sujo": "MA", "limpo": "TX", "justificativa": "j"},
        {"coluna": "estado", "sujo": "YY", "limpo": "YY", "justificativa": "j"},
    ]))
    entrada, deteccoes = entrada_com_deteccao()
    [r] = e5_residual.resolver(deteccoes, [], {}, entrada)
    assert r.mapa == {"XX": "MA"}
    nota = next(n for n in provedor.cliente().registro if n["status"] == "escolha")
    assert nota["detalhe"] == "cervejaria: nomeia a cervejaria"


def test_sem_flag_nao_chama_o_llm(roteiro):
    api = roteiro(responder("cervejaria", []))
    entrada, _ = entrada_com_deteccao()
    assert e5_residual.resolver([], [], {}, entrada) == []
    assert api.pedidos == []


def test_lote_alem_do_teto_vira_sem_lote(roteiro, monkeypatch):
    monkeypatch.setattr(config, "MAX_LOTES_RESIDUAL", 1)
    monkeypatch.setattr(config, "LINHAS_POR_LOTE", 3)
    roteiro(responder("cervejaria", []))
    entrada, deteccoes = entrada_com_deteccao()
    e5_residual.resolver(deteccoes, [], {}, entrada)
    status = [(n["unidade"], n["status"]) for n in provedor.cliente().registro]
    assert ("lote 1", "ok") in status and ("lote 2", "sem_lote") in status


def test_falha_no_lote_so_perde_o_lote(roteiro):
    def responde(instrucao, conteudo):
        if instrucao == e5_residual.INSTRUCAO_SUJEITO:
            return {"coluna": None, "raciocinio": "nenhuma"}
        return CORTADA
    roteiro(responde)
    entrada, deteccoes = entrada_com_deteccao()
    assert e5_residual.resolver(deteccoes, [], {}, entrada) == []

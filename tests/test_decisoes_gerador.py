"""As decisoes do usuario no gerador: leitura, crivo, herdadas, instrucao e reaproveitamento."""
import importlib.util
import json
import shutil

import pandas as pd
import pytest

from limpeza2 import config, e2_detector, e4_especificador, e5_residual, provedor
from limpeza2.e1_perfil import perfilar
from limpeza2.e3_crivo import crivar_deteccao, crivar_residual
from limpeza2.espinha import gerar_limpador
from limpeza2.tipos import Candidata, Residual
from tests.apoio import CORTADA, Roteiro, em_fila, monta_entrada, ok
from tests.test_e2_detector import entrada_minima, so_na, variante
from tests.test_invariante import FIXTURES, GUIA, PASTA_DO_RUN, SUJO, sem_cr


def guia_com(tmp_path, decisoes):
    """Copia o guia do beers para tmp e grava nele o decisoes.json."""
    pasta = tmp_path / "guia"
    shutil.copytree(GUIA, pasta)
    (pasta / "decisoes.json").write_text(json.dumps(decisoes), encoding="utf-8")
    return pasta


def test_sem_decisoes_json_a_lista_e_vazia():
    assert perfilar(SUJO, GUIA).decisoes == []


def test_le_o_decisoes_json_da_pasta_do_guia(tmp_path):
    d = {"coluna": "ibu", "tipo": "faixa", "parametros": {"minimo": 0, "maximo": 150},
         "decisao": "aprovar"}
    entrada = perfilar(SUJO, guia_com(tmp_path, [d]))
    assert entrada.decisao("ibu", "faixa", {"minimo": 0, "maximo": 150}) == d
    assert entrada.decisao("ibu", "faixa", {"minimo": 0, "maximo": 151}) is None


def test_decisoes_vazias_geram_o_mesmo_limpador_e_raciocinio(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(FIXTURES / "respostas_beers_poc2.jsonl"))
    sem = gerar_limpador(SUJO, GUIA, tmp_path / "a" / PASTA_DO_RUN)
    com = gerar_limpador(SUJO, guia_com(tmp_path, []), tmp_path / "b" / PASTA_DO_RUN)
    assert sem_cr(com) == sem_cr(sem) == sem_cr(FIXTURES / "limpador_beers_poc2.py")
    nome = f"raciocinio_{PASTA_DO_RUN}.md"
    assert sem_cr(com.parent / nome) == sem_cr(sem.parent / nome)


# --- O crivo honra as decisoes -------------------------------------------------------------

def _sujo_dez():
    return pd.DataFrame({
        "estado": ["MA", "MA", "TX", "TX", "XX", "MA", "TX", "MA", "MA", "YY"],
        "cidade": ["Boston", "Boston", "Austin", "Austin", "Boston",
                   "Boston", "Austin", "Boston", "Boston", "Austin"],
    })


def _cand(tipo, parametros, coluna="estado"):
    return Candidata(coluna=coluna, tipo=tipo, parametros=parametros, raciocinio="x")


def _decide(entrada, candidata, decisao, **extra):
    entrada.decisoes.append({"coluna": candidata.coluna, "tipo": candidata.tipo,
                             "parametros": candidata.parametros, "decisao": decisao, **extra})


def test_rejeitar_tira_a_regra_aprovada():
    entrada = monta_entrada(_sujo_dez())
    c = _cand("dominio", {"valores": ["MA", "TX"]})
    _decide(entrada, c, "rejeitar")
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "rejeitada_pelo_usuario"
    assert c.metricas["decisao"] == "rejeitar"


def test_aprovar_dispensa_o_teto_de_marcacao():
    entrada = monta_entrada(_sujo_dez())
    c = _cand("formato", {"regex": r"[A-Z]{3}"})
    _decide(entrada, c, "aprovar")
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["motivo"] == "aprovada"


def test_aprovar_nao_dispensa_o_teste_contra_o_guia():
    entrada = monta_entrada(_sujo_dez(), linhas_guia=(0, 1, 2))
    c = _cand("dominio", {"valores": ["TX"]})
    _decide(entrada, c, "aprovar")
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "marca_celula_correta"


def test_aprovar_dispensa_a_ambiguidade_da_dependencia():
    sujo = pd.DataFrame({"voo": ["AA1"] * 4 + ["AA2"] * 4,
                         "hora": ["10:30", "10:30", "10:30", "10:39",
                                  "11:00", "11:00", "11:00", "11:03"]})
    entrada = monta_entrada(sujo)
    entrada.perfil.pares[("voo", "hora")] = {
        "det": 0.75, "n_grupos": 2, "n_divergentes": 2, "frac_ambiguos": 1.0}
    c = _cand("dependencia", {"determinantes": ["voo"]}, coluna="hora")
    _decide(entrada, c, "aprovar")
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["motivo"] == "aprovada"


def test_a_variante_aprovada_pelo_usuario_vence_a_disputa():
    entrada = monta_entrada(_sujo_dez())
    larga = _cand("dominio", {"valores": ["MA", "TX"]})
    estreita = _cand("dominio", {"valores": ["MA", "TX", "YY"]})
    _decide(entrada, larga, "aprovar")
    assert crivar_deteccao([larga, estreita], entrada) == [larga]
    assert (larga.metricas["motivo"], estreita.metricas["motivo"]) == ("aprovada", "superada")
    assert crivar_deteccao([estreita, larga], entrada) == [larga]


def test_rejeitar_entrada_do_residual():
    entrada = monta_entrada(_sujo_dez())
    entrada.decisoes.append({"coluna": "estado", "tipo": "residual", "parametros": {"sujo": "XX"},
                             "decisao": "rejeitar"})
    [r] = crivar_residual([Residual(coluna="estado", mapa={"XX": "MA", "YY": "TX"},
                                    justificativas={})], entrada)
    assert r.mapa == {"YY": "TX"}
    assert r.caidas == {"XX": "rejeitada_pelo_usuario"}


# --- Candidatas herdadas -------------------------------------------------------------------

def _aprova_dominio(entrada, valores, decisao="aprovar", tipo="dominio"):
    entrada.decisoes.append({"coluna": "estado", "tipo": tipo, "parametros": {"valores": valores},
                             "decisao": decisao, "versao": "v1"})


def test_regra_aprovada_e_nao_proposta_entra_como_herdada(roteiro):
    entrada = entrada_minima()
    _aprova_dominio(entrada, ["MA", "TX"])
    roteiro(so_na("estado", []))
    [c] = e2_detector.propor(entrada, [], [])
    assert (c.coluna, c.tipo, c.parametros) == ("estado", "dominio", {"valores": ["MA", "TX"]})
    assert c.raciocinio == "aprovada pelo usuario na versao v1"


def test_regra_aprovada_e_proposta_de_novo_nao_se_duplica(roteiro):
    entrada = entrada_minima()
    _aprova_dominio(entrada, ["MA", "TX"])
    roteiro(so_na("estado", [variante("dominio", valores=["MA", "TX"])]))
    [c] = e2_detector.propor(entrada, [], [])
    assert c.raciocinio == "r"


def test_rejeitada_e_residual_nao_viram_candidata(roteiro):
    entrada = entrada_minima()
    _aprova_dominio(entrada, ["MA", "TX"], decisao="rejeitar")
    _aprova_dominio(entrada, ["MA"], tipo="residual")
    roteiro(so_na("estado", []))
    assert e2_detector.propor(entrada, [], []) == []


# --- Instrucao do usuario no especificador -------------------------------------------------

def _conteudo_com(decisoes):
    entrada = monta_entrada(_sujo_dez())
    entrada.decisoes = decisoes
    c = _cand("dominio", {"valores": ["MA", "TX"]})
    mascara = pd.Series([v not in ("MA", "TX") for v in entrada.sujo["estado"]])
    return e4_especificador._conteudo(c, entrada, mascara)


def test_instrucao_do_usuario_entra_no_prompt_do_especificador():
    d = {"coluna": "estado", "tipo": "dominio", "parametros": {"valores": ["MA", "TX"]},
         "decisao": "aprovar", "instrucao": "use a sigla do estado vizinho"}
    assert _conteudo_com([d]).splitlines()[-1] == (
        "instrucao do usuario, valida desde que reproduza os exemplos do guia: "
        "use a sigla do estado vizinho")


def test_sem_instrucao_o_prompt_do_especificador_nao_muda():
    d = {"coluna": "estado", "tipo": "dominio", "parametros": {"valores": ["MA", "TX"]},
         "decisao": "aprovar", "instrucao": None}
    assert _conteudo_com([d]) == _conteudo_com([])
    assert "instrucao do usuario" not in _conteudo_com([])


# --- PROVEDOR=reaproveitar -----------------------------------------------------------------

RESPOSTAS_MVP = FIXTURES / "respostas_beers_poc2.jsonl"


def _reaproveitar(monkeypatch, gravadas, responder=None):
    """Liga o modo reaproveitar com uma API viva de mentira; devolve o roteiro dela."""
    vivo = Roteiro(responder or (lambda instrucao, conteudo: CORTADA))
    monkeypatch.setattr(config, "PROVEDOR", "reaproveitar")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(gravadas))
    monkeypatch.setattr(config, "MODELO", "gpt-6-luna")
    monkeypatch.setattr(provedor, "_api_viva", lambda nome: vivo)
    return vivo


def test_reaproveitar_reproduz_o_mvp_sem_chamar_a_api_viva(tmp_path, monkeypatch):
    vivo = _reaproveitar(monkeypatch, RESPOSTAS_MVP)
    caminho = gerar_limpador(SUJO, GUIA, tmp_path / PASTA_DO_RUN)
    assert sem_cr(caminho) == sem_cr(FIXTURES / "limpador_beers_poc2.py")
    assert vivo.pedidos == []


def test_reaproveitar_chama_a_api_viva_so_para_o_que_falta(tmp_path, monkeypatch):
    original = provedor.Cliente(tmp_path / "a", em_fila(ok({"x": 1})))
    original.pedir_json("detector", "estado", "instrucao", "c1", {})
    vivo = _reaproveitar(monkeypatch, tmp_path / "a" / "respostas.jsonl",
                         lambda instrucao, conteudo: {"x": 2})
    monkeypatch.setattr(config, "MODELO", original.origem["modelo"])
    copia = provedor.iniciar(tmp_path / "b")
    assert copia.pedir_json("detector", "estado", "instrucao", "c1", {}) == {"x": 1}
    assert copia.pedir_json("detector", "estado", "instrucao", "c2", {}) == {"x": 2}
    assert [conteudo for _, conteudo in vivo.pedidos] == ["c2"]
    gravadas = (tmp_path / "b" / "respostas.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(gravadas) == 3 and json.loads(gravadas[0]) == {"origem": original.origem}


def test_reaproveitar_com_provedor_vivo_desconhecido_falha_alto(monkeypatch):
    monkeypatch.setattr(config, "PROVEDOR", "reaproveitar")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(RESPOSTAS_MVP))
    monkeypatch.setattr(config, "PROVEDOR_VIVO", "opneai")
    with pytest.raises(ValueError, match="PROVEDOR_VIVO='opneai'.*Nao caio para openai"):
        provedor._construir_api()


def test_reaproveitar_com_modelo_diferente_do_gravado_falha_alto(monkeypatch):
    _reaproveitar(monkeypatch, RESPOSTAS_MVP)
    monkeypatch.setattr(config, "MODELO", "outro-modelo")
    with pytest.raises(ValueError, match="difere do gravado"):
        provedor._construir_api()


# --- O ciclo de aperfeicoamento sobre o MVP ------------------------------------------------

MODA_DO_ID = {"coluna": "brewery_id", "tipo": "dependencia",
              "parametros": {"determinantes": ["brewery-name"]}}


def _limpador(caminho):
    spec = importlib.util.spec_from_file_location("limpador_teste", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_rejeitar_a_moda_do_id_tira_a_regra_sem_chamada_nova(tmp_path, monkeypatch):
    vivo = _reaproveitar(monkeypatch, RESPOSTAS_MVP)
    guia = guia_com(tmp_path, [{**MODA_DO_ID, "decisao": "rejeitar"}])
    caminho = gerar_limpador(SUJO, guia, tmp_path / PASTA_DO_RUN)
    regras = [(r["coluna"], r["tipo"]) for r in _limpador(caminho).REGRAS]
    assert ("brewery_id", "dependencia") not in regras and len(regras) == 10
    raciocinio = (caminho.parent / f"raciocinio_{PASTA_DO_RUN}.md").read_text(encoding="utf-8")
    assert "### dependencia: rejeitada_pelo_usuario" in raciocinio
    # Assinatura do comportamento: rejeitar esta regra nao muda prompt nenhum.
    assert vivo.pedidos == []


def test_instrucao_numa_regra_aprovada_reespecifica_so_ela(tmp_path, monkeypatch):
    vivo = _reaproveitar(monkeypatch, RESPOSTAS_MVP)
    guia = guia_com(tmp_path, [{**MODA_DO_ID, "decisao": "aprovar", "instrucao": "nao mude o id"}])
    gerar_limpador(SUJO, guia, tmp_path / PASTA_DO_RUN)
    # Assinatura: o especificador da regra (prompt novo) e, como a API viva de mentira
    # corta a resposta, o lote do residual que passa a ver as celulas sem reparo.
    [(especificador, conteudo), (residual, _)] = vivo.pedidos
    assert especificador == e4_especificador.INSTRUCAO
    assert conteudo.endswith("exemplos do guia: nao mude o id")
    assert residual == e5_residual.INSTRUCAO

"""As decisoes do usuario no gerador: leitura, crivo, herdadas, instrucao e reaproveitamento."""
import json
import shutil

import pandas as pd

from limpeza2 import config, e2_detector
from limpeza2.e1_perfil import perfilar
from limpeza2.e3_crivo import crivar_deteccao, crivar_residual
from limpeza2.espinha import gerar_limpador
from limpeza2.tipos import Candidata, Residual
from tests.apoio import monta_entrada
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

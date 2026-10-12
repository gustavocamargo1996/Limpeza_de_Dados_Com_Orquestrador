"""O detector: catalogo por coluna, conversao que descarta o malformado, degradacao."""
import pandas as pd

from limpeza2 import e2_detector
from limpeza2.e1_perfil import perfilar_coluna
from limpeza2.tipos import Candidata, Entrada, Perfil
from tests.apoio import CORTADA

PAR = {("cidade", "estado"): {"det": 0.83, "n_grupos": 2, "n_divergentes": 1,
                              "frac_ambiguos": 0.0, "cobertura": 1.0}}


def entrada_minima(pares=None):
    sujo = pd.DataFrame({"cidade": ["Boston"] * 3 + ["Austin"] * 3,
                         "estado": ["MA", "MA", "XX", "TX", "TX", "TX"]})
    return Entrada(
        sujo=sujo, guia_linhas=pd.DataFrame(columns=sujo.columns),
        guia_pares=pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"]),
        perfil=Perfil(colunas={c: perfilar_coluna(sujo[c]) for c in sujo},
                      pares=pares or {}, candidatas_sujeito=[]),
    )


def conformidade(coluna, motivo):
    c = Candidata(coluna=coluna, tipo="conformidade", parametros={"padroes": ["A"]}, raciocinio="x")
    c.metricas = {"motivo": motivo}
    return c


def variante(tipo, **campos):
    base = dict.fromkeys(["regex", "valores", "minimo", "maximo", "sentinelas", "determinantes"])
    return {**base, **campos, "tipo": tipo, "raciocinio": "r"}


def so_na(coluna, regras):
    """Responde `regras` para a coluna pedida e nada para as outras."""
    return lambda instrucao, conteudo: {"regras": regras if f"coluna: {coluna}\n" in conteudo else []}


def test_formato_sai_so_quando_a_conformidade_da_coluna_foi_aprovada():
    entrada, aprovada = entrada_minima(), conformidade("estado", "aprovada")
    assert "formato" not in e2_detector.catalogo(entrada, "estado", [aprovada])
    assert "formato" in e2_detector.catalogo(entrada, "cidade", [aprovada])
    assert "formato" in e2_detector.catalogo(entrada, "estado", [])


def test_dependencia_so_onde_a_coluna_e_o_lado_determinado():
    assert "dependencia" in e2_detector.catalogo(entrada_minima(PAR), "estado", [])
    assert "dependencia" not in e2_detector.catalogo(entrada_minima(PAR), "cidade", [])
    assert "dependencia" not in e2_detector.catalogo(entrada_minima(), "estado", [])


def test_caso_da_conformidade_nos_quatro_casos():
    aprovada, vacua = conformidade("estado", "aprovada"), conformidade("estado", "vacua")
    reprovada = conformidade("estado", "perde_par_do_guia")
    caso = e2_detector.caso_da_conformidade
    assert caso("estado", [aprovada], [aprovada]).startswith("aprovada:")
    assert caso("estado", [], [vacua]).startswith("vacua:")
    assert caso("estado", [], [reprovada]).startswith("reprovada (perde_par_do_guia)")
    assert caso("estado", [], []).startswith("sem schema:")


def test_variante_malformada_cai_sozinha(roteiro):
    roteiro(so_na("estado", [
        variante("dominio", valores=["MA", "TX"]),
        variante("dominio", valores=[]),
        variante("faixa", minimo=None, maximo=3),
        variante("faixa", minimo=5, maximo=1),
        variante("formato", regex=None),
        {"tipo": "inexistente"},
        "nem e objeto",
    ]))
    candidatas = e2_detector.propor(entrada_minima(), [], [])
    assert [(c.coluna, c.tipo, c.parametros) for c in candidatas] == [
        ("estado", "dominio", {"valores": ["MA", "TX"]})
    ]


def test_faixa_com_limite_infinito_cai(roteiro):
    roteiro(so_na("estado", [
        variante("faixa", minimo=float("inf"), maximo=float("inf")),
        variante("faixa", minimo=float("-inf"), maximo=3),
        variante("faixa", minimo=1, maximo=3),
    ]))
    candidatas = e2_detector.propor(entrada_minima(), [], [])
    assert [c.parametros for c in candidatas] == [{"minimo": 1, "maximo": 3}]


def test_no_maximo_tres_variantes_por_tipo(roteiro):
    roteiro(so_na("estado", [variante("dominio", valores=[v]) for v in ("MA", "TX", "XX", "YY")]))
    candidatas = e2_detector.propor(entrada_minima(), [], [])
    assert [c.parametros["valores"] for c in candidatas] == [["MA"], ["TX"], ["XX"]]


def test_tipo_fora_do_catalogo_da_coluna_cai(roteiro):
    aprovada = conformidade("estado", "aprovada")
    roteiro(so_na("estado", [variante("formato", regex="[A-Z]{2}")]))
    assert e2_detector.propor(entrada_minima(), [aprovada], [aprovada]) == []


def test_falha_do_llm_deixa_so_aquela_coluna_sem_regra(roteiro):
    def responder(instrucao, conteudo):
        if "coluna: cidade\n" in conteudo:
            return CORTADA
        return {"regras": [variante("dominio", valores=["MA", "TX"])]}
    api = roteiro(responder)
    candidatas = e2_detector.propor(entrada_minima(), [], [])
    assert [c.coluna for c in candidatas] == ["estado"]
    assert len(api.pedidos) == 2


def test_prompt_leva_o_caso_o_catalogo_e_o_par_minerado(roteiro):
    api = roteiro(lambda instrucao, conteudo: {"regras": []})
    e2_detector.propor(entrada_minima(PAR), [], [conformidade("estado", "vacua")])
    instrucao, conteudo = next(p for p in api.pedidos if "coluna: estado\n" in p[1])
    assert instrucao == e2_detector.INSTRUCAO
    assert "conformidade de schema: vacua:" in conteudo
    assert "catalogo: formato, dominio, faixa, ausente_disfarcado, dependencia" in conteudo
    assert "par minerado: cidade -> estado" in conteudo

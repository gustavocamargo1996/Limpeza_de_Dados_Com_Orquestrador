"""O crivo: cinco testes sem LLM e sem gabarito. Ver docs/DECISOES.md#crivo-sem-vacuidade."""
import pandas as pd
import pytest

from limpeza2.e3_crivo import crivar_deteccao, crivar_reparo
from limpeza2.tipos import Candidata, Entrada, Perfil, Reparo


def monta_entrada(sujo, linhas_guia=(), pares=()):
    guia_linhas = sujo.loc[list(linhas_guia)] if linhas_guia else pd.DataFrame(
        columns=sujo.columns
    )
    guia_pares = pd.DataFrame(
        list(pares), columns=["linha", "coluna", "sujo", "limpo"]
    ) if pares else pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"])
    return Entrada(
        sujo=sujo,
        guia_linhas=guia_linhas,
        guia_pares=guia_pares,
        perfil=Perfil(colunas={}, pares={}, candidatas_sujeito=[]),
    )


@pytest.fixture
def sujo():
    # Dez linhas, com DUAS celulas estranhas em estado: XX na linha 4 e YY na
    # linha 9. Duas sao o minimo para distinguir "marcou algo" de "pegou o par".
    return pd.DataFrame(
        {
            "estado": ["MA", "MA", "TX", "TX", "XX", "MA", "TX", "MA", "MA", "YY"],
            "cidade": ["Boston", "Boston", "Austin", "Austin", "Boston",
                       "Boston", "Austin", "Boston", "Boston", "Austin"],
            # So existe para o caso de determinante composto: sem ela, o
            # groupby lancaria KeyError e o motivo seria "lancou".
            "zona": ["T"] * 10,
        }
    )


def candidata(tipo, parametros, coluna="estado"):
    return Candidata(coluna=coluna, tipo=tipo, parametros=parametros, raciocinio="x")


def test_aprova_regra_que_marca_pouco_e_acha_erro(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["marcadas"] == 2
    assert c.metricas["motivo"] == "aprovada"


def test_reprova_regra_vacua(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("dominio", {"valores": ["MA", "TX", "XX", "YY"]})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["marcadas"] == 0
    assert c.metricas["motivo"] == "vacua"


def test_reprova_regra_que_marca_a_coluna_inteira(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("formato", {"regex": r"[A-Z]{3}"})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "marca_demais"


def test_reprova_regra_que_toca_linha_limpa_do_guia(sujo):
    entrada = monta_entrada(sujo, linhas_guia=(0, 1, 2))
    c = candidata("dominio", {"valores": ["TX"]})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "toca_linha_limpa"


def test_reprova_regra_que_perde_par_do_guia(sujo):
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    # Marca a linha 9 (YY) e nao marca a 4 (XX), que e a do par: passa na
    # nao-vacuidade e no teto, e cai justamente no piso do guia.
    c = candidata("dominio", {"valores": ["MA", "TX", "XX"]})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["marcadas"] == 1
    assert c.metricas["motivo"] == "perde_par_do_guia"


def test_aprova_regra_que_pega_o_par_do_guia(sujo):
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    assert crivar_deteccao([c], entrada) == [c]


def test_reprova_dependencia_ambigua():
    sujo = pd.DataFrame(
        {"voo": ["AA1"] * 4 + ["AA2"] * 4,
         "hora": ["10:30", "10:31", "10:28", "10:39", "11:00", "11:01", "11:02", "11:03"]}
    )
    entrada = monta_entrada(sujo)
    entrada.perfil.pares[("voo", "hora")] = {
        "det": 0.5, "n_grupos": 2, "n_divergentes": 6, "frac_ambiguos": 1.0
    }
    c = candidata("dependencia", {"determinantes": ["voo"]}, coluna="hora")
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "ambigua"


def test_reprova_regra_que_lanca(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("formato", {"regex": "[["})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "lancou"


def test_entre_variantes_fica_a_que_marca_menos(sujo):
    entrada = monta_entrada(sujo)
    # As DUAS passam nos cinco testes: a larga marca 2 celulas, a estreita 1.
    # Se uma fosse reprovada pelo teto, o teste nao estaria medindo a escolha.
    larga = candidata("dominio", {"valores": ["MA", "TX"]})
    estreita = candidata("dominio", {"valores": ["MA", "TX", "YY"]})
    sobreviventes = crivar_deteccao([larga, estreita], entrada)
    assert sobreviventes == [estreita]
    assert larga.metricas["motivo"] == "aprovada"
    assert larga.metricas["marcadas"] == 2
    assert estreita.metricas["marcadas"] == 1


@pytest.mark.parametrize(
    "determinantes", [["cidade", "zona"], ["cidade"]], ids=["composto", "sem_entrada"]
)
def test_reprova_dependencia_sem_perfil(sujo, determinantes):
    entrada = monta_entrada(sujo)
    c = candidata("dependencia", {"determinantes": determinantes}, coluna="estado")
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "sem_perfil"


def test_crivar_reparo_guarda_contra_reparo_fora_da_mascara(sujo):
    # Guarda de regressao, nao caminho normal: nenhuma das cinco estrategias
    # toca linha fora da mascara, e este teste e o que acusa se alguma passar
    # a tocar. Por isso chama a funcao interna direto.
    from limpeza2.e3_crivo import _reprovar_reparo

    entrada = monta_entrada(sujo, linhas_guia=(0, 1))
    novo = entrada.sujo.copy()
    novo.at[0, "estado"] = "ZZ"
    reparada = pd.Series(False, index=novo.index)
    reparada.loc[4] = True
    assert _reprovar_reparo(entrada, novo, reparada) == "toca_linha_limpa"


def test_crivar_reparo_aprova_quem_repara_e_respeita_o_guia(sujo):
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(
        candidata=c,
        estrategia="moda_condicionada",
        parametros={"determinantes": ["cidade"]},
        raciocinio="x",
    )
    # Marca as linhas 4 (XX) e 9 (YY). O grupo Boston tem moda MA em 5 de 6, e
    # o grupo Austin tem TX em 3 de 4, entao as duas sao reparadas.
    assert crivar_reparo([r], entrada) == [r]
    assert r.candidata.metricas["reparadas"] == 2
    assert r.candidata.metricas["motivo_reparo"] == "aprovada"


def test_crivar_reparo_reprova_quem_nao_repara_nada(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(
        candidata=c, estrategia="dicionario", parametros={"mapa": {"ZZ": "MA"}},
        raciocinio="x",
    )
    assert crivar_reparo([r], entrada) == []
    assert r.candidata.metricas["motivo_reparo"] == "nao_repara"

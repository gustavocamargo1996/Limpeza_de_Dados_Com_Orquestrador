"""O crivo: cinco testes sem LLM e sem gabarito. Ver docs/DECISOES.md#crivo-sem-vacuidade."""
import pandas as pd
import pytest

from limpeza2 import config
from limpeza2.e3_crivo import (
    _marca_valor_certificado, _reprovar_reparo, crivar_deteccao, crivar_reparo,
)
from limpeza2.limites import teto_da_coluna
from limpeza2.tipos import Candidata, Entrada, Perfil, Reparo


def monta_entrada(sujo, linhas_guia=(), pares=(), corrigidos=None):
    """O guia traz o valor do sujo, salvo nas celulas de `corrigidos` {(linha, coluna): valor}."""
    guia_linhas = sujo.loc[list(linhas_guia)].copy() if linhas_guia else pd.DataFrame(
        columns=sujo.columns
    )
    for (linha, coluna), valor in (corrigidos or {}).items():
        guia_linhas.at[linha, coluna] = valor
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


def test_reprova_regra_que_marca_celula_correta_do_guia(sujo):
    entrada = monta_entrada(sujo, linhas_guia=(0, 1, 2))
    c = candidata("dominio", {"valores": ["TX"]})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "marca_celula_correta"


def test_aprova_regra_que_marca_so_celula_errada_do_guia(sujo):
    # A linha 4 (XX) esta no guia corrigida para MA: marcar o XX e o certo.
    entrada = monta_entrada(sujo, linhas_guia=(4,), corrigidos={(4, "estado"): "MA"})
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["marcadas"] == 2
    assert c.metricas["motivo"] == "aprovada"


def test_controle_negativo_so_olha_a_coluna_da_candidata(sujo):
    # O guia nao tem a coluna `estado`: nada a comparar, e a regra segue para os outros testes.
    entrada = monta_entrada(sujo, linhas_guia=(0, 4))
    entrada.guia_linhas = entrada.guia_linhas[["cidade"]]
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    assert crivar_deteccao([c], entrada) == [c]


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
    c = candidata("formato", {"regex": "("})
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
    assert crivar_deteccao([estreita, larga], entrada) == [estreita]


def test_reprova_taxa_acima_do_teto_sem_ser_a_coluna_inteira(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("dominio", {"valores": ["MA"]})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["marcadas"] == 5
    assert c.metricas["motivo"] == "marca_demais"


@pytest.mark.parametrize(
    "determinantes", [["cidade", "zona"], ["cidade"]], ids=["composto", "sem_entrada"]
)
def test_reprova_dependencia_sem_perfil(sujo, determinantes):
    entrada = monta_entrada(sujo)
    # Entrada de baixa ambiguidade para ["cidade"]: o composto so e reprovado
    # pela ramificacao de tamanho, nunca por falta de entrada.
    entrada.perfil.pares[("cidade", "estado")] = {
        "det": 0.9, "n_grupos": 2, "n_divergentes": 2, "frac_ambiguos": 0.0
    }
    c = candidata("dependencia", {"determinantes": determinantes}, coluna="estado")
    if determinantes == ["cidade"]:
        entrada.perfil.pares.clear()
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "sem_perfil"


def test_crivar_reparo_guarda_contra_reparo_fora_da_mascara(sujo):
    # Guarda de regressao: nenhuma estrategia toca linha fora da mascara, e
    # este teste acusa se alguma passar a tocar. Chama a funcao interna.
    entrada = monta_entrada(sujo, linhas_guia=(0, 1))
    novo = entrada.sujo.copy()
    novo.at[0, "estado"] = "ZZ"
    reparada = pd.Series(False, index=novo.index)
    reparada.loc[4] = True
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    r = Reparo(candidata=c, estrategia="dicionario", parametros={}, raciocinio="x")
    mascara = pd.Series(False, index=novo.index)
    assert _reprovar_reparo(entrada, novo, reparada, r, mascara) == "corrompe_celula_do_guia"


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


def test_crivar_reparo_reprova_quem_repara_o_par_para_o_valor_errado(sujo):
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(
        candidata=c, estrategia="dicionario", parametros={"mapa": {"XX": "TX"}},
        raciocinio="x",
    )
    assert crivar_reparo([r], entrada) == []
    assert c.metricas["reparadas"] == 1
    assert c.metricas["motivo_reparo"] == "perde_par_do_guia"


def test_crivar_reparo_reprova_quem_deixa_o_par_intacto(sujo):
    # Acerta a linha 9 e nao toca a 4, que e o par: nao alterar e continuar errado.
    entrada = monta_entrada(sujo, pares=[(4, "estado", "XX", "MA")])
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(
        candidata=c, estrategia="dicionario", parametros={"mapa": {"YY": "MA"}},
        raciocinio="x",
    )
    assert crivar_reparo([r], entrada) == []
    assert c.metricas["reparadas"] == 1
    assert c.metricas["motivo_reparo"] == "perde_par_do_guia"


def test_crivar_reparo_ignora_par_de_outra_coluna(sujo):
    # O par de cidade cai numa linha marcada em estado e o limpo dele nunca sai do reparo.
    entrada = monta_entrada(sujo, pares=[(4, "cidade", "Bostom", "Outra")])
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    r = Reparo(
        candidata=c, estrategia="dicionario",
        parametros={"mapa": {"XX": "MA", "YY": "MA"}}, raciocinio="x",
    )
    assert crivar_deteccao([c], entrada) == [c]
    assert crivar_reparo([r], entrada) == [r]
    assert c.metricas["motivo_reparo"] == "aprovada"


def test_crivar_reparo_reprova_estrategia_que_lanca(sujo):
    entrada = monta_entrada(sujo)
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(
        candidata=c, estrategia="normalizar", parametros={"funcao": "explode"},
        raciocinio="x",
    )
    def explode(valor):
        raise ValueError("falha de proposito")
    assert crivar_reparo([r], entrada, {"explode": explode}) == []
    assert c.metricas["motivo_reparo"] == "lancou"


def test_crivar_reparo_nao_responde_por_determinante_que_nao_escreveu(sujo):
    # O par esta em cidade, na linha 4 marcada em estado; o reparo conserta so estado.
    entrada = monta_entrada(sujo, pares=[(4, "cidade", "Boston", "Bostonia")])
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(
        candidata=c, estrategia="moda_condicionada",
        parametros={"determinantes": ["cidade"]}, raciocinio="x",
    )
    assert crivar_reparo([r], entrada) == [r]
    assert c.metricas["motivo_reparo"] == "aprovada"


def test_crivar_reparo_responde_por_determinante_que_escreveu_valor_errado():
    # Bostom aparece uma vez e Boston esta a uma edicao: a excecao reescreve a cidade.
    sujo = pd.DataFrame({
        "estado": ["MA", "MA", "MA", "MA", "XX", "MA"],
        "cidade": ["Boston", "Boston", "Boston", "Boston", "Bostom", "Boston"],
    })
    entrada = monta_entrada(sujo, pares=[(4, "cidade", "Bostom", "Outra")])
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(
        candidata=c, estrategia="moda_condicionada",
        parametros={"determinantes": ["cidade"]}, raciocinio="x",
    )
    assert crivar_reparo([r], entrada) == []
    assert c.metricas["motivo_reparo"] == "perde_par_do_guia"


def _reparo_por_mapa(sujo, mapa, **guia):
    entrada = monta_entrada(sujo, linhas_guia=(4,), **guia)
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(candidata=c, estrategia="dicionario", parametros={"mapa": mapa}, raciocinio="x")
    return entrada, c, r


def test_crivar_reparo_reprova_quem_escreve_valor_errado_no_guia(sujo):
    entrada, c, r = _reparo_por_mapa(
        sujo, {"XX": "TX", "YY": "MA"}, corrigidos={(4, "estado"): "MA"}
    )
    assert crivar_reparo([r], entrada) == []
    assert c.metricas["motivo_reparo"] == "corrompe_celula_do_guia"


def test_crivar_reparo_aprova_quem_escreve_valor_certo_no_guia(sujo):
    entrada, c, r = _reparo_por_mapa(
        sujo, {"XX": "MA", "YY": "MA"}, corrigidos={(4, "estado"): "MA"}
    )
    assert crivar_reparo([r], entrada) == [r]
    assert c.metricas["motivo_reparo"] == "aprovada"


def test_crivar_reparo_reprova_quem_deixa_intacta_celula_suja_do_guia(sujo):
    # A linha 4 (XX) esta na mascara e o guia a corrige para MA: continuar XX perde.
    entrada, c, r = _reparo_por_mapa(
        sujo, {"YY": "MA"}, corrigidos={(4, "estado"): "MA"}
    )
    assert crivar_reparo([r], entrada) == []
    assert c.metricas["motivo_reparo"] == "perde_par_do_guia"


def test_crivar_reparo_aprova_celula_suja_do_guia_fora_da_mascara(sujo):
    # A mascara so pega a linha 9 (YY); a 4 (XX) fica fora e intacta.
    entrada = monta_entrada(sujo, linhas_guia=(4,), corrigidos={(4, "estado"): "MA"})
    c = candidata("dominio", {"valores": ["MA", "TX", "XX"]})
    crivar_deteccao([c], entrada)
    r = Reparo(candidata=c, estrategia="dicionario", parametros={"mapa": {"YY": "MA"}},
               raciocinio="x")
    assert crivar_reparo([r], entrada) == [r]
    assert c.metricas["motivo_reparo"] == "aprovada"


def test_crivar_reparo_reprova_quem_escreve_em_celula_certa_do_guia(sujo):
    # A linha 0 esta certa (MA) no guia e o reparo a reescreve com outro valor.
    entrada = monta_entrada(sujo, linhas_guia=(0,))
    novo = entrada.sujo.copy()
    novo.at[0, "estado"] = "TX"
    reparada = pd.Series(False, index=novo.index)
    reparada.loc[4] = True
    c = candidata("dominio", {"valores": ["MA", "TX"]})
    r = Reparo(candidata=c, estrategia="dicionario", parametros={}, raciocinio="x")
    mascara = pd.Series(False, index=novo.index)
    assert _reprovar_reparo(entrada, novo, reparada, r, mascara) == "corrompe_celula_do_guia"


def guia_de_taxa(sujas_no_guia, n_guia, sujas_fora, n=100):
    """Coluna `v` com `ok` ou `X`: o guia tem as n_guia primeiras linhas, `sujas_no_guia` delas sujas."""
    valores = ["ok"] * n
    for i in list(range(sujas_no_guia)) + list(range(n_guia, n_guia + sujas_fora)):
        valores[i] = "X"
    sujo = pd.DataFrame({"v": valores})
    corrigidos = {(i, "v"): "ok" for i in range(sujas_no_guia)}
    return monta_entrada(sujo, linhas_guia=range(n_guia), corrigidos=corrigidos)


def regra_ok():
    return candidata("dominio", {"valores": ["ok"]}, coluna="v")


def test_teto_sobe_quando_o_guia_esta_todo_sujo():
    entrada = guia_de_taxa(20, 20, 78)
    c = regra_ok()
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["taxa"] == 0.98
    assert c.metricas["teto"] == pytest.approx(1.0 + 2 * (0.25 / 20) ** 0.5)


def test_guia_quase_limpo_mantem_o_teto_e_reprova_quem_marca_demais():
    entrada = guia_de_taxa(0, 20, 80)
    c = regra_ok()
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["teto"] == config.TETO_MARCACAO
    assert c.metricas["motivo"] == "marca_demais"


def test_guia_vazio_da_exatamente_o_a_priori(sujo):
    assert teto_da_coluna(monta_entrada(sujo), "estado") == config.TETO_MARCACAO


def test_guia_sem_a_coluna_da_o_a_priori(sujo):
    entrada = monta_entrada(sujo, linhas_guia=(0, 1))
    entrada.guia_linhas = entrada.guia_linhas[["cidade"]]
    assert teto_da_coluna(entrada, "estado") == config.TETO_MARCACAO


def test_guia_sem_sujeira_nao_aperta_o_teto_abaixo_do_a_priori():
    # A margem sozinha (0,22) fica abaixo do a priori: marcar 25% tem de passar.
    entrada = guia_de_taxa(0, 20, 25)
    c = regra_ok()
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["teto"] == config.TETO_MARCACAO


def test_a_margem_alarga_o_teto_acima_da_taxa_do_guia():
    # Guia com 25% sujo: teto 0,47, e a regra marca 40%.
    entrada = guia_de_taxa(5, 20, 35)
    c = regra_ok()
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["taxa"] == 0.40


def test_a_margem_diminui_quando_o_guia_cresce():
    pequeno = teto_da_coluna(guia_de_taxa(5, 20, 0), "v")
    grande = teto_da_coluna(guia_de_taxa(10, 40, 0), "v")
    assert grande < pequeno


def sujo_com_certificado():
    sujo = pd.DataFrame({
        "estado": ["MAA", "MA", "TX", "TX", "XX", "MA", "TX", "MA", "MA", "YY"],
        "cidade": ["Boston"] * 10,
    })
    return monta_entrada(sujo, linhas_guia=(0,), corrigidos={(0, "estado"): "MA"})


def test_veta_regra_de_valor_que_marca_valor_certificado():
    entrada = sujo_com_certificado()
    # Marca os MA das linhas 1, 5, 7 e 8; o guia certificou MA.
    c = candidata("dominio", {"valores": ["MAA", "TX", "XX", "YY"]})
    assert crivar_deteccao([c], entrada) == []
    assert c.metricas["motivo"] == "marca_valor_certificado"


def test_aprova_regra_de_valor_que_marca_so_valor_nao_certificado():
    entrada = sujo_com_certificado()
    c = candidata("dominio", {"valores": ["MAA", "MA", "TX"]})
    assert crivar_deteccao([c], entrada) == [c]


def test_veto_compara_valor_inteiro_e_nao_substring():
    entrada = sujo_com_certificado()
    entrada.sujo.at[4, "estado"] = "MAX"
    c = candidata("dominio", {"valores": ["MAA", "MA", "TX", "YY"]})
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["marcadas"] == 1


def test_dependencia_pode_marcar_valor_certificado():
    # Linha 5 (Boston, TX) diverge da moda MA e TX esta certificado pela linha 6 do guia.
    sujo = pd.DataFrame({
        "estado": ["MA"] * 5 + ["TX", "TX"],
        "cidade": ["Boston"] * 6 + ["Denver"],
    })
    entrada = monta_entrada(sujo, linhas_guia=(6,))
    entrada.perfil.pares[("cidade", "estado")] = {
        "det": 0.9, "n_grupos": 2, "n_divergentes": 1, "frac_ambiguos": 0.0
    }
    c = candidata("dependencia", {"determinantes": ["cidade"]})
    assert crivar_deteccao([c], entrada) == [c]
    assert c.metricas["marcadas"] == 1


def test_sem_guia_nenhum_valor_e_certificado(sujo):
    mascara = pd.Series(True, index=sujo.index)
    assert not _marca_valor_certificado(monta_entrada(sujo), "estado", mascara)


def coluna_xy(n_x, n_y):
    """Coluna `v` com n_x celulas X, n_y celulas Y e o resto ok, sem guia."""
    valores = ["X"] * n_x + ["Y"] * n_y + ["ok"] * (100 - n_x - n_y)
    return monta_entrada(pd.DataFrame({"v": valores}))


def par_de_tipos():
    marca_x = candidata("dominio", {"valores": ["ok", "Y"]}, coluna="v")
    marca_y = candidata("formato", {"regex": "ok|X"}, coluna="v")
    return marca_x, marca_y


def test_uniao_acima_do_teto_descarta_o_tipo_de_maior_taxa():
    marca_x, marca_y = par_de_tipos()
    entrada = coluna_xy(20, 15)
    assert crivar_deteccao([marca_x, marca_y], entrada) == [marca_y]
    assert marca_x.metricas["motivo"] == "uniao_acima_do_teto"
    assert marca_x.metricas["taxa_uniao"] == 0.35
    assert marca_y.metricas["motivo"] == "aprovada"


def test_uniao_que_cabe_no_teto_mantem_os_dois_tipos():
    marca_x, marca_y = par_de_tipos()
    assert crivar_deteccao([marca_x, marca_y], coluna_xy(10, 15)) == [marca_x, marca_y]


def test_empate_de_taxa_nao_depende_da_ordem_da_lista():
    marca_x, marca_y = par_de_tipos()
    entrada = coluna_xy(16, 16)
    # Empate: dominio vem antes de formato em ordem alfabetica e cai primeiro.
    assert crivar_deteccao([marca_x, marca_y], entrada) == [marca_y]
    marca_x, marca_y = par_de_tipos()
    assert crivar_deteccao([marca_y, marca_x], entrada) == [marca_y]

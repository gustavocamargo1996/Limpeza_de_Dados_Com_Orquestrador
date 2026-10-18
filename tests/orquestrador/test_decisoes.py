"""As decisoes do usuario: o que pode ser decidido, a recusa do que contradiz o guia e o acumulo."""
import pytest

from orquestrador import decisoes
from orquestrador.relatorio_geracao import CONTRADIZ


def cand(motivo, reparo=None, tipo="dominio", parametros=None):
    metricas = {"motivo_reparo": reparo} if reparo else {}
    return {"tipo": tipo, "motivo": motivo, "parametros": parametros or {"valores": ["A"]},
            "metricas": metricas}


@pytest.mark.parametrize("motivo", sorted(CONTRADIZ - {"contradiz_o_guia", "valor_certificado"}))
def test_o_que_contradiz_o_guia_nao_tem_opcao_e_e_recusado(motivo):
    assert decisoes.opcoes(cand(motivo)) == []
    with pytest.raises(ValueError, match="contradiz o guia"):
        decisoes.decidir(cand(motivo), "c", "aprovar", None, "v1")


def test_reparo_que_contradiz_o_guia_so_pode_ser_rejeitado():
    c = cand("aprovada", "corrompe_celula_do_guia")
    assert decisoes.opcoes(c) == ["rejeitar"]
    with pytest.raises(ValueError):
        decisoes.decidir(c, "c", "tentar", "faca assim", "v1")


@pytest.mark.parametrize("motivo", ["vacua", "lancou", "sem_perfil"])
def test_regra_sem_efeito_nao_tem_opcao(motivo):
    assert decisoes.opcoes(cand(motivo)) == []


def test_opcoes_de_cada_situacao():
    assert decisoes.opcoes(cand("aprovada", "aprovada")) == ["rejeitar"]
    assert decisoes.opcoes(cand("aprovada", "nao_repara")) == ["rejeitar"]
    assert decisoes.opcoes(cand("aprovada", "codigo_rejeitado")) == ["rejeitar", "tentar"]
    assert decisoes.opcoes(cand("marca_demais")) == ["aprovar"]
    assert decisoes.opcoes(cand("superada")) == ["aprovar"]
    assert decisoes.opcoes(cand("ambigua")) == ["aprovar"]
    assert decisoes.opcoes(cand("rejeitada_pelo_usuario")) == ["desfazer"]


def test_decidir_monta_a_entrada_do_decisoes_json():
    d = decisoes.decidir(cand("marca_demais"), "ibu", "aprovar", "  ", "v1")
    assert d == {"coluna": "ibu", "tipo": "dominio", "parametros": {"valores": ["A"]},
                 "decisao": "aprovar", "instrucao": None, "origem": "usuario", "versao": "v1"}
    t = decisoes.decidir(cand("aprovada", "codigo_rejeitado"), "ibu", "tentar", "use int", "v1")
    assert (t["decisao"], t["instrucao"]) == ("aprovar", "use int")
    with pytest.raises(ValueError, match="instrucao"):
        decisoes.decidir(cand("aprovada", "codigo_rejeitado"), "ibu", "tentar", "", "v1")
    assert decisoes.decidir_residual("city", "Bostn", "v1") == {
        "coluna": "city", "tipo": "residual", "parametros": {"sujo": "Bostn"},
        "decisao": "rejeitar", "instrucao": None, "origem": "usuario", "versao": "v1"}


def test_acumular_herda_regras_e_a_escolha_nova_vence():
    regras = [{"coluna": "ibu", "tipo": "faixa", "deteccao": {"minimo": 0, "maximo": 9}},
              {"coluna": "abv", "tipo": "dominio", "deteccao": {"valores": ["A"]}}]
    anteriores = [decisoes.decidir_residual("city", "x", "v0")]
    nova = decisoes.decidir(cand("aprovada", tipo="faixa", parametros={"minimo": 0, "maximo": 9}),
                            "ibu", "rejeitar", None, "v1")
    juntas = decisoes.acumular(anteriores, [nova], regras=regras, versao="v1")
    por_coluna = {d["coluna"]: d for d in juntas}
    assert len(juntas) == 3
    assert por_coluna["ibu"]["decisao"] == "rejeitar" and por_coluna["ibu"]["origem"] == "usuario"
    assert por_coluna["abv"] == {"coluna": "abv", "tipo": "dominio", "parametros": {"valores": ["A"]},
                                 "decisao": "aprovar", "instrucao": None, "origem": "herdada",
                                 "versao": "v1"}


def test_desfazer_tira_a_decisao():
    rejeitada = decisoes.decidir(cand("aprovada"), "abv", "rejeitar", None, "v1")
    desfeita = decisoes.decidir(cand("rejeitada_pelo_usuario"), "abv", "desfazer", None, "v2")
    assert decisoes.acumular([rejeitada], [desfeita]) == []


def test_gravar_e_ler(tmp_path):
    d = [decisoes.decidir_residual("city", "São", "v1")]
    decisoes.gravar(tmp_path, d)
    assert decisoes.ler(tmp_path) == d
    assert decisoes.ler(tmp_path / "nada") == []


def test_heranca_nao_apaga_a_instrucao_que_o_usuario_deu_antes():
    regra = {"coluna": "ibu", "tipo": "faixa", "deteccao": {"minimo": 0, "maximo": 9}}
    anterior = decisoes.decidir(cand("aprovada", "codigo_rejeitado", tipo="faixa",
                                     parametros={"minimo": 0, "maximo": 9}),
                                "ibu", "tentar", "use int", "v0")
    [junta] = decisoes.acumular([anterior], [], regras=[regra], versao="v1")
    assert (junta["instrucao"], junta["origem"], junta["versao"]) == ("use int", "usuario", "v0")

"""O fluxo ponta a ponta, offline: esquema novo, aperfeicoamento, aprovacao e esquema conhecido.

Os testes `test_1` a `test_4` compartilham o processo do MVP e rodam nesta ordem: cada um parte
de onde o anterior parou. Nenhum gasta API: o filho do gerador roda com PROVEDOR=gravado e,
no aperfeicoamento, com uma API viva apontada para uma porta fechada desta maquina.
"""
import importlib.util
import time
from pathlib import Path

import pandas as pd
import pytest
from moto import mock_aws

from orquestrador import amostra, automaticas, config, controle, fluxo, lago

RAIZ = Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "tests" / "fixtures"
SUJO = FIXTURES / "beers_dirty_300.csv"
GUIA_MVP = RAIZ / "dados" / "guia" / "beers"
VERSAO_MVP = "2026-10-12_2152"
MODA_DO_ID = ("brewery_id", "dependencia")


def ler(caminho):
    return pd.read_csv(caminho, **config.LER_CSV)


def esperar(con, processo, limite=600):
    """Chama acompanhar ate a geracao sair das etapas 4 a 6."""
    fim = time.time() + limite
    while time.time() < fim:
        etapa = fluxo.acompanhar(con, processo)
        atual = controle.etapa_atual(con, processo)
        if etapa not in (4, 5, 6) or atual["STATUS"] != controle.ANDAMENTO:
            return etapa
        time.sleep(0.5)
    raise TimeoutError("a geracao nao terminou")


def importar(caminho):
    spec = importlib.util.spec_from_file_location(f"limpador_{time.time_ns()}", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def mvp(tmp_path_factory):
    """Um processo do MVP levado ate a etapa 9, com o bucket do moto e o banco num tmp."""
    raiz = tmp_path_factory.mktemp("mvp")
    with pytest.MonkeyPatch.context() as mp, mock_aws():
        mp.setenv("MOTO_S3_CUSTOM_ENDPOINTS", config.S3_ENDPOINT)
        mp.setenv("PROVEDOR", "gravado")
        mp.setenv("RESPOSTAS_GRAVADAS", str(FIXTURES / "respostas_beers_poc2.jsonl"))
        mp.setenv("MODELO", "gpt-6-luna")
        mp.setattr(config, "TRABALHO", raiz / "trabalho")
        relogio = {"agora": VERSAO_MVP}
        mp.setattr(automaticas, "carimbo", lambda: relogio["agora"])
        guia = ler(GUIA_MVP / "guia_linhas.csv")
        linhas = [int(v) for v in guia["_linha"]]
        mp.setattr(amostra, "sortear", lambda n_total, n, semente: {
            "semente": semente, "n_total": n_total, "linhas": linhas, "trocas": []})
        lago.disponivel()
        con = controle.conectar(raiz / "controle.sqlite")
        processo = fluxo.iniciar(con, SUJO.read_bytes(), "beers.csv", "Outros")
        estado = {"con": con, "processo": processo, "relogio": relogio, "mp": mp,
                  "etapa_ao_nomear": controle.etapa_atual(con, processo)["DETALHE"]}
        fluxo.nomear(con, processo, "beers")
        fluxo.confirmar_guia(con, processo, guia, ler(GUIA_MVP / "guia_pares.csv"))
        fluxo.gerar(con, processo, "inteira", 300)
        estado["etapa"] = esperar(con, processo)
        yield estado


def test_1_esquema_novo_gera_o_limpador_do_mvp_byte_a_byte(mvp, tmp_path):
    con, processo = mvp["con"], mvp["processo"]
    assert mvp["etapa_ao_nomear"] == automaticas.ESPERA_NOME
    assert mvp["etapa"] == 9, controle.etapa_atual(con, processo)["DETALHE"]
    prefixo = f"Outros/beers/Limpador/{VERSAO_MVP}"
    baixado = lago.baixar_pasta(prefixo, tmp_path / "v1")
    gerado = (baixado / f"limpador_beers_{VERSAO_MVP}.py").read_bytes().replace(b"\r\n", b"\n")
    assert gerado == (FIXTURES / "limpador_beers_poc2.py").read_bytes().replace(b"\r\n", b"\n")
    assert {"raciocinio_beers_2026-10-12_2152.md", "respostas.jsonl", "decisoes.json",
            "parametros.json", "relatorio_geracao.md"} <= {p.name for p in baixado.iterdir()}
    assert "31 chamadas (31 novas)" in (baixado / "relatorio_geracao.md").read_text(encoding="utf-8")
    assert lago.metadados(f"Outros/beers/Original/{VERSAO_MVP}/dados.csv")["sha256"]
    assert lago.subpastas("Outros/beers/Amostra_Guia") == [VERSAO_MVP]
    etapas = controle.etapas(con, processo)
    assert [e["ID_ETAPA"] for e in etapas] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert all(e["STATUS"] == controle.SUCESSO for e in etapas[:-1])
    ctx = controle.contexto(con, processo)
    assert controle.obter_limpador(con, ctx["id_limpador"])["STATUS_APROVACAO"] == "pendente"


def test_1b_relatorio_de_limpeza_bate_com_o_limpador(mvp):
    ctx = controle.contexto(mvp["con"], mvp["processo"])
    limpador = importar(FIXTURES / "limpador_beers_poc2.py")
    _, _, fontes = limpador.aplicar_detalhado(ler(SUJO))
    texto = (Path(ctx["corrigido"]) / "relatorio_limpeza.md").read_text(encoding="utf-8")
    assert f"- células alteradas: {int((fontes != '').sum().sum())}," in texto
    assert ler(Path(ctx["corrigido"]) / "dados.csv").shape == ler(SUJO).shape


def test_2_aperfeicoar_rejeitando_a_moda_do_id_sem_chamada_nova(mvp, tmp_path):
    con, processo, mp = mvp["con"], mvp["processo"], mvp["mp"]
    # Porta fechada: se o ciclo chamasse a API viva, nada sairia da maquina e o teste veria.
    mp.setenv("PROVEDOR_VIVO", "openai")
    mp.setenv("OPENAI_API_KEY", "sk-teste-sem-valor")
    mp.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9/v1")
    mvp["relogio"]["agora"] = "2026-10-12_2300"
    anterior = controle.contexto(con, processo)["id_limpador"]
    regra = {"coluna": "brewery_id", "tipo": "dependencia", "motivo": "aprovada",
             "parametros": {"determinantes": ["brewery-name"]}, "metricas": {"motivo_reparo": "aprovada"}}
    from orquestrador import decisoes
    fluxo.aperfeicoar(con, processo, [decisoes.decidir(regra, "brewery_id", "rejeitar", None, "v1")])
    assert esperar(con, processo) == 9, controle.etapa_atual(con, processo)["DETALHE"]
    ctx = controle.contexto(con, processo)
    assert controle.obter_limpador(con, anterior)["STATUS_APROVACAO"] == "reprovado"
    novo = controle.obter_limpador(con, ctx["id_limpador"])
    assert (novo["STATUS_APROVACAO"], novo["ID_LIMPADOR_ORIGEM"]) == ("pendente", anterior)
    baixado = lago.baixar_pasta(novo["DIRETORIO_BUCKET"], tmp_path / "v2")
    regras = importar(baixado / "limpador_beers_2026-10-12_2300.py").REGRAS
    assert MODA_DO_ID not in [(r["coluna"], r["tipo"]) for r in regras] and len(regras) == 10
    # 30, e nao 31: o especificador da regra rejeitada nao e mais chamado.
    assert "30 chamadas (0 novas)" in (baixado / "relatorio_geracao.md").read_text(encoding="utf-8")
    assert '"rejeitar"' in (baixado / "decisoes.json").read_text(encoding="utf-8")


def test_3_aprovar_grava_o_corrigido_e_encerra(mvp):
    con, processo = mvp["con"], mvp["processo"]
    mvp["relogio"]["agora"] = "2026-10-13_0800"
    fluxo.aprovar(con, processo)
    ctx = controle.contexto(con, processo)
    corrigido = "Outros/beers/Corrigido/2026-10-13_0800"
    assert lago.listar(corrigido) == [f"{corrigido}/{n}" for n in ("dados.csv", "flags.csv", "relatorio_limpeza.md")]
    assert controle.obter_limpador(con, ctx["id_limpador"])["STATUS_APROVACAO"] == "aprovado"
    dado = controle.dado_existente(con, "Outros", "beers", ctx["hash"])
    assert (dado["DIRETORIO_CORRIGIDO"], dado["LIMPADOR_UTILIZADO"]) == (corrigido, "beers_2026-10-12_2300")
    assert controle.processo_aberto(con) is None
    assert controle.etapa_atual(con, processo)["ID_ETAPA"] == 10


def test_4_esquema_conhecido_aplica_o_limpador_aprovado_sem_gerar(mvp):
    con = mvp["con"]
    mvp["relogio"]["agora"] = "2026-10-14_0800"
    processo = fluxo.iniciar(con, SUJO.read_bytes(), "beers_de_novo.csv", "Outros")
    ctx = controle.contexto(con, processo)
    assert ctx["conhecido"] and ctx["repetido"] and ctx["versao"] == "beers_2026-10-12_2300"
    assert [e["ID_ETAPA"] for e in controle.etapas(con, processo)] == [1, 2, 8, 9]
    assert not ctx["gerou"]
    assert lago.subpastas("Outros/beers/Original") == [VERSAO_MVP]
    mvp["conhecido"] = processo


def test_4b_nova_versao_usa_o_guia_antigo_renumerado_e_herda_as_regras(mvp):
    con, processo, mp = mvp["con"], mvp["conhecido"], mvp["mp"]
    mvp["relogio"]["agora"] = "2026-10-14_0900"
    mp.setattr(fluxo.geracao, "disparar", lambda *a, **k: type("P", (), {"pid": 999999})())
    fluxo.nova_versao(con, processo, "inteira", 300)
    ctx = controle.contexto(con, processo)
    entrada = Path(ctx["pasta_versao"]) / "entrada"
    sujas = amostra.linhas_sujas(Path(ctx["pasta_versao"]) / "guia_lago")
    sujo = ler(entrada / "sujo.csv")
    assert len(sujo) == len(sujas) + 300 and not ctx["guia_deste_processo"]
    guia = ler(entrada / "guia" / "guia_linhas.csv")
    assert guia["_linha"].astype(int).max() < len(sujas)
    for posicao, velho in zip(guia["_linha"].astype(int), ler(GUIA_MVP / "guia_linhas.csv")["_linha"].astype(int)):
        assert sujo.loc[posicao].equals(ler(SUJO).loc[velho])
    herdadas = [d for d in ctx["geracao"]["decisoes"] if d["origem"] == "herdada"]
    assert len(herdadas) == 10 and ctx["geracao"]["reaproveitar"] is None
    assert any(d["decisao"] == "rejeitar" for d in ctx["geracao"]["decisoes"])
    fluxo.cancelar(con, processo)


# --- Casos de erro, cada um no seu banco e no seu bucket ---------------------------------

@pytest.fixture
def ingerido(con, lago_falso, monkeypatch):
    """Um processo com o guia do MVP confirmado, esperando os parametros da geracao."""
    lago.disponivel()
    guia = ler(GUIA_MVP / "guia_linhas.csv")
    linhas = [int(v) for v in guia["_linha"]]
    monkeypatch.setattr(amostra, "sortear", lambda n_total, n, semente: {
        "semente": semente, "n_total": n_total, "linhas": linhas, "trocas": []})
    processo = fluxo.iniciar(con, SUJO.read_bytes(), "beers.csv", "Outros")
    fluxo.nomear(con, processo, "beers")
    fluxo.confirmar_guia(con, processo, guia, ler(GUIA_MVP / "guia_pares.csv"))
    assert controle.etapa_atual(con, processo)["DETALHE"] == automaticas.ESPERA_PARAMETROS
    return processo


def test_filho_que_falha_deixa_a_etapa_em_erro_e_o_log_no_lago(con, ingerido, tmp_path, monkeypatch):
    (tmp_path / "vazio.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("PROVEDOR", "gravado")
    monkeypatch.setenv("RESPOSTAS_GRAVADAS", str(tmp_path / "vazio.jsonl"))
    fluxo.gerar(con, ingerido, "inteira", 300)
    esperar(con, ingerido)
    atual = controle.etapa_atual(con, ingerido)
    assert atual["STATUS"] == controle.ERRO and "resposta nao gravada" in atual["DETALHE"]
    ctx = controle.contexto(con, ingerido)
    chave = f"Outros/beers/Limpador/{ctx['versao_em']}/erro.log"
    assert chave in lago.listar("Outros/beers/Limpador/")


def test_pid_morto_sem_limpador_vira_interrompido(con, ingerido, monkeypatch):
    monkeypatch.setattr(fluxo.geracao, "disparar", lambda *a, **k: type("P", (), {"pid": 999999})())
    fluxo.gerar(con, ingerido, "inteira", 300)
    assert fluxo.acompanhar(con, ingerido) == 4
    atual = controle.etapa_atual(con, ingerido)
    assert atual["STATUS"] == controle.ERRO and atual["DETALHE"].startswith("interrompido")


def test_versao_truncada_nao_pode_ser_aprovada(con, ingerido):
    controle.atualizar_contexto(con, ingerido, truncada=True)
    with pytest.raises(ValueError, match="truncada"):
        fluxo.aprovar(con, ingerido)


def test_nome_repetido_no_dominio_e_recusado(con, ingerido):
    outro = fluxo.iniciar(con, b"a,b\n1,2\n", "x.csv", "Outros")
    with pytest.raises(ValueError, match="ja existe"):
        fluxo.nomear(con, outro, "beers")
    with pytest.raises(ValueError, match="letra"):
        fluxo.nomear(con, outro, "  /  ")


@pytest.mark.parametrize("conteudo, motivo", [
    (b"a,a\n1,2\n", "repetidos"), (b"_x,b\n1,2\n", "_linha"), (b"a,b\n", "linhas"),
    (b"\xff\xfe\x00a", "UTF-8"),
])
def test_dataset_recusado_na_ingestao(con, conteudo, motivo):
    with pytest.raises(ValueError, match=motivo):
        fluxo.iniciar(con, conteudo, "x.csv", "Outros")
    assert controle.processo_aberto(con) is None

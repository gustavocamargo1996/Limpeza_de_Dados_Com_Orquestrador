"""Fumaca das telas com o AppTest do Streamlit: cada estado do processo cai na tela certa."""
import shutil
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from orquestrador import amostra, config, controle, fluxo, geracao, lago

RAIZ = Path(__file__).resolve().parents[2]
APP = str(RAIZ / "orquestrador" / "app.py")
FIXTURES = RAIZ / "tests" / "fixtures"
SUJO = FIXTURES / "beers_dirty_300.csv"
GUIA_MVP = RAIZ / "dados" / "guia" / "beers"
RACIOCINIO_MVP = (RAIZ / "docs" / "evidencia" / "parte-2" / "run-beers_2026-10-12_2152"
                  / "raciocinio_beers_2026-10-12_2152.md")


def rodar():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    assert not app.exception, app.exception
    return app


def textos(app):
    return " ".join(str(e.value) for e in [*app.header, *app.markdown, *app.error, *app.info])


@pytest.fixture
def no_guia(con, lago_falso, monkeypatch):
    """Um processo de esquema novo parado na etapa 3, com o sorteio do guia do MVP."""
    lago.disponivel()
    guia = pd.read_csv(GUIA_MVP / "guia_linhas.csv", **config.LER_CSV)
    linhas = [int(v) for v in guia["_linha"]]
    monkeypatch.setattr(amostra, "sortear", lambda n_total, n, semente: {
        "semente": semente, "n_total": n_total, "linhas": linhas, "trocas": []})
    processo = fluxo.iniciar(con, SUJO.read_bytes(), "beers.csv", "Outros")
    fluxo.nomear(con, processo, "beers")
    return processo, guia


def test_sem_processo_mostra_a_ingestao(lago_falso):
    app = rodar()
    assert app.header[0].value == "Ingestão do dataset"
    assert [b.label for b in app.button] == ["Ingerir"]


def test_bucket_fora_do_ar_bloqueia(monkeypatch):
    monkeypatch.setattr(lago, "disponivel", lambda: False)
    app = rodar()
    assert "Bucket indisponível" in app.error[0].value
    assert not app.header


def test_esquema_novo_pede_o_nome(con, lago_falso):
    lago.disponivel()
    fluxo.iniciar(con, b"a,b\n1,2\n", "x.csv", "Outros")
    app = rodar()
    assert app.header[0].value == "Esquema novo" and "`a` `b`" in textos(app)


def test_etapa_3_mostra_o_formulario_do_guia(no_guia):
    app = rodar()
    assert "Amostra-guia" in textos(app)
    assert {"Sortear de novo", "Confirmar guia"} <= {b.label for b in app.button}
    assert [t.label for t in app.tabs] == ["Formulário", "Template"]


def test_guia_confirmado_mostra_os_parametros_e_o_aviso_do_provedor(con, no_guia, monkeypatch):
    processo, guia = no_guia
    monkeypatch.setattr(config, "PROVEDOR", "openai")
    fluxo.confirmar_guia(con, processo, guia, pd.read_csv(GUIA_MVP / "guia_pares.csv", **config.LER_CSV))
    app = rodar()
    assert "Parâmetros da geração" in textos(app)
    assert any("API da OpenAI" in w.value for w in app.warning)
    assert "Iniciar geração" in {b.label for b in app.button}


def test_geracao_que_falhou_mostra_o_erro_e_tentar_de_novo(con, no_guia, monkeypatch):
    processo, guia = no_guia
    fluxo.confirmar_guia(con, processo, guia, pd.read_csv(GUIA_MVP / "guia_pares.csv", **config.LER_CSV))
    monkeypatch.setattr(geracao, "disparar", lambda *a, **k: type("P", (), {"pid": 999999})())
    fluxo.gerar(con, processo, "inteira", 300)
    fluxo.acompanhar(con, processo)
    app = rodar()
    assert app.error and "Tentar de novo" in {b.label for b in app.button}


def test_etapa_9_mostra_os_relatorios_e_a_decisao(con, no_guia, monkeypatch):
    processo, guia = no_guia
    fluxo.confirmar_guia(con, processo, guia, pd.read_csv(GUIA_MVP / "guia_pares.csv", **config.LER_CSV))
    monkeypatch.setattr(geracao, "disparar", lambda *a, **k: type("P", (), {"pid": 999999})())
    fluxo.gerar(con, processo, "inteira", 300)
    # O filho de mentira "terminou": deixa os arquivos que o gerador deixaria.
    ctx = controle.contexto(con, processo)
    destino, versao = Path(ctx["destino"]), ctx["versao"]
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "limpador_beers_poc2.py", destino / f"limpador_{versao}.py")
    shutil.copy(RACIOCINIO_MVP, destino / f"raciocinio_{versao}.md")
    shutil.copy(FIXTURES / "respostas_beers_poc2.jsonl", destino / "respostas.jsonl")
    geracao.log(destino).write_text(f"limpador: {destino}\n", encoding="utf-8")
    assert fluxo.acompanhar(con, processo) == 9
    app = rodar()
    assert [t.label for t in app.tabs] == ["Relatório de geração", "Relatório de limpeza", "Decisão"]
    assert "Aprovar e gravar o dataset corrigido" in {b.label for b in app.button}
    assert any("Relatório de limpeza" in m.value for m in app.markdown)
    assert app.expander and app.selectbox

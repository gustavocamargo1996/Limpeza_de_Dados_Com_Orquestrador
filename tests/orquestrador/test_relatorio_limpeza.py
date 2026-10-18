"""O relatorio de limpeza: o limpador roda em subprocesso, e o resumo bate com o que ele faz."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from orquestrador import config
from orquestrador import relatorio_limpeza as rl

RAIZ = Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "tests" / "fixtures"
LIMPADOR = FIXTURES / "limpador_beers_poc2.py"
SUJO = FIXTURES / "beers_dirty_300.csv"


def direto():
    """O que o limpador faz, rodado neste processo: a referencia do teste."""
    spec = importlib.util.spec_from_file_location("limpador_direto", LIMPADOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo, modulo.aplicar_detalhado(pd.read_csv(SUJO, **config.LER_CSV))


@pytest.fixture(scope="module")
def aplicacao(tmp_path_factory):
    return rl.aplicar(LIMPADOR, SUJO, tmp_path_factory.mktemp("corrigido"))


def test_o_filho_devolve_o_que_o_limpador_faz(aplicacao):
    modulo, (corrigido, flags, fontes) = direto()
    assert aplicacao["corrigido"].equals(corrigido)
    assert aplicacao["fontes"].equals(fontes)
    assert (aplicacao["flags"].values == flags.values).all()
    assert aplicacao["regras"] == [dict(r) for r in modulo.REGRAS]
    assert aplicacao["residual"] == modulo.RESIDUAL and aplicacao["truncada"] is False


def test_resumo_conta_por_regra_o_que_as_fontes_dizem(aplicacao):
    modulo, (corrigido, flags, fontes) = direto()
    resumo = rl.resumir(aplicacao)
    assert [r["id"] for r in resumo["regras"]] == [f"R{i}" for i in range(1, len(modulo.REGRAS) + 1)]
    for regra in resumo["regras"]:
        fonte = f"{regra['tipo']}/{regra['estrategia']}" if regra["estrategia"] else None
        assert regra["alteradas"] == int((fontes[regra["coluna"]] == fonte).sum())
        assert len(regra["amostra"]) <= config.CELULAS_POR_REGRA
        assert all(antes != depois for _, antes, depois in regra["amostra"])
    assert resumo["residual"] == {c: int((fontes[c] == "residual").sum())
                                  for c in fontes if (fontes[c] == "residual").any()}
    assert resumo["flags"] == {c: int(n) for c, n in flags.sum().items() if n}
    assert resumo["celulas"] == int((fontes != "").sum().sum())
    assert resumo["linhas"] == int((fontes != "").any(axis=1).sum())
    ounces = next(r for r in resumo["regras"] if r["coluna"] == "ounces" and r["tipo"] == "conformidade")
    assert ounces["alteradas"] > 0


def test_montar_lista_as_regras_e_a_amostra(aplicacao):
    texto = rl.montar(rl.resumir(aplicacao), "beers_v1")
    assert texto.startswith("# Relatório de limpeza: beers_v1")
    assert "R1" in texto and "| antes | depois |" in texto and "residual" in texto


def test_limpador_que_lanca_vira_runtime_error(tmp_path):
    ruim = tmp_path / "limpador_ruim.py"
    ruim.write_text("def aplicar_detalhado(df):\n    raise KeyError('coluna_x')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="coluna_x"):
        rl.aplicar(ruim, SUJO, tmp_path / "saida")

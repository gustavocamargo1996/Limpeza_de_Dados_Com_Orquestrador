"""A espinha de ponta a ponta, com o duble no lugar do LLM."""
from pathlib import Path

from limpeza2 import config, e2_detector, e4_especificador, e5_residual, e6_codificador, provedor
from limpeza2.espinha import gerar_limpador
from medir import avaliar, linhas_do_guia

RAIZ = Path(__file__).resolve().parent.parent
SUJO = RAIZ / "tests" / "fixtures" / "beers_dirty_300.csv"
LIMPO = RAIZ / "tests" / "fixtures" / "beers_clean_300.csv"
GUIA = RAIZ / "dados" / "guia" / "beers"

CODIGO_ONCA = r'''def corrigir(valor):
    m = re.match(r'\s*(\d+)(\.\d+)?', valor)
    if m is None:
        return valor
    decimal = m.group(2) or ''
    if decimal.strip('0') == '.':
        decimal = ''
    return m.group(1) + decimal'''


def campo(conteudo, nome):
    return next(l.split(": ", 1)[1] for l in conteudo.splitlines() if l.startswith(f"{nome}: "))


def responder_beers(instrucao, conteudo):
    """Um LLM de mentira, deterministico, que conhece so a coluna ounces."""
    if instrucao == e2_detector.INSTRUCAO:
        return {"regras": []}
    if instrucao == e4_especificador.INSTRUCAO:
        estrategia = "normalizar" if campo(conteudo, "coluna") == "ounces" else "esvaziar"
        return {"estrategia": estrategia, "transformacao": "manter so o numero, sem .0",
                "determinantes": None, "distancia": None, "mapa": None,
                "raciocinio": {"padrao": "p", "analise": "a", "acao": "t"}}
    if instrucao == e6_codificador.INSTRUCAO:
        return {"codigo": CODIGO_ONCA}
    if instrucao == e5_residual.INSTRUCAO_SUJEITO:
        return {"coluna": None, "raciocinio": "nenhuma nomeia"}
    if instrucao == e5_residual.INSTRUCAO:
        return {"correcoes": []}
    raise AssertionError("instrucao desconhecida")


def test_gera_limpador_que_o_medir_mede(tmp_path, roteiro):
    roteiro(responder_beers)
    destino = tmp_path / "beers_teste"
    caminho = gerar_limpador(SUJO, GUIA, destino)
    assert caminho == destino / "limpador_beers_teste.py"
    assert (destino / "raciocinio_beers_teste.md").exists()
    assert (destino / "respostas.jsonl").read_text(encoding="utf-8").count("\n") > 0
    fora = linhas_do_guia(GUIA / "guia_linhas.csv", GUIA / "guia_pares.csv")
    r = avaliar(caminho, SUJO, LIMPO, holdout=fora)
    assert r["fontes"].get("conformidade/normalizar", 0) > 0
    assert r["colunas"]["ounces"]["precisao"] == 1.0
    assert r["truncada"] is False


def test_mesma_geracao_mesmo_limpador(tmp_path, roteiro):
    roteiro(responder_beers)
    a = gerar_limpador(SUJO, GUIA, tmp_path / "a" / "beers_teste")
    b = gerar_limpador(SUJO, GUIA, tmp_path / "b" / "beers_teste")
    assert a.read_bytes() == b.read_bytes()


def test_replay_gravado_reproduz_o_limpador_byte_a_byte(tmp_path, roteiro, monkeypatch):
    construir = provedor._construir_api
    roteiro(responder_beers)
    original = gerar_limpador(SUJO, GUIA, tmp_path / "a" / "beers_teste")
    monkeypatch.setattr(provedor, "_construir_api", construir)
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(original.parent / "respostas.jsonl"))
    copia = gerar_limpador(SUJO, GUIA, tmp_path / "b" / "beers_teste")
    assert copia.read_bytes() == original.read_bytes()
    md = "raciocinio_beers_teste.md"
    assert (copia.parent / md).read_bytes() == (original.parent / md).read_bytes()


def test_braco_sem_guia_gera_limpador(tmp_path, roteiro):
    roteiro(responder_beers)
    caminho = gerar_limpador(SUJO, None, tmp_path / "beers_sem_guia")
    assert "sem guia" in caminho.read_text(encoding="utf-8")

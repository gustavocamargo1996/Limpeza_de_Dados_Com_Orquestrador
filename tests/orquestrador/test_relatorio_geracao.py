"""O relatorio de geracao: contrato com o raciocinio do gerador e a traducao para o usuario."""
import re
from collections import Counter
from pathlib import Path

from orquestrador import relatorio_geracao as rg

RAIZ = Path(__file__).resolve().parents[2]
MVP = RAIZ / "docs" / "evidencia" / "parte-2" / "run-beers_2026-10-12_2152" / "raciocinio_beers_2026-10-12_2152.md"


def candidatas(raciocinio):
    return [c for coluna in raciocinio["colunas"].values() for c in coluna["candidatas"]]


def test_contrato_com_o_raciocinio_do_mvp():
    texto = MVP.read_text(encoding="utf-8")
    raciocinio = rg.ler(MVP)
    assert list(raciocinio["colunas"]) == re.findall(r"^## (?!Outras)(.+)$", texto, re.M)
    lidas = candidatas(raciocinio)
    cabecalhos = re.findall(r"^### (?!residual)\w+: (\w+)$", texto, re.M)
    assert Counter(c["motivo"] for c in lidas) == Counter(cabecalhos) == {
        "aprovada": 11, "vacua": 8, "perde_par_do_guia": 3, "marca_celula_correta": 1,
        "superada": 1}
    assert Counter(c["metricas"].get("motivo_reparo") for c in lidas if "motivo_reparo" in c["metricas"]) == {
        "aprovada": 8, "perde_par_do_guia": 2, "nao_repara": 1}
    assert raciocinio["cabecalho"]["modelo"] == "gpt-6-luna (openai), raciocinio none"


def test_campos_de_cada_candidata():
    colunas = rg.ler(MVP)["colunas"]
    [abv] = [c for c in colunas["abv"]["candidatas"] if c["tipo"] == "conformidade"]
    assert abv["parametros"] == {"padroes": ["9.9"]}
    assert abv["metricas"]["marcadas"] == 72 and abv["metricas"]["taxa_uniao"] == 0.24
    assert abv["reparo"] == "normalizar" and abv["raciocinio_reparo"].startswith("Os valores")
    assert "def corrigir" not in str(abv)


def test_residual_mapa_e_caidas():
    colunas = rg.ler(MVP)["colunas"]
    assert colunas["ounces"]["residual"]["mapa"] == [
        ("8.4 ounce", "8.4", "O exemplo do guia indica remover a unidade e manter o valor numérico.")]
    assert colunas["state"]["residual"]["caidas"] == [("", "conflitante")]


def test_descrever_e_justificar_em_linguagem_de_usuario():
    colunas = rg.ler(MVP)["colunas"]
    [ounces] = [c for c in colunas["ounces"]["candidatas"] if c["tipo"] == "conformidade"]
    assert "formato que o guia mostra" in rg.descrever(ounces)
    [dep] = [c for c in colunas["brewery_id"]["candidatas"] if c["tipo"] == "dependencia"]
    assert rg.descrever(dep) == "o valor é determinado por brewery-name"
    [errada] = [c for c in candidatas(rg.ler(MVP)) if c["motivo"] == "marca_celula_correta"]
    assert "confirmou como correta no guia" in rg.justificar(errada)
    assert rg.contradiz(errada)


def test_montar_destaca_o_que_contradiz_o_guia_e_declara_a_base():
    raciocinio = rg.ler(MVP)
    sorteio = {"linhas": list(range(20)), "trocas": [{"posicao": 0, "saiu": 1, "entrou": 2}]}
    parametros = {"base": "amostra", "tamanho": 300, "semente": 5}
    texto = rg.montar(raciocinio, parametros, sorteio, (31, 3), truncada=True)
    assert "amostra de 300 linhas" in texto and "semente 5" in texto
    assert "1 troca" in texto and "31 chamadas (3 novas)" in texto
    assert "TRUNCADA" in texto
    assert texto.count("contradiz o guia") >= 4
    assert "## ounces" in texto and "`8.4 ounce` → `8.4`" in texto

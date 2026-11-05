"""A amostra-guia e a entrada da geracao: sorteio com semente, validacao e renumeracao."""
import json
import shutil
from pathlib import Path

import pandas as pd

from orquestrador import amostra, config

RAIZ = Path(__file__).resolve().parents[2]
SUJO = RAIZ / "tests" / "fixtures" / "beers_dirty_300.csv"
GUIA_MVP = RAIZ / "dados" / "guia" / "beers"


def ler(caminho, **extra):
    return pd.read_csv(caminho, **config.LER_CSV, **extra)


def test_mesma_semente_mesmo_sorteio():
    a, b = amostra.sortear(300, 20, 7), amostra.sortear(300, 20, 7)
    assert a == b and len(set(a["linhas"])) == 20 and a["trocas"] == []
    assert amostra.sortear(300, 20, 8)["linhas"] != a["linhas"]


def test_trocar_nao_repete_linha_e_registra_a_troca():
    sorteio = amostra.sortear(30, 10, 7)
    trocado = amostra.trocar(amostra.trocar(sorteio, 3), 3)
    assert len(set(trocado["linhas"])) == 10
    saidas = {t["saiu"] for t in trocado["trocas"]}
    assert sorteio["linhas"][3] in saidas and not saidas & set(trocado["linhas"])
    assert [t["posicao"] for t in trocado["trocas"]] == [3, 3]
    assert sorteio["trocas"] == []


def test_template_tem_linha_e_colunas_na_ordem_do_sorteio():
    sujo = ler(SUJO)
    sorteio = amostra.sortear(len(sujo), 10, 7)
    tabela = amostra.template(sujo, sorteio)
    assert list(tabela.columns) == ["_linha", *sujo.columns]
    assert list(tabela["_linha"]) == sorteio["linhas"]
    assert tabela.iloc[0]["state"] == sujo.at[sorteio["linhas"][0], "state"]


def test_template_devolvido_com_linha_alterada_diverge():
    sujo = ler(SUJO)
    sorteio = amostra.sortear(len(sujo), 10, 7)
    tabela = amostra.template(sujo, sorteio)
    assert amostra.divergencias(tabela, sujo, sorteio) == []
    tabela.loc[0, "_linha"] = 299 if 299 not in sorteio["linhas"] else 298
    assert amostra.divergencias(tabela, sujo, sorteio)
    assert amostra.divergencias(tabela.drop(columns=["state"]), sujo, sorteio)
    assert amostra.divergencias(tabela.iloc[:5], sujo, sorteio)


def test_pares_validados_e_completados_pela_celula():
    sujo = ler(SUJO)
    pares = pd.DataFrame([{"linha": "12", "coluna": "abv", "limpo": "0.069"},
                          {"linha": "999", "coluna": "abv", "limpo": "x"},
                          {"linha": "3", "coluna": "nao_existe", "limpo": "x"},
                          {"linha": "abc", "coluna": "abv", "limpo": "x"}])
    completos, problemas = amostra.completar_pares(pares, sujo)
    assert completos.to_dict("records") == [
        {"linha": 12, "coluna": "abv", "sujo": sujo.at[12, "abv"], "limpo": "0.069"}]
    assert len(problemas) == 3


def _guia_do_mvp(tmp_path):
    """Grava, pelo amostra.gravar_guia, o guia do MVP como se o usuario o tivesse corrigido."""
    sujo = ler(SUJO)
    guia = ler(GUIA_MVP / "guia_linhas.csv")
    pares = ler(GUIA_MVP / "guia_pares.csv")
    sorteio = {"semente": 1, "n_total": 300, "linhas": [int(v) for v in guia["_linha"]], "trocas": []}
    amostra.gravar_guia(tmp_path / "guia", guia, pares, sujo, sorteio)
    return sujo, tmp_path / "guia"


def test_gravar_guia_preserva_ordem_e_guarda_as_linhas_sujas(tmp_path):
    sujo, pasta = _guia_do_mvp(tmp_path)
    assert ler(pasta / "guia_linhas.csv").equals(ler(GUIA_MVP / "guia_linhas.csv"))
    assert ler(pasta / "guia_pares.csv").equals(ler(GUIA_MVP / "guia_pares.csv"))
    sujas = amostra.linhas_sujas(pasta)
    citadas = set(ler(GUIA_MVP / "guia_linhas.csv")["_linha"].astype(int)) | set(
        ler(GUIA_MVP / "guia_pares.csv")["linha"].astype(int))
    assert set(sujas.index) == citadas
    assert sujas.loc[12].equals(sujo.loc[12])
    assert json.loads((pasta / "sorteio.json").read_text(encoding="utf-8"))["semente"] == 1


def test_base_inteira_e_a_identidade(tmp_path):
    sujo, pasta = _guia_do_mvp(tmp_path)
    parametros = amostra.montar_entrada(sujo, pasta, tmp_path / "entrada", "inteira", 300, 5)
    assert ler(tmp_path / "entrada" / "sujo.csv").equals(sujo)
    assert ler(tmp_path / "entrada" / "guia" / "guia_linhas.csv").equals(ler(GUIA_MVP / "guia_linhas.csv"))
    assert ler(tmp_path / "entrada" / "guia" / "guia_pares.csv").equals(ler(GUIA_MVP / "guia_pares.csv"))
    assert parametros["tamanho"] == 300 and parametros["origem"][7] == {"fonte": "dados", "linha": 7}


def test_amostra_contem_o_guia_e_renumera(tmp_path):
    sujo, pasta = _guia_do_mvp(tmp_path)
    shutil.copy(pasta / "guia_linhas.csv", tmp_path / "x.csv")
    (pasta / "decisoes.json").write_text("[]", encoding="utf-8")
    parametros = amostra.montar_entrada(sujo, pasta, tmp_path / "entrada", "amostra", 100, 5)
    entrada = ler(tmp_path / "entrada" / "sujo.csv")
    guia = ler(tmp_path / "entrada" / "guia" / "guia_linhas.csv")
    pares = ler(tmp_path / "entrada" / "guia" / "guia_pares.csv")
    assert len(entrada) == 100 == parametros["tamanho"]
    origem = [o["linha"] for o in parametros["origem"]]
    assert origem == sorted(origem)
    original = ler(GUIA_MVP / "guia_linhas.csv")
    for novo, velho in zip(guia["_linha"].astype(int), original["_linha"].astype(int)):
        assert entrada.loc[novo].equals(sujo.loc[velho])
    for novo, velho in zip(pares["linha"].astype(int), ler(GUIA_MVP / "guia_pares.csv")["linha"].astype(int)):
        assert entrada.loc[novo].equals(sujo.loc[velho])
    assert (tmp_path / "entrada" / "guia" / "decisoes.json").read_text(encoding="utf-8") == "[]"
    outra = amostra.montar_entrada(sujo, pasta, tmp_path / "outra", "amostra", 100, 5)
    assert outra == parametros


def test_esquema_conhecido_poe_as_linhas_antigas_na_frente(tmp_path):
    sujo, pasta = _guia_do_mvp(tmp_path)
    novo = sujo.iloc[::-1].reset_index(drop=True).head(150)
    antigas = amostra.linhas_sujas(pasta)
    parametros = amostra.montar_entrada(novo, pasta, tmp_path / "entrada", "inteira", 150, 5, antigas)
    entrada = ler(tmp_path / "entrada" / "sujo.csv")
    assert len(entrada) == len(antigas) + 150
    assert [o["fonte"] for o in parametros["origem"]][:len(antigas)] == ["guia"] * len(antigas)
    guia = ler(tmp_path / "entrada" / "guia" / "guia_linhas.csv")
    for posicao, velho in zip(guia["_linha"].astype(int), ler(GUIA_MVP / "guia_linhas.csv")["_linha"].astype(int)):
        assert entrada.loc[posicao].equals(sujo.loc[velho])
    pares = ler(tmp_path / "entrada" / "guia" / "guia_pares.csv")
    for posicao, velho in zip(pares["linha"].astype(int), ler(GUIA_MVP / "guia_pares.csv")["linha"].astype(int)):
        assert entrada.loc[posicao].equals(sujo.loc[velho])


def test_celula_apagada_no_formulario_vira_vazio(tmp_path):
    # Guarda de regressao: no pandas 3 passa tambem sem o fillna; morde no pandas 2.
    sujo = ler(SUJO)
    sorteio = amostra.sortear(len(sujo), 10, 7)
    guia = amostra.template(sujo, sorteio).astype(object)
    guia.loc[0, "ibu"] = None
    pares = pd.DataFrame([{"linha": 12, "coluna": "ibu", "sujo": "N/A", "limpo": None}])
    amostra.gravar_guia(tmp_path, guia, pares, sujo, sorteio)
    assert ler(tmp_path / "guia_linhas.csv").loc[0, "ibu"] == ""
    assert ler(tmp_path / "guia_pares.csv").loc[0, "limpo"] == ""

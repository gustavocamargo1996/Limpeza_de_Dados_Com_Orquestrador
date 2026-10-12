"""Conformidade de schema: o schema sai das celulas do guia. Ver docs/DECISOES.md#conformidade-de-schema."""
import pandas as pd

from limpeza2.conformidade import candidatas_de_conformidade, schema_da_coluna
from limpeza2.motor import detectar
from limpeza2.tipos import Entrada, Perfil


def entrada_com_guia(guia, sujo=None):
    guia = pd.DataFrame(guia)
    sujo = guia if sujo is None else pd.DataFrame(sujo)
    vazio = pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"])
    return Entrada(sujo=sujo, guia_linhas=guia, guia_pares=vazio,
                   perfil=Perfil(colunas={}, pares={}, candidatas_sujeito=[]))


def guia_com_padroes(n_padroes, n_linhas=12):
    """Coluna `v` com n_padroes padroes distintos (a, aa, aaa...) em n_linhas linhas."""
    valores = ["a" * (i % n_padroes + 1) for i in range(n_linhas)]
    return entrada_com_guia({"v": valores})


def test_schema_apertado_marca_so_o_que_foge():
    entrada = entrada_com_guia({"v": ["12", "34", "56"]}, {"v": ["12", "7", "ab", "99"]})
    candidata = candidatas_de_conformidade(entrada)[0]
    assert candidata.tipo == "conformidade" and candidata.parametros == {"padroes": ["92"]}
    mascara = detectar(entrada.sujo, "v", "conformidade", candidata.parametros)
    assert list(mascara) == [False, True, True, False]


def test_texto_livre_nao_tem_schema_e_nao_emite_candidata():
    entrada = entrada_com_guia({"v": [f"{'a' * (i + 1)}" for i in range(12)]})
    assert schema_da_coluna(entrada, "v") is None
    assert candidatas_de_conformidade(entrada) == []


def test_no_limite_exato_de_um_terco_tem_schema():
    assert schema_da_coluna(guia_com_padroes(4), "v") == {"a", "a2", "a3", "a4"}


def test_um_padrao_acima_do_limite_nao_tem_schema():
    assert schema_da_coluna(guia_com_padroes(5), "v") is None


def test_guia_vazio_ou_coluna_ausente_nao_emite_candidata():
    vazio = entrada_com_guia({"v": []}, {"v": ["x", "y"]})
    assert candidatas_de_conformidade(vazio) == []
    sem_coluna = entrada_com_guia({"w": ["1"] * 6}, {"v": ["x"] * 6, "w": ["1"] * 6})
    assert schema_da_coluna(sem_coluna, "v") is None
    assert [c.coluna for c in candidatas_de_conformidade(sem_coluna)] == ["w"]

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


def valor_de_padrao(k):
    """Valor cujo padrao de nivel 3 e unico para cada k: a1a1... com k+1 caracteres."""
    return ("a1" * 20)[: k + 1]


def guia_com_padroes(n_padroes, n_linhas=12):
    """Coluna `v` com n_padroes padroes distintos de nivel 3 em n_linhas linhas."""
    return entrada_com_guia({"v": [valor_de_padrao(i % n_padroes) for i in range(n_linhas)]})


def test_schema_apertado_marca_so_o_que_foge():
    entrada = entrada_com_guia({"v": ["12", "34", "56"]}, {"v": ["12", "7", "ab", "99"]})
    candidata = candidatas_de_conformidade(entrada)[0]
    assert candidata.tipo == "conformidade" and candidata.parametros == {"padroes": ["9"]}
    mascara = detectar(entrada.sujo, "v", "conformidade", candidata.parametros)
    assert list(mascara) == [False, False, True, False]


def test_numerica_de_largura_variavel_sem_erro_nao_e_marcada():
    # O guia viu 1 e 2 digitos; o sujo tem 3. O nivel 2 marcava "299" por acidente da amostra.
    guia = {"v": ["5", "17", "8", "42", "9", "31"]}
    entrada = entrada_com_guia(guia, {"v": ["5", "17", "299", "100", "0"]})
    candidata = candidatas_de_conformidade(entrada)[0]
    mascara = detectar(entrada.sujo, "v", "conformidade", candidata.parametros)
    assert not mascara.any()


def test_texto_livre_nao_tem_schema_e_nao_emite_candidata():
    entrada = guia_com_padroes(12, n_linhas=12)
    assert schema_da_coluna(entrada, "v") is None
    assert candidatas_de_conformidade(entrada) == []


def test_no_limite_exato_de_um_terco_tem_schema():
    assert len(schema_da_coluna(guia_com_padroes(4), "v")) == 4


def test_um_padrao_acima_do_limite_nao_tem_schema():
    assert schema_da_coluna(guia_com_padroes(5), "v") is None


def test_guia_vazio_ou_coluna_ausente_nao_emite_candidata():
    vazio = entrada_com_guia({"v": []}, {"v": ["x", "y"]})
    assert candidatas_de_conformidade(vazio) == []
    sem_coluna = entrada_com_guia({"w": ["1"] * 6}, {"v": ["x"] * 6, "w": ["1"] * 6})
    assert schema_da_coluna(sem_coluna, "v") is None
    assert [c.coluna for c in candidatas_de_conformidade(sem_coluna)] == ["w"]

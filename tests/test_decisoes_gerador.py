"""As decisoes do usuario no gerador: leitura, crivo, herdadas, instrucao e reaproveitamento."""
import json
import shutil

from limpeza2 import config
from limpeza2.e1_perfil import perfilar
from limpeza2.espinha import gerar_limpador
from tests.test_invariante import FIXTURES, GUIA, PASTA_DO_RUN, SUJO, sem_cr


def guia_com(tmp_path, decisoes):
    """Copia o guia do beers para tmp e grava nele o decisoes.json."""
    pasta = tmp_path / "guia"
    shutil.copytree(GUIA, pasta)
    (pasta / "decisoes.json").write_text(json.dumps(decisoes), encoding="utf-8")
    return pasta


def test_sem_decisoes_json_a_lista_e_vazia():
    assert perfilar(SUJO, GUIA).decisoes == []


def test_le_o_decisoes_json_da_pasta_do_guia(tmp_path):
    d = {"coluna": "ibu", "tipo": "faixa", "parametros": {"minimo": 0, "maximo": 150},
         "decisao": "aprovar"}
    entrada = perfilar(SUJO, guia_com(tmp_path, [d]))
    assert entrada.decisao("ibu", "faixa", {"minimo": 0, "maximo": 150}) == d
    assert entrada.decisao("ibu", "faixa", {"minimo": 0, "maximo": 151}) is None


def test_decisoes_vazias_geram_o_mesmo_limpador_e_raciocinio(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROVEDOR", "gravado")
    monkeypatch.setattr(config, "RESPOSTAS_GRAVADAS", str(FIXTURES / "respostas_beers_poc2.jsonl"))
    sem = gerar_limpador(SUJO, GUIA, tmp_path / "a" / PASTA_DO_RUN)
    com = gerar_limpador(SUJO, guia_com(tmp_path, []), tmp_path / "b" / PASTA_DO_RUN)
    assert sem_cr(com) == sem_cr(sem) == sem_cr(FIXTURES / "limpador_beers_poc2.py")
    nome = f"raciocinio_{PASTA_DO_RUN}.md"
    assert sem_cr(com.parent / nome) == sem_cr(sem.parent / nome)

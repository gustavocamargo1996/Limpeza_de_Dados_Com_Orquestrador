"""A fronteira: o orquestrador usa o gerador so pelo filho de geracao, e o gerador nao o conhece."""
import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ORQUESTRADOR = sorted((RAIZ / "orquestrador").glob("*.py"))
GERADOR = sorted((RAIZ / "limpeza2").glob("*.py"))
# O unico import do gerador permitido, e so no modulo que roda como filho.
PERMITIDO = {("geracao.py", "limpeza2.espinha")}


def importados(caminho):
    """Os modulos que o arquivo importa, pelo nome completo."""
    nomes = set()
    for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            nomes |= {alias.name for alias in no.names}
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module)
    return nomes


def test_ha_modulos_dos_dois_lados():
    assert len(ORQUESTRADOR) >= 10 and len(GERADOR) >= 10


@pytest.mark.parametrize("caminho", ORQUESTRADOR, ids=lambda p: p.name)
def test_orquestrador_nao_importa_o_gerador_nem_os_guardioes(caminho):
    proibidos = {n for n in importados(caminho)
                 if n.split(".")[0] in {"limpeza2", "medir", "preparar_guia"}}
    assert proibidos <= {m for arquivo, m in PERMITIDO if arquivo == caminho.name}, proibidos


@pytest.mark.parametrize("caminho", GERADOR, ids=lambda p: p.name)
def test_gerador_nao_conhece_o_orquestrador(caminho):
    assert not {n for n in importados(caminho) if n.split(".")[0] == "orquestrador"}

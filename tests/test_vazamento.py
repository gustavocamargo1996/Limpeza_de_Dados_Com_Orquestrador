"""Invariante: a geracao nunca alcanca o CSV limpo. Ver docs/DECISOES.md#guia-sorteado."""
import ast
from pathlib import Path

import pytest

PACOTE = Path(__file__).resolve().parent.parent / "limpeza2"
GUARDIOES = {"preparar_guia", "medir"}


def modulos():
    return sorted(p for p in PACOTE.rglob("*.py") if p.name != "__init__.py")


def test_o_pacote_tem_modulos():
    assert modulos(), "sem modulos, o teste de vazamento nao estaria testando nada"


@pytest.mark.parametrize("caminho", modulos(), ids=lambda p: str(p.relative_to(PACOTE)))
def test_nenhum_modulo_importa_os_guardioes(caminho):
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom):
            if no.module:
                importados.add(no.module.split(".")[0])
            importados.update(alias.name.split(".")[0] for alias in no.names)
    vazando = importados & GUARDIOES
    assert not vazando, f"{caminho.name} importa {vazando}: o gabarito vazaria para a geracao"


@pytest.mark.parametrize("caminho", modulos(), ids=lambda p: str(p.relative_to(PACOTE)))
def test_nenhum_modulo_cita_arquivo_csv(caminho):
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    literais = [
        no.value
        for no in ast.walk(arvore)
        if isinstance(no, ast.Constant)
        and isinstance(no.value, str)
        and no.value.lower().endswith(".csv")
    ]
    assert not literais, (
        f"{caminho.name} tem literal de CSV em {literais}: o caminho tem de vir por argumento"
    )

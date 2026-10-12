"""Invariante: a geracao nunca alcanca o CSV limpo. Ver docs/DECISOES.md#guia-sorteado."""
import ast
from pathlib import Path

import pytest

PACOTE = Path(__file__).resolve().parent.parent / "limpeza2"
GUARDIOES = {"preparar_guia", "medir"}
# Unicos literais .csv permitidos, por nome exato: os dois arquivos do guia.
CSV_PERMITIDOS = {"guia_linhas.csv", "guia_pares.csv"}
# O motor e copiado para dentro do limpador gerado, que roda sem este repositorio.
IMPORTS_PERMITIDOS_NO_MOTOR = {"pandas"}


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
            importados.update(parte for alias in no.names for parte in alias.name.split("."))
        elif isinstance(no, ast.ImportFrom):
            if no.module:
                importados.update(no.module.split("."))
            importados.update(parte for alias in no.names for parte in alias.name.split("."))
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
        and no.value not in CSV_PERMITIDOS
        and (no.value.lower().endswith(".csv") or no.value in GUARDIOES)
    ]
    assert not literais, (
        f"{caminho.name} tem literal proibido em {literais}: CSV vem por argumento e guardiao nao se cita por nome"
    )


def test_motor_importa_so_o_permitido():
    arvore = ast.parse((PACOTE / "motor.py").read_text(encoding="utf-8"))
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom):
            importados.add(f"{'.' * no.level}{no.module or ''}".split(".")[0] or "<relativo>")
    assert importados, "motor sem import algum: o teste nao estaria testando nada"
    assert importados <= IMPORTS_PERMITIDOS_NO_MOTOR, (
        f"motor.py importa {importados - IMPORTS_PERMITIDOS_NO_MOTOR}: o limpador gerado quebraria"
    )

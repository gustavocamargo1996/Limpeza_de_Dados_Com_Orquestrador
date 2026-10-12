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


def test_geracao_so_abre_o_sujo_o_guia_e_o_motor(tmp_path, roteiro, monkeypatch):
    import builtins
    import io

    import pandas as pd

    from limpeza2 import e6_codificador
    from limpeza2.espinha import gerar_limpador

    raiz = PACOTE.parent
    sujo = raiz / "tests" / "fixtures" / "beers_dirty_300.csv"
    guia = raiz / "dados" / "guia" / "beers"
    destino = tmp_path / "beers_vazamento"
    roteiro(lambda instrucao, conteudo: {})
    abertos = []
    ler_csv, abrir = pd.read_csv, io.open

    def espia_csv(caminho, *args, **kwargs):
        abertos.append(Path(caminho).resolve())
        return ler_csv(caminho, *args, **kwargs)

    def espia_open(arquivo, *args, **kwargs):
        if isinstance(arquivo, (str, Path)):
            abertos.append(Path(arquivo).resolve())
        return abrir(arquivo, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", espia_csv)
    monkeypatch.setattr(io, "open", espia_open)
    monkeypatch.setattr(builtins, "open", espia_open)
    gerar_limpador(sujo, guia, destino)

    permitidos = {sujo.resolve(), (guia / "guia_linhas.csv").resolve(),
                  (guia / "guia_pares.csv").resolve(), e6_codificador.MOTOR.resolve()}
    assert abertos, "nada foi aberto: a espia nao estaria espiando"
    intrusos = [p for p in abertos if p not in permitidos and destino.resolve() not in p.parents]
    assert not intrusos, f"a geracao abriu {intrusos}: so o sujo, o guia e o motor podem ser lidos"

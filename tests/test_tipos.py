"""A forma literal das regras, que o residual usa e o limpador embute."""
from limpeza2.tipos import Candidata, Reparo, regras_literais


def candidata(tipo, coluna="estado"):
    return Candidata(coluna=coluna, tipo=tipo, parametros={"valores": ["MA"]}, raciocinio="r")


def test_ordena_pelo_catalogo_de_tipos():
    dep, fmt = candidata("dependencia"), candidata("formato")
    assert [r["tipo"] for r in regras_literais([dep, fmt], [])] == ["formato", "dependencia"]


def test_reparo_vai_para_a_candidata_pela_identidade():
    # Duas candidatas iguais em tudo: so a segunda ganhou reparo.
    primeira, segunda = candidata("dominio"), candidata("dominio")
    reparo = Reparo(candidata=segunda, estrategia="esvaziar", parametros={}, raciocinio="r")
    regras = regras_literais([primeira, segunda], [reparo])
    assert [r["estrategia"] for r in regras] == [None, "esvaziar"]
    assert regras[0]["reparo"] is None


def test_formato_literal():
    c = candidata("dominio")
    reparo = Reparo(candidata=c, estrategia="dicionario", parametros={"mapa": {"XX": "MA"}}, raciocinio="r")
    assert regras_literais([c], [reparo]) == [{
        "coluna": "estado", "tipo": "dominio", "deteccao": {"valores": ["MA"]},
        "estrategia": "dicionario", "reparo": {"mapa": {"XX": "MA"}},
    }]

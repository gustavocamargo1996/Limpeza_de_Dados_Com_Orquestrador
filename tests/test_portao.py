"""O portao: codigo gerado por LLM nao roda antes de passar."""
import pytest

from limpeza2.portao import CodigoRejeitado, materializar, validar
# Alias: o pytest coletaria um nome importado que comeca com 'test' como se fosse teste.
from limpeza2.portao import testar_fumaca as rodar_fumaca

VALIDA = 'def corrigir(valor):\n    return valor.strip().lower()\n'


def test_aceita_funcao_escalar_simples():
    assert materializar(VALIDA)("  ABC ") == "abc"


def test_aceita_uso_de_re_sem_import():
    codigo = 'def corrigir(valor):\n    return re.sub(r"\\.0$", "", valor)\n'
    assert materializar(codigo)("12.0") == "12"


@pytest.mark.parametrize(
    "codigo,trecho",
    [
        ('import os\ndef corrigir(valor):\n    return valor\n', "import"),
        ('def corrigir(valor):\n    return open(valor).read()\n', "open"),
        ('def corrigir(valor):\n    return eval(valor)\n', "eval"),
        ('def corrigir(valor):\n    return valor.__class__\n', "dunder"),
        ('def corrigir(valor):\n    return __import__("os")\n', "__import__"),
        ('def limpar(valor):\n    return valor\n', "corrigir"),
        ('def corrigir(v):\n    return v\n', "valor"),
        ('def corrigir(valor):\n    return valor\nX = 1\n', "uma definicao de funcao"),
        ('def corrigir(valor):\n    return valor(\n', "sintaxe"),
    ],
)
def test_rejeita_codigo_proibido(codigo, trecho):
    with pytest.raises(CodigoRejeitado, match=trecho):
        validar(codigo)


def test_rejeita_sem_executar(monkeypatch):
    marcas = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: marcas.append(a))
    with pytest.raises(CodigoRejeitado):
        materializar('import os\ndef corrigir(valor):\n    print("rodei")\n    return valor\n')
    assert marcas == []


def test_fumaca_pega_falha_em_runtime():
    funcao = materializar('def corrigir(valor):\n    return valor[9]\n')
    with pytest.raises(CodigoRejeitado, match="IndexError"):
        rodar_fumaca(funcao, ["ab"])


def test_fumaca_passa_com_funcao_sadia():
    rodar_fumaca(materializar(VALIDA), ["ab", "", "  X  "])

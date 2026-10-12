"""O portao: codigo gerado por LLM nao roda antes de passar."""
import pytest

from limpeza2.portao import CodigoRejeitado, materializar, testar_fumaca, validar

VALIDA = 'def corrigir(valor):\n    return valor.strip().lower()\n'


def test_aceita_funcao_escalar_simples():
    assert materializar(VALIDA)("  ABC ") == "abc"


def test_aceita_uso_de_re_sem_import():
    codigo = 'def corrigir(valor):\n    return re.sub(r"\\.0$", "", valor)\n'
    assert materializar(codigo)("12.0") == "12"


def test_aceita_flag_de_re():
    codigo = 'def corrigir(valor):\n    return re.sub(r"x", "y", valor, flags=re.I)\n'
    assert materializar(codigo)("aXb") == "ayb"


@pytest.mark.parametrize(
    "codigo,trecho",
    [
        ('import os\ndef corrigir(valor):\n    return valor\n', "import"),
        ('def corrigir(valor):\n    import os\n    return valor\n', "import proibido"),
        ('def corrigir(valor):\n    from os import path\n    return valor\n', "import proibido"),
        ('def corrigir(valor):\n    return open(valor).read()\n', "open"),
        ('def corrigir(valor):\n    return eval(valor)\n', "eval"),
        ('def corrigir(valor):\n    return exec(valor)\n', "chamada proibida: exec"),
        ('def corrigir(valor):\n    return compile(valor, "x", "eval")\n', "chamada proibida: compile"),
        ('def corrigir(valor):\n    return getattr(valor, "upper")\n', "chamada proibida: getattr"),
        ('def corrigir(valor):\n    return setattr(valor, "a", 1)\n', "chamada proibida: setattr"),
        ('def corrigir(valor):\n    return globals()\n', "chamada proibida: globals"),
        ('def corrigir(valor):\n    return input()\n', "chamada proibida: input"),
        ('def corrigir(valor):\n    return "{0.__class__}".format(valor)\n', r"metodo proibido: \.format"),
        ('def corrigir(valor):\n    return "{0.__class__}".format_map({})\n', r"metodo proibido: \.format_map"),
        ('def corrigir(valor):\n    f = "{0.__class__}".format\n    return f(valor)\n', r"metodo proibido: \.format"),
        ('def corrigir(valor):\n    return str(list(map("{0.__class__}".format, [valor])))\n', r"metodo proibido: \.format"),
        ('def corrigir(valor):\n    f = "{a}".format_map\n    return f({})\n', r"metodo proibido: \.format_map"),
        ('def corrigir(valor):\n    re.sub = len\n    return valor\n', "escrita de atributo proibida"),
        ('def corrigir(valor):\n    del re.sub\n    return valor\n', "escrita de atributo proibida"),
        ('def corrigir(valor):\n    return valor.__class__\n', "dunder"),
        ('def corrigir(valor):\n    __builtins__.clear()\n    return valor\n', "nome dunder proibido"),
        ('def corrigir(valor):\n    return __import__("os")\n', "__import__"),
        ('def limpar(valor):\n    return valor\n', "corrigir"),
        ('def corrigir(valor):\n    return corrigir(valor[1:]) if valor else valor\n', "recursao proibida"),
        ('def corrigir(valor):\n    f = corrigir\n    return valor\n', "recursao proibida"),
        ('def corrigir(v):\n    return v\n', "valor"),
        ('def corrigir(*valor):\n    return valor\n', "so-nomeado"),
        ('def corrigir(valor, *, k=1):\n    return valor\n', "so-nomeado"),
        ('def corrigir(valor, /):\n    return valor\n', "so-nomeado"),
        ('def corrigir(valor):\n    return valor\nX = 1\n', "uma definicao de funcao"),
        ('def corrigir(valor):\n    return valor(\n', "sintaxe"),
    ],
)
def test_rejeita_codigo_proibido(codigo, trecho):
    with pytest.raises(CodigoRejeitado, match=trecho):
        validar(codigo)


def test_materializacoes_nao_compartilham_o_proxy_de_re():
    a, b = materializar(VALIDA), materializar(VALIDA)
    assert a.__globals__["re"] is not b.__globals__["re"]


def test_rejeita_sem_executar(monkeypatch):
    marcas = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: marcas.append(a))
    with pytest.raises(CodigoRejeitado):
        materializar('import os\ndef corrigir(valor):\n    print("rodei")\n    return valor\n')
    assert marcas == []


@pytest.mark.parametrize(
    "corpo",
    [
        'str(re.enum.sys.modules["os"].getcwd())',
        "re.functools",
    ],
)
def test_re_nao_vaza_modulos(corpo):
    funcao = materializar(f"def corrigir(valor):\n    return {corpo}\n")
    with pytest.raises(CodigoRejeitado, match="AttributeError"):
        testar_fumaca(funcao, ["ab"])


@pytest.mark.parametrize("nome", ["open", "print"])
def test_alias_de_builtin_fora_da_allowlist_morre_na_fumaca(nome):
    funcao = materializar(f"def corrigir(valor):\n    f = {nome}\n    return str(f(valor))\n")
    with pytest.raises(CodigoRejeitado, match="NameError"):
        testar_fumaca(funcao, ["ab"])


def test_fumaca_pega_falha_em_runtime():
    funcao = materializar('def corrigir(valor):\n    return valor[9]\n')
    with pytest.raises(CodigoRejeitado, match="IndexError"):
        testar_fumaca(funcao, ["ab"])


def test_fumaca_passa_com_funcao_sadia():
    testar_fumaca(materializar(VALIDA), ["ab", "", "  X  "])

@pytest.mark.parametrize("corpo", ["yield valor", "return None", "return [valor]"])
def test_fumaca_rejeita_o_que_nao_devolve_str(corpo):
    funcao = materializar(f"def corrigir(valor):\n    {corpo}\n")
    with pytest.raises(CodigoRejeitado, match="deve devolver str"):
        testar_fumaca(funcao, ["ab"])

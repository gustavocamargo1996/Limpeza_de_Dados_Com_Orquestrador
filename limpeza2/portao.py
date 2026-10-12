"""Valida o Python gerado pelo LLM antes de deixa-lo rodar."""
import ast
import re

NOME_FUNCAO = "corrigir"
NOME_ARGUMENTO = "valor"

# O namespace do exec e sempre descartavel, nunca globals().
# Ver docs/DECISOES.md#portao-ast.
_CHAMADAS_PROIBIDAS = {
    "__import__", "eval", "exec", "compile", "open", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "breakpoint", "memoryview", "exit", "quit",
}

_BUILTINS_PERMITIDOS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float, "int": int,
    "len": len, "list": list, "map": map, "max": max, "min": min,
    "range": range, "round": round, "set": set, "sorted": sorted,
    "str": str, "sum": sum, "tuple": tuple, "zip": zip,
    "isinstance": isinstance, "ValueError": ValueError, "TypeError": TypeError,
    "AttributeError": AttributeError, "IndexError": IndexError,
    "KeyError": KeyError, "Exception": Exception, "None": None,
}


class CodigoRejeitado(Exception):
    """O codigo gerado nao passou no portao, e nunca foi executado."""


def validar(codigo, nome_funcao=NOME_FUNCAO, nome_argumento=NOME_ARGUMENTO):
    """Analisa a AST e levanta CodigoRejeitado sem executar nada."""
    try:
        arvore = ast.parse(codigo)
    except SyntaxError as erro:
        raise CodigoRejeitado(f"sintaxe invalida: {erro}") from erro

    if len(arvore.body) != 1 or not isinstance(arvore.body[0], ast.FunctionDef):
        raise CodigoRejeitado(
            "o codigo deve ter exatamente uma definicao de funcao e mais nada: "
            "sem import, sem constante de modulo, sem chamada no topo"
        )

    funcao = arvore.body[0]
    if funcao.name != nome_funcao:
        raise CodigoRejeitado(
            f"a funcao deve se chamar '{nome_funcao}', veio '{funcao.name}'"
        )
    args = funcao.args
    if args.vararg or args.kwarg or args.kwonlyargs or args.posonlyargs:
        raise CodigoRejeitado("sem *args, **kwargs nem argumento so-nomeado")
    if len(args.args) != 1 or args.args[0].arg != nome_argumento:
        raise CodigoRejeitado(
            f"a funcao deve receber um argumento so, chamado '{nome_argumento}'"
        )

    for no in ast.walk(funcao):
        if isinstance(no, (ast.Import, ast.ImportFrom)):
            raise CodigoRejeitado("import proibido: o modulo 're' ja esta disponivel")
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
            if no.func.id in _CHAMADAS_PROIBIDAS:
                raise CodigoRejeitado(f"chamada proibida: {no.func.id}()")
        if isinstance(no, ast.Attribute) and no.attr.startswith("__"):
            raise CodigoRejeitado(f"acesso a atributo dunder proibido: {no.attr}")


def materializar(codigo, nome_funcao=NOME_FUNCAO, nome_argumento=NOME_ARGUMENTO):
    """Valida e devolve a funcao viva; nao materializa o que `validar` rejeitar."""
    validar(codigo, nome_funcao=nome_funcao, nome_argumento=nome_argumento)
    # pandas fica fora do namespace: o LLM so escreve funcao escalar.
    namespace = {"re": re, "__builtins__": dict(_BUILTINS_PERMITIDOS)}
    exec(compile(codigo, "<regra-gerada>", "exec"), namespace, namespace)
    funcao = namespace.get(nome_funcao)
    if not callable(funcao):
        raise CodigoRejeitado("a funcao nao ficou definida apos a execucao")
    return funcao


def testar_fumaca(funcao, amostras):
    """Chama a funcao com valores reais e rejeita a que falhar em runtime."""
    for amostra in amostras:
        try:
            funcao(amostra)
        except Exception as erro:
            raise CodigoRejeitado(
                f"a funcao lancou {type(erro).__name__} com \"{amostra}\": {erro}. "
                "Atencao a regex mal formada: flag inline como (?i) so vale no inicio."
            ) from erro

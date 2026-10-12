# Relatorio da tarefa 4: portao.py

## Commits
1. `a65385e` medir.py: suprime so SyntaxWarning e UserWarning (item prependido). `medir.py` fica na raiz, nao em `limpeza2/`. `simplefilter("ignore")` virou dois `filterwarnings("ignore", category=...)`. `tests/test_medir.py`: 11 testes passam, saida limpa, sem warning.
2. Commit da tarefa 4 (`limpeza2/portao.py`, `tests/test_portao.py`): codigo do brief copiado literalmente.

## TDD
RED: `pytest tests/test_portao.py` -> `ModuleNotFoundError: No module named 'limpeza2.portao'` (esperado, modulo nao existia).
GREEN: 14 passed.

## Desvios do brief
- Contagem: sao **14** testes (2 + 9 parametrizados + `test_rejeita_sem_executar` + 2 de fumaca), nao 13. Mais um erro de contagem do brief.
- O brief importa `testar_fumaca` no modulo de teste; o pytest o coleta como teste e dava `ERROR ... fixture 'funcao' not found`. Importei com alias `rodar_fumaca` (com comentario de 1 linha). `portao.py` nao mudou e o nome publico continua `testar_fumaca`.

## Provas por mutacao (executadas)
- **A (tirar o bloco de import)**: 14 passed, exit 0. NAO falhou. Causa: um `import` no topo do modulo ja e barrado antes, pela checagem "exatamente uma definicao de funcao". O bloco so pega `import` dentro do corpo da funcao, que nenhum teste cobre (confirmado a mao: `validar` rejeita `def corrigir(valor): import os` com a mensagem de import). Logo a previsao do brief estava errada e o bloco esta sem teste.
- **B (namespace = {"re": re})**: 14 passed, exit 0. NAO falhou. Era de se esperar: `exec` injeta `__builtins__` completo e os testes so usam strip/lower/re, que funcionam com ou sem allowlist. Nenhum teste prova a allowlist. Confirmado a mao com o codigo real: `f = open; return str(f)` (a AST nao pega, pois o `Call` e em `str`) da `NameError: name 'open' is not defined` no portao normal, e escaparia sem a allowlist.
- **C (startswith("____"))**: falhou exatamente `test_rejeita_codigo_proibido[... valor.__class__ ... dunder]`. Morde.
Todas as mutacoes foram revertidas (diff com a copia original vazio; 14 passed).

## Orcamento
Antes: 5 arquivos, 297 linhas. Depois: 6 arquivos, 387 linhas (portao.py 89). Teto 13 / 1.400 / 200.

## Auto-revisao e preocupacoes
- Lacunas de teste (A e B): sugiro dois testes, a decidir por voce: (1) rejeitar `def corrigir(valor):\n    import os\n    return valor`; (2) `materializar` de `f = open; return str(f)` seguido de chamada deve lancar NameError (prova a allowlist). Nao adicionei, para nao mudar os valores do brief.
- Sobre a mutacao B: pode-se dizer que a allowlist esta sem cobertura, nao que o portao falha; a protecao existe (verificada a mao).
- `compile` e `memoryview` estao em `_CHAMADAS_PROIBIDAS` mas nao ha teste por item; so eval/open/__import__ sao cobertos.
- Mensagem de import cita 're' em todo caso; sem acento, ok.

---

# Rodada de correcao 1

Commit: ver `git log` (assunto "portao.py: fecha o escape por re.enum.sys e barra format").

## O que mudou
- `portao.py`: o namespace recebe `_RE_PERMITIDO`, um `SimpleNamespace` com sub, subn, search, match, fullmatch, findall, finditer, split, escape, compile e as flags I, IGNORECASE, M, MULTILINE, S, DOTALL, X, VERBOSE, A, ASCII, no lugar do modulo `re`. `.format()` e `.format_map()` passam a ser rejeitados (`_METODOS_PROIBIDOS`, chamada por atributo).
- `pyproject.toml`: `python_functions = ["test_*"]`. O alias `rodar_fumaca` saiu; `testar_fumaca` e importado direto.
- `tests/test_portao.py`: 14 -> **32 testes**.

## Cobertura nova
- Escape: `test_re_nao_vaza_modulos` (re.enum.sys.modules["os"].getcwd() e re.functools; ambos passam em `validar` e morrem com AttributeError na fumaca). `test_aceita_flag_de_re` (re.sub com flags=re.I); o teste do re.sub existente segue verde.
- `import` no corpo e `from os import path` no corpo, com match "import proibido".
- Allowlist: `f = open` e `f = print` via `testar_fumaca`, match "NameError".
- exec, compile, getattr, setattr, globals, input (match "chamada proibida: <nome>"), format e format_map.
- Assinatura: `*valor`, `valor, *, k=1`, `valor, /` (match "so-nomeado").

## Provas por mutacao (script que aplica, roda `pytest tests/test_portao.py`, reverte em finally)
| Mutacao | Resultado |
|---|---|
| M1 `"re": _RE_PERMITIDO` -> `"re": re` | 2 failed (os dois de test_re_nao_vaza_modulos) |
| M2 `_METODOS_PROIBIDOS` vazio | 2 failed (format, format_map) |
| M2b so `{"format"}` | 1 failed (format_map) |
| M3 remove o bloco de import | 2 failed (import no corpo, from os import) |
| M4 remove `__builtins__` do namespace | 2 failed (alias open, alias print) |
| M5 tira `exec` de `_CHAMADAS_PROIBIDAS` | 1 failed (exec) |
| M6 checagem de assinatura reduzida a `args.kwarg` | 3 failed (os tres casos) |
Todas morderam; arquivo revertido (diff com a copia vazio). Na primeira tentativa o script de mutacao falhou ao rodar o subprocesso (caminho relativo do python) e deixou o arquivo mutado; restaurei da copia e refiz com `sys.executable` e `try/finally`; as saidas acima sao da segunda execucao.

## Coleta do pytest
`pytest tests --collect-only`: com a config, test_portao = 32; sem ela, 33 (o `testar_fumaca` importado e coletado como falso teste). Nenhum teste real deixou de ser coletado (medir 11, preparar_guia 6, vazamento 7 iguais).

## Execucao e orcamento
`pytest tests/test_portao.py tests/test_medir.py`: 43 passed (32 + 11). Orcamento: 6 arquivos `.py` fora de tests, 402 linhas no total, portao.py com 104 (teto 13 / 1.400 / 200).

## Preocupacoes
- `re.compile` devolve objeto Pattern, cujos metodos (sub, match...) ficam disponiveis; nao ha caminho conhecido para modulos a partir dele, mas a superficie de Pattern/Match nao foi auditada alem de dunder.
- A allowlist ainda inclui `isinstance`, `dict`, `list`, `str` etc.; atributos nao-dunder de tipos nativos nao foram auditados (ex.: `str.format` barrado, mas `str.__mod__`/`%` e dunder via operador nao passam por Attribute).

---

# Rodada de correcao 2

## O que mudou
- `portao.py`: `_METODOS_PROIBIDOS` agora barra qualquer `ast.Attribute` com esse `attr`, lido ou chamado (mensagem "metodo proibido: .format"); a checagem antiga de `Call` foi removida por redundante. Qualquer `ast.Attribute` com `ctx` Store ou Del e rejeitado ("escrita de atributo proibida"). O proxy de `re` deixou de ser objeto de modulo: o modulo guarda a tupla `_NOMES_RE_PERMITIDOS` (mesma lista) e `materializar` constroi um `SimpleNamespace` novo a cada chamada.
- `tests/test_portao.py`: de 32 para 38 testes (5 casos de format lido, 2 de escrita/remocao em `re`, 1 de isolamento entre materializacoes via `__globals__`).
- Nao mexi no conteudo do proxy nem nos testes de import, allowlist, `_CHAMADAS_PROIBIDAS` e assinatura. Os testes de `.format(...)` chamado trocaram so o trecho de match para a mensagem nova.

## Provas por mutacao: saida bruta do pytest

### M1: volta a exigir Call
```
..............FFFFF...................                                   [100%]
================================== FAILURES ===================================
E   AttributeError: 'Call' object has no attribute 'attr'
C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados_2\limpeza2\portao.py:75: AttributeError: 'Call' object has no attribute 'attr'
E   AttributeError: 'Call' object has no attribute 'attr'
C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados_2\limpeza2\portao.py:75: AttributeError: 'Call' object has no attribute 'attr'
E   Failed: DID NOT RAISE CodigoRejeitado
C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados_2\tests\test_portao.py:56: Failed: DID NOT RAISE CodigoRejeitado
E   Failed: DID NOT RAISE CodigoRejeitado
C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados_2\tests\test_portao.py:56: Failed: DID NOT RAISE CodigoRejeitado
E   Failed: DID NOT RAISE CodigoRejeitado
C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados_2\tests\test_portao.py:56: Failed: DID NOT RAISE CodigoRejeitado
=========================== short test summary info ===========================
FAILED tests/test_portao.py::test_rejeita_codigo_proibido[def corrigir(valor):\n    return "{0.__class__}".format(valor)\n-metodo proibido: \\.format]
FAILED tests/test_portao.py::test_rejeita_codigo_proibido[def corrigir(valor):\n    return "{0.__class__}".format_map({})\n-metodo proibido: \\.format_map]
FAILED tests/test_portao.py::test_rejeita_codigo_proibido[def corrigir(valor):\n    f = "{0.__class__}".format\n    return f(valor)\n-metodo proibido: \\.format]
FAILED tests/test_portao.py::test_rejeita_codigo_proibido[def corrigir(valor):\n    return str(list(map("{0.__class__}".format, [valor])))\n-metodo proibido: \\.format]
FAILED tests/test_portao.py::test_rejeita_codigo_proibido[def corrigir(valor):\n    f = "{a}".format_map\n    return f({})\n-metodo proibido: \\.format_map]
5 failed, 33 passed in 0.05s

```

### M2: sem Store/Del
```
...................FF.................                                   [100%]
================================== FAILURES ===================================
E   Failed: DID NOT RAISE CodigoRejeitado
C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados_2\tests\test_portao.py:56: Failed: DID NOT RAISE CodigoRejeitado
E   Failed: DID NOT RAISE CodigoRejeitado
C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados_2\tests\test_portao.py:56: Failed: DID NOT RAISE CodigoRejeitado
=========================== short test summary info ===========================
FAILED tests/test_portao.py::test_rejeita_codigo_proibido[def corrigir(valor):\n    re.sub = len\n    return valor\n-escrita de atributo proibida]
FAILED tests/test_portao.py::test_rejeita_codigo_proibido[def corrigir(valor):\n    del re.sub\n    return valor\n-escrita de atributo proibida]
2 failed, 36 passed in 0.06s

```

### M3: proxy construido uma vez so
```
..............................F.......                                   [100%]
================================== FAILURES ===================================
E   assert namespace(sub=<function sub at 0x000001D84B025010>, subn=<function subn at 0x000001D84B026610>, search=<function searc...E, MULTILINE=re.MULTILINE, S=re.DOTALL, DOTALL=re.DOTALL, X=re.VERBOSE, VERBOSE=re.VERBOSE, A=re.ASCII, ASCII=re.ASCII) is not namespace(sub=<function sub at 0x000001D84B025010>, subn=<function subn at 0x000001D84B026610>, search=<function searc...E, MULTILINE=re.MULTILINE, S=re.DOTALL, DOTALL=re.DOTALL, X=re.VERBOSE, VERBOSE=re.VERBOSE, A=re.ASCII, ASCII=re.ASCII)
C:\Users\gusta\projects\Limpeza_de_Dados\POC_Limpeza_de_Dados_2\tests\test_portao.py:62: assert namespace(sub=<function sub at 0x000001D84B025010>, subn=<function subn at 0x000001D84B026610>, search=<function searc...E, MULTILINE=re.MULTILINE, S=re.DOTALL, DOTALL=re.DOTALL, X=re.VERBOSE, VERBOSE=re.VERBOSE, A=re.ASCII, ASCII=re.ASCII) is not namespace(sub=<function sub at 0x000001D84B025010>, subn=<function subn at 0x000001D84B026610>, search=<function searc...E, MULTILINE=re.MULTILINE, S=re.DOTALL, DOTALL=re.DOTALL, X=re.VERBOSE, VERBOSE=re.VERBOSE, A=re.ASCII, ASCII=re.ASCII)
=========================== short test summary info ===========================
FAILED tests/test_portao.py::test_materializacoes_nao_compartilham_o_proxy_de_re
1 failed, 37 passed in 0.18s

```

### Verde final
```
......................................                                   [100%]
38 passed in 0.09s
```

## Orcamento e preocupacoes
6 arquivos `.py` fora de tests, 403 linhas, portao.py com 105 (teto 13 / 1.400 / 200). Na M1, os dois casos de chamada direta tambem falham porque a mutacao remove a mensagem nova para chamada; o que prova a correcao sao os tres casos de leitura. Sem preocupacoes novas.

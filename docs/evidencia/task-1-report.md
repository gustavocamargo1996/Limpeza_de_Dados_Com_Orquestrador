# Relatório da Tarefa 1: Esqueleto, tipos, config e o teste de vazamento

**Status:** DONE_WITH_CONCERNS
**Commit:** `0d81921` Esqueleto: tipos, config e o teste de vazamento

## O que foi implementado

- `requirements.txt` (pandas>=2.2, openai>=1.40, python-dotenv>=1.0, pytest>=8.0). O arquivo não existia; foi criado com o `printf` do Step 1.
- `.venv` criado com uv (CPython 3.14.4) e dependências instaladas com `uv pip install -r requirements.txt`. pytest 9.1.1.
- `pyproject.toml` com `[tool.pytest.ini_options]`, `testpaths`, `addopts = "-q"` e `pythonpath = ["."]`. O pytest leu a configuração sem precisar de `pytest.ini`.
- `tests/test_vazamento.py`: três testes, sendo um de presença e dois parametrizados por módulo do pacote.
- `limpeza2/__init__.py` (vazio), `limpeza2/tipos.py` (Perfil, Entrada, Candidata, Reparo, Residual), `limpeza2/config.py` (todas as constantes do brief, com os valores copiados literalmente).
- `.env.exemplo`.

## Testes

Suíte final: 7 testes passando (`.venv/Scripts/python -m pytest -q` e `tests/test_vazamento.py -v`).

Verifiquei também, com um teste temporário que foi removido em seguida, que `from limpeza2.tipos import Perfil` e `from limpeza2.config import SEMENTE` resolvem a partir de `tests/` por causa do `pythonpath`. Sem isso, nenhum teste futuro importaria o pacote. O arquivo temporário não entrou no commit.

## Evidência de TDD

**RED** (`.venv/Scripts/python -m pytest tests/test_vazamento.py -v`, antes de criar `limpeza2/`):

```
collected 3 items
tests\test_vazamento.py Fss                                              [100%]
...
E       AssertionError: sem modulos, o teste de vazamento nao estaria testando nada
E       assert []
E        +  where [] = modulos()
tests\test_vazamento.py:16: AssertionError
FAILED tests/test_vazamento.py::test_o_pacote_tem_modulos - AssertionError: s...
1 failed, 2 skipped in 0.20s
```

A falha foi a esperada: `PACOTE.glob` num diretório inexistente devolveu lista vazia, e o teste de presença acusou isso. Os dois testes parametrizados ficaram como **skip** (lista de parâmetros vazia), não como falha. Isso é a situação prevista no item 3 da orientação. Enquanto o pacote não existe, esses dois testes não cobrem nada, e a presença é o que impede o verde falso.

**GREEN** (depois de criar `limpeza2/`):

```
collected 7 items
tests\test_vazamento.py .......                                          [100%]
7 passed in 0.09s
```

Os 7 testes são: 1 de presença + 2 por módulo × 3 módulos (`__init__.py`, `config.py`, `tipos.py`). O brief dizia "5 testes"; a conta correta é 7.

## Provas por mutação

**Mutação A:** `from preparar_guia import sortear` no topo de `limpeza2/config.py`.

```
FAILED tests/test_vazamento.py::test_nenhum_modulo_importa_os_guardioes[config.py]
E       AssertionError: config.py importa {'preparar_guia'}: o gabarito vazaria para a geracao
1 failed, 6 passed in 0.50s
```

**Mutação B:** `ALVO = "beers_clean.csv"` no fim de `limpeza2/config.py`.

```
FAILED tests/test_vazamento.py::test_nenhum_modulo_cita_arquivo_csv[config.py]
E       AssertionError: config.py tem literal de CSV em ['beers_clean.csv']: o caminho tem de vir por argumento
1 failed, 6 passed in 0.18s
```

Nas duas, `config.py` foi restaurado a partir de uma cópia, `cmp` confirmou arquivo idêntico, e a suíte voltou a 7 passed.

## Arquivos alterados (commit 0d81921)

- `requirements.txt` (novo)
- `pyproject.toml` (novo)
- `.env.exemplo` (novo)
- `limpeza2/__init__.py` (novo, vazio)
- `limpeza2/tipos.py` (novo, 54 linhas)
- `limpeza2/config.py` (novo, 30 linhas)
- `tests/test_vazamento.py` (novo, 44 linhas)

## Orçamento de tamanho (Step 9)

- Arquivos `.py` fora de `tests/`: **3** (teto 13).
- Linhas nesses arquivos: **84** (teto 1.400).
- Maior arquivo: `tipos.py` com 54 linhas (teto 200).

## Auto-revisão

- Os valores de `config.py` foram copiados do brief e conferidos linha a linha.
- `config.py` carrega `.env` com `load_dotenv()`. `.gitignore` já exclui `.env`.
- `PROVEDOR` tem default `openai`. A regra de "PROVEDOR desconhecido falha alto" (CLAUDE.md §7) não entra nesta tarefa e não está implementada aqui. Fica para a tarefa do módulo de provedores.
- `tipos.py` usa `str | None`, que exige Python 3.10 ou superior. O venv usa 3.14, então está coberto.
- Não criei `preparar_guia.py` nem `medir.py`. O teste apenas os nomeia.
- Nenhum `try`, nenhuma chamada de API, nenhum comentário inline.

## Desvios em relação ao brief

1. **Co-Authored-By:** o brief traz `Claude Opus 5 (1M context)`. Usei `Claude Haiku 5.5 <noreply@anthropic.com>`, que é o modelo indicado no contexto desta sessão.
2. **`git add -A`:** não usei. Adicionei os sete arquivos por caminho explícito, para não arrastar nada que não seja desta tarefa.
3. **Contagem de testes:** 7, não 5 (ver acima).
4. **Mutação A:** a saída ficou com 1 failed e 6 passed, então confirma que o teste morde só no `config.py`.

## Preocupações

- **Avisos de CRLF:** o `git add` avisou que LF será convertido para CRLF nos arquivos novos. É configuração de `core.autocrlf` no Windows, não afeta o commit. Vale conferir se o repositório quer finais de linha uniformes antes da tarefa 2.
- **`.pytest_cache`:** o pytest criou `.pytest_cache/` na raiz e ele não está no `.gitignore`. Ele não entrou no commit, mas pode aparecer em um `git add -A` futuro. Sugiro acrescentar ao `.gitignore` numa tarefa posterior, ou agora se você preferir.
- **Testes parametrizados em skip:** enquanto `limpeza2/` não tiver módulos, os dois testes parametrizados ficam em skip, como já descrito. O teste de presença cobre esse caso, mas quem ler "2 skipped" deve saber que esses dois não cobrem nada naquele estado.

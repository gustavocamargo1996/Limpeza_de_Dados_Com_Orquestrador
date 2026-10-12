# Relatorio da Tarefa 5: limpeza2/motor.py, os cinco tipos de deteccao

**Status:** DONE_WITH_CONCERNS (uma prova por mutacao do brief nao morde; ver abaixo)

## O que foi implementado

- `limpeza2/motor.py` (43 linhas), copiado literalmente do brief: `TIPOS`, `detectar(df, coluna, tipo, parametros, dominancia=0.70)`, `moda_dominante`, `divergentes_da_moda`.
- `motor.py` nao importa nenhum modulo do repositorio, so `pandas`.
- `tests/test_motor_deteccao.py` (66 linhas), nove testes, copiados literalmente do brief.
- A assinatura e `detectar(df, ...)`, sobre a linha, nao sobre a celula.
- `moda_dominante` fica separada de `divergentes_da_moda`, para a tarefa 6 usar a mesma conta.

## TDD

RED: `.venv/Scripts/python -m pytest tests/test_motor_deteccao.py -v`

```
ERROR tests/test_motor_deteccao.py
E   ModuleNotFoundError: No module named 'limpeza2.motor'
1 error in 1.98s
```

Falha esperada: o modulo ainda nao existia.

GREEN: `.venv/Scripts/python -m pytest tests/test_motor_deteccao.py -v`

```
collected 9 items
tests\test_motor_deteccao.py .........                                   [100%]
============================== 9 passed in 0.87s ==============================
```

Suite completa depois do GREEN: `73 passed in 1.74s` (sem warnings).
Linha de base sem o arquivo novo: `64 tests collected`. O brief diz 62; a diferenca nao foi investigada alem disso, mas nao afeta a tarefa.

## Provas por mutacao (saida bruta do pytest, aparada com `tail`)

Cada mutacao foi feita sobre o arquivo e revertida a partir de uma copia em scratchpad. Depois da reversao, o `diff` deu identico.

### Mutacao A: `~serie.str.fullmatch(...)` -> `~serie.str.match(...)`. Resultado: MORDE.

```
tests\test_motor_deteccao.py F........                                   [100%]
FAILED tests/test_motor_deteccao.py::test_formato_marca_quem_nao_casa - asser...
E       assert [False, False...e, False, ...] == [False, True,...e, False, ...]
E         At index 1 diff: False != True
========================= 1 failed, 8 passed in 1.74s =========================
```

### Mutacao B: `continue` -> `pass` no grupo sem maioria clara. Resultado: MORDE.

Obs.: apagar a linha `continue` deixaria o `if` sem corpo, o que e erro de sintaxe. Por isso a mutacao troca `continue` por `pass`, que e a remocao efetiva do pulo.

```
FAILED tests/test_motor_deteccao.py::test_dependencia_marca_quem_diverge_da_moda_do_grupo
FAILED tests/test_motor_deteccao.py::test_dependencia_pula_grupo_sem_maioria_clara
FAILED tests/test_motor_deteccao.py::test_dependencia_pula_grupo_de_uma_linha
========================= 3 failed, 6 passed in 1.83s =========================
```

### Mutacao C (literal do brief): `numeros.notna() & fora` -> `fora`. Resultado: NAO MORDE.

```
=== MUTACAO C: notna() & fora -> fora ===
17:        return fora
collected 9 items
tests\test_motor_deteccao.py .........                                   [100%]
============================== 9 passed in 0.96s ==============================
```

Motivo: comparar NaN com numero da False no pandas. Verificado:
`fora para nao-numero: [False, False, False, True]` (para `N/A`, vazio, `Temperate`, `5`). Logo `fora` ja e False para qualquer nao-numero, e `numeros.notna() &` e redundante. A mutacao e equivalente, nao um defeito do teste. O brief afirmava que ela derrubaria `test_faixa_nao_marca_o_que_nao_e_numero`, e isso esta errado.

### Mutacao C2 (complementar, que de fato marca nao-numero): `numeros.notna() & fora` -> `~numeros.notna() | fora`. Resultado: MORDE.

```
tests\test_motor_deteccao.py ...F.....                                   [100%]
FAILED tests/test_motor_deteccao.py::test_faixa_nao_marca_o_que_nao_e_numero
E       assert not np.True_
E        +  where np.True_ = any()
========================= 1 failed, 8 passed in 1.28s =========================
```

Essa e a protecao real do teste. `motor.py` foi mantido exatamente como o brief pede, sem alterar o codigo para remover a redundancia.

## Orcamento (medido depois do `git add`, antes do commit)

- `git ls-files "*.py" ":!tests/" | wc -l`: **7** arquivos (teto 13; antes eram 6).
- `git ls-files "*.py" ":!tests/" | xargs wc -l | tail -1`: **446** linhas (teto 1.400; antes 403, +43).
- Maior arquivo: `medir.py` com 141 linhas (teto 200). `motor.py` tem 43.

## Commit

`6237242 motor.py: os cinco tipos de deteccao`, branch `fundacao-deterministica`, 2 arquivos (109 insercoes).
A mensagem do brief foi corrigida num ponto: dizia que as tres mutacoes derrubam o teste correspondente, o que nao e verdade para a literal C. A mensagem agora registra isso. A linha de atribuicao e `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`, como pedido.

## Arquivos alterados

- `limpeza2/motor.py` (novo)
- `tests/test_motor_deteccao.py` (novo)
- `.superpowers/sdd/2026-10-12-fundacao-deterministica/task-5-report.md` (este relatorio, fora do git por causa do `.gitignore`)

## Auto-revisao

- Sem `try`. A unica falha alta e o `raise ValueError(f"tipo de regra desconhecido: {tipo}")`.
- Docstrings de uma linha. Sem comentarios inline no motor.
- Sem acento em identificadores nem em strings de log.
- O `FutureWarning` da regex `"[["` nao aparece: o teste dessa regex nao existe nos nove testes do brief.
- Nenhum teste gasta API.

## Preocupacoes

1. **Mutacao C do brief esta errada.** Ela e equivalente, pois NaN comparado da False. Antes de ser usada como prova, o texto do brief deveria trocar por C2 (ou aceitar que a redundancia e inofensiva).
2. **Redundancia em `motor.py`.** `numeros.notna() &` nao muda o resultado, porque comparacoes com NaN ja dao False. A linha so documenta intencao. Nao alterei, pois o brief manda copiar literalmente.
3. **Contagem de testes.** O brief diz 62 testes na linha de base; medi 64. Vale conferir a origem.

---

## Rodada de correcao 1

Commit: `6e7c63f motor.py: correcoes da rodada 1 da tarefa 5`. Orcamento depois da rodada: 7 arquivos, 447 linhas, maior `medir.py` com 141.

### O que mudou

- **Importante (guarda de grupo de uma linha):** o guarda `if len(serie) < 2: return None` ficou, e foi acrescentado o teste direto `test_moda_de_grupo_de_uma_linha_e_none`, com `moda_dominante(pd.Series(["x"]), 0.70) is None`.
- **Menor 1 (clausula redundante):** em `faixa`, `return numeros.notna() & fora` virou `return fora`, com comentario de uma linha dizendo que comparacao com NaN ja da False. `test_faixa_nao_marca_o_que_nao_e_numero` foi mantido.
- **Menor 2 (fronteira da dominancia):** acrescentado `test_dependencia_aceita_dominancia_exata`, com 7 de 10 linhas iguais e dominancia 0,70. Afirma que a moda e `10:30` e que as 3 divergentes sao marcadas.
- **Menor 3 (trabalho desperdicado):** o ramo `dependencia` foi movido para o topo de `detectar`, e `serie = df[coluna].astype(str)` so roda para os outros tipos.

### Testes

GREEN de `tests/test_motor_deteccao.py`: `11 passed in 2.62s` (9 originais e 2 novos).
Suite completa antes do commit: `75 passed in 2.27s` (64 de base mais 11).

### Mutacoes da rodada (saida bruta do pytest, aparada com `tail`)

**M1: remover o guarda `if len(serie) < 2: return None`.** Resultado: MORDE, no teste novo.

```
tests\test_motor_deteccao.py .........F.                                 [100%]
___________________ test_moda_de_grupo_de_uma_linha_e_none ____________________
>       assert moda_dominante(pd.Series(["x"]), 0.70) is None
E       AssertionError: assert 'x' is None
========================= 1 failed, 10 passed in 1.71s =========================
```

**M2: reescrever a faixa na forma negada, `fora = ~((numeros >= minimo) & (numeros <= maximo))`.** Resultado: MORDE, em `test_faixa_nao_marca_o_que_nao_e_numero`.

```
tests\test_motor_deteccao.py ...F.......                                 [100%]
___________________ test_faixa_nao_marca_o_que_nao_e_numero ___________________
>       assert not m.any()
E       assert not np.True_
E        +  where any = 0    True\n1    True\n2    True\n3    True\n4    True\n5    True\n6    True\nName: zona, dtype: bool.any
========================= 1 failed, 10 passed in 1.63s =========================
```

**M3: `<` por `<=` na dominancia.** Resultado: MORDE, em `test_dependencia_aceita_dominancia_exata`.

```
tests\test_motor_deteccao.py ..........F                                 [100%]
__________________ test_dependencia_aceita_dominancia_exata ___________________
>       assert moda_dominante(serie, 0.70) == "10:30"
E       AssertionError: assert None == '10:30'
========================= 1 failed, 10 passed in 1.73s =========================
```

Em cada mutacao, `motor.py` foi restaurado a partir de uma copia e o `diff` deu identico. As mutacoes, o restauro e a suite final rodaram sobre o estado commitado.

### Preocupacoes da rodada

- As mutacoes da rodada 1 mordem; a equivalente C do brief continua sendo a unica que nao morde, e ja foi substituida pela forma negada na M2.
- A linha de base de 64 testes (brief: 62) continua sem explicacao alem da contagem medida.

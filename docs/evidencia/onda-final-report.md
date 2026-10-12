# Onda final: relatório

## O que mudou por achado
- **I1** `e3_crivo._reprovar_reparo(entrada, novo, reparada, proposta, mascara)`: filtra os pares pela coluna da candidata (mais determinantes em `moda_condicionada`) e exige `novo == limpo` em toda linha de par que esteja na máscara, sem consultar `reparada`. Testes novos: par intacto (`perde_par_do_guia`) e par de outra coluna não reprova. Entrada `#par-exige-valor-exato` em DECISOES (precisão a mais, recall a menos). Desvio menor: recebe `proposta` (de onde saem a coluna e os determinantes) em vez da coluna avulsa.
- **I2** `testar_fumaca` rejeita retorno que não seja `str`, com o tipo na mensagem. 3 testes (yield, None, lista).
- **I3** `test_motor_importa_so_o_permitido` com a constante `IMPORTS_PERMITIDOS_NO_MOTOR = {"pandas"}`.
- **I4** teste `..._limitacao_conhecida` e parágrafo em `#duas-medicoes`. Fórmula intocada.
- **5** DECISOES e spec: teste byte a byte declarado pendência da parte 2.
- **6** `DATASETS` removido de `config.py` (grep: nenhum módulo o lia).
- **7** `holdout` conta só a interseção com o índice do sujo; teste novo.
- **8** guarda morta removida de `linhas_do_guia`; teste de "pares só com cabeçalho" segue passando.
- **9** portão reprova `ast.Name` com `id` iniciado em `__`; caso novo na tabela parametrizada.
- **10** `"None": None` removido da allowlist.
- **11** `coluna_sujeito` declarada pendência da parte 2 (CLAUDE.md e spec); "quatro" -> "cinco" números (REGRAS e spec); ressalva do teto de 20 (DECISOES e spec).
- **12** limite de tempo/memória do portão registrado em DECISOES, junto da garantia por sondagem (mais um parágrafo sobre `corrigir -> str`).

## Mutações (saída bruta, trecho final do pytest)
I1(a) consultar `reparada` em vez da máscara:
```
E       AssertionError: assert [Reparo(candi... codigo=None)] == []
E         Left contains one more item: Reparo(... parametros={'mapa': {'YY': 'MA'}} ...)
tests\test_e3_crivo.py:215: AssertionError
FAILED tests/test_e3_crivo.py::test_crivar_reparo_reprova_quem_deixa_o_par_intacto
```
I1(b) sem filtro por coluna:
```
E       AssertionError: assert [] == [Reparo(candi...de_par_do_guia'}), estrategia='dicionario', ...)]
tests\test_e3_crivo.py:229: AssertionError
FAILED tests/test_e3_crivo.py::test_crivar_reparo_ignora_par_de_outra_coluna
```
I2 sem checagem de tipo:
```
E       Failed: DID NOT RAISE CodigoRejeitado
tests\test_portao.py:105: Failed
FAILED tests/test_portao.py::test_fumaca_rejeita_o_que_nao_devolve_str[yield valor]
FAILED tests/test_portao.py::test_fumaca_rejeita_o_que_nao_devolve_str[return None]
FAILED tests/test_portao.py::test_fumaca_rejeita_o_que_nao_devolve_str[return [valor]]
```
I3 `from limpeza2 import config` em motor.py:
```
E         Extra items in the left set:
E         'limpeza2'
tests\test_vazamento.py:63: AssertionError
FAILED tests/test_vazamento.py::test_motor_importa_so_o_permitido - Assertion...
```
I3 `import os`:
```
E         Extra items in the left set:
E         'os'
tests\test_vazamento.py:63: AssertionError
FAILED tests/test_vazamento.py::test_motor_importa_so_o_permitido - Assertion...
```
7 contar `len(holdout)` como antes:
```
>       assert r["holdout"] == 2
E       assert 4 == 2
FAILED tests/test_medir.py::test_holdout_publicado_conta_so_indice_existente
```
9 sem a checagem de `ast.Name`:
```
E       Failed: DID NOT RAISE CodigoRejeitado
tests\test_portao.py:57: Failed
FAILED tests/test_portao.py::test_rejeita_codigo_proibido[def corrigir(valor):\n    __builtins__.clear()\n    return valor\n-nome dunder proibido]
```
I4 e 8: sem mutação pedida (I4 documenta comportamento; em 8 o teste existente seguiu verde sem a guarda).

## Suíte
`146 passed in 4.70s` (137 + 9), sem seção de avisos.

## Orçamento
9 arquivos `.py` fora de tests, 817 linhas, maior 159 (`limpeza2/motor.py`).

## Não aplicado / ressalvas
- Nada deixou de ser aplicado.
- I1: incluir as colunas determinantes na verificação é mais estrito, não mais frouxo: um par numa coluna determinante, em linha marcada, exige que o reparo o conserte. Segui o texto da instrução; vale revisar quando o codificador existir.
- Um `python -` com heredoc vazio, por engano meu, pendurou um shell em segundo plano; foi encerrado.

## Correção posterior: determinante só responde onde escreveu

A instrução original incluía as colunas determinantes sem condição; isso reprovava reparo válido (par em `cidade`, linha marcada em `estado`, reparo que conserta só `estado`). Agora a coluna-alvo vale sempre e a determinante só onde `novo` difere do sujo. Testes novos: `..._nao_responde_por_determinante_que_nao_escreveu` (aprova) e `..._responde_por_determinante_que_escreveu_valor_errado` (reprova).

Mutação, determinante sem condição (`if False and ...`):
```
E         Right contains one more item: Reparo(candidata=Candidata(coluna='estado', ...), estrategia='moda_condicionada', parametros={'determinantes': ['cidade']}, ...)
tests\test_e3_crivo.py:256: AssertionError
FAILED tests/test_e3_crivo.py::test_crivar_reparo_nao_responde_por_determinante_que_nao_escreveu
```
Mutação, sem coluna-alvo (`colunas = set()`):
```
tests\test_e3_crivo.py:215: AssertionError
FAILED tests/test_e3_crivo.py::test_crivar_reparo_reprova_quem_repara_o_par_para_o_valor_errado
FAILED tests/test_e3_crivo.py::test_crivar_reparo_reprova_quem_deixa_o_par_intacto
```

Suite final: 148 passed in 1.79s, sem avisos. Orcamento: 9 arquivos, 821 linhas, maior 159.

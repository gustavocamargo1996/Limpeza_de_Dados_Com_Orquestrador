# Task 7 - e5_residual

Implementado `limpeza2/e5_residual.py` (117 linhas) e `tests/test_e5_residual.py` exatamente como o brief, com dois ajustes:
1. Teste `test_resolver_ignora_null_igual_e_valor_nao_pedido`: o brief pegava a primeira nota com unidade `coluna_sujeito`, mas `pedir_json` ja grava uma nota `ok` com detalhe vazio. O filtro virou `n["status"] == "escolha"` (a nota que o brief especifica).
2. Teste novo `test_lote_exatamente_cheio_ainda_cabe` (LINHAS_POR_LOTE=5): a mutacao `<=` -> `<` sobrevivia aos testes do brief.

TDD: RED (ImportError na coleta), GREEN apos implementar e ajustar o teste.
Mutacoes: as 8 falham o teste nomeado (m1 falha tambem o de lote cheio); m2 (`<=`->`<`) sobreviveu ate o teste novo, depois falha.
Medidas: 15 arquivos .py de producao, 1589 linhas, maior 193 (e3_crivo/motor); e5 tem 117. Suite: 252 passed. Commit 93d22dd.
Arquivos: limpeza2/e5_residual.py, tests/test_e5_residual.py.
Concerns: o brief tinha a inconsistencia teste/implementacao acima; o residual sai sem crivo (espinha chama crivar_residual).

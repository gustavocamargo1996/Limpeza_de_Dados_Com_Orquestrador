# Tarefa 1 - relatorio

Implementado: `reparar` simplificado (+ `_escalar`) e `aplicar_regras` em `limpeza2/motor.py` (193 linhas), codigo do brief verbatim.
RED: `test_reparada_so_conta_valor_que_mudou` falhou com `assert not np.True_`; `test_motor_aplicar.py` falhou com ImportError (funcao renomeada temporariamente).
GREEN: suite 194 passed (188 apos Step 2/3, sem falha em teste antigo).
Mutacoes (6/6 morderam, revertidas): 1 -> test_reparada_so_conta_valor_que_mudou (tambem derrubou test_esvaziar_nao_conta_celula_ja_vazia); 2..6 -> o teste nomeado no brief, e so ele.
Arquivos: limpeza2/motor.py, tests/test_motor_reparo.py, tests/test_motor_aplicar.py.
Medida: motor.py 193 linhas.
Concerns: o brief sugeria trailer "Claude Opus 5.5"; usei "Claude Sonnet 5.5" conforme a regra de atribuicao do ambiente.

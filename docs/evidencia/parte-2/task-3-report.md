# Relatorio da tarefa 3

Implementado verbatim do brief: bloco do provedor em `limpeza2/config.py`, `.env.exemplo`, `limpeza2/provedor.py` (150 linhas), dubles `ok`, `CORTADA`, `Roteiro`, `em_fila` em `tests/apoio.py`, fixture `roteiro` em `tests/conftest.py`, `tests/test_provedor.py` (15 casos).

RED: `pytest tests/test_provedor.py` -> ImportError (`cannot import name 'provedor' from 'limpeza2'`). GREEN: suite completa passa (218).

Mutacoes (uma por vez, revertidas): as 8 do brief derrubaram, respectivamente, test_provedor_desconhecido_falha_alto (falhou por erro do SDK sem chave, nao por assercao), test_falha_vira_falha_do_llm_com_motivo[cortada], [json_invalido do 1,2], test_autenticacao_nao_degrada, test_teto_de_chamadas, test_gravado_reproduz_a_geracao_na_mesma_ordem, test_gravado_sem_a_resposta_levanta, test_parametro_none_sai_do_pedido.

Medidas: 10 arquivos .py de producao, 1.161 linhas, maior 193. Commit d637901.
Concerns: o brief previa 11 arquivos; contagem real 10 (a tarefa 3 soma provedor.py a 9 existentes). Mutacao 1 falha por exception do SDK e nao por ValueError ausente, mas o teste morde.

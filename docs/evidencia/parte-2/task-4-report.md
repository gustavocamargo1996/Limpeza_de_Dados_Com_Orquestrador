# Relatorio da tarefa 4: e2_detector

Implementado `limpeza2/e2_detector.py` (130 linhas, codigo do brief verbatim) e contagens `int` em `e1_perfil.py`.
Commit 46a5902. Testes: 220 + 1 (e1) + 8 (e2) = 229 passam. Arquivos .py de producao: 12 (o brief previa 12; wc: 11 listados antes do add -N), 1.291 linhas ao todo, maior 193.

TDD: e2 RED = ImportError na coleta, GREEN apos implementar.
Ressalva: o teste novo de e1 JA passava antes da troca para int (nesta versao do pandas `.items()` ja entrega int), entao nao houve RED observado; a troca foi feita como o brief manda.

Mutacoes (as 7 do brief, uma por vez, todas falharam o teste nomeado, revertidas): catalogo/formato, catalogo/det, caso/vacua, _valida/minimo<=maximo, por_tipo/VARIANTES, tipos->CAMPOS, continue->return.
Incidente: a primeira execucao do script de mutacao quebrou (caminho do python) deixando a mutacao 1 aplicada; restaurei manualmente e rerodei tudo; suite final verde.
Arquivos: limpeza2/e1_perfil.py, limpeza2/e2_detector.py, tests/test_e1_perfil.py, tests/test_e2_detector.py.

# Tarefa 9 - relatorio
Implementado limpeza2/espinha.py (verbatim do brief), tests/test_espinha.py (3 testes), 1 teste novo em tests/test_vazamento.py.
RED: ImportError (sem limpeza2.espinha). GREEN: testes passam apos criar espinha.py.
Mutacoes: M1 e M2 falham test_gera_limpador_que_o_medir_mede. M3 (leitura do limpo em e1_perfil._ler_guia) falha test_geracao_so_abre_o_sujo_o_guia_e_o_motor (e tambem test_nenhum_modulo_cita_arquivo_csv[e1_perfil.py]). M4 (datetime.now() no cabecalho) falha test_mesma_geracao_mesmo_limpador (e tambem os outros 2 de test_espinha, pois o cabecalho deixa de ser valido para o fluxo). Todas revertidas (git status limpo).
Medidas: 16 arquivos; 1772 linhas; maior 200 (e6_codificador.py).
Suite final: 277+ passed (ultima linha da execucao sem falhas).
Preocupacao: folga de arquivos zero; e6_codificador no teto de 200 linhas.

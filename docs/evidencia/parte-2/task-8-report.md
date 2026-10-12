# Relatorio da tarefa 8

Status: DONE. Commit 555e45f.

- Implementado: `e6_codificador.escrever`, `renomear`, `MOTOR/INICIO/FIM`, RODAPE, `_limpador`, `_cabecalho`, `_raciocinio` (codigo do briefing); `medir.avaliar` devolve `truncada` e `degradadas`, `main` avisa.
- RED: 7 testes novos do e6 (AttributeError) e 2 do medir (KeyError 'truncada'). GREEN: suite inteira passa (266 + 9 novos = 275).
- Mutacoes (todas fizeram o teste nomeado falhar, depois revertidas): sem newline="" -> byte_a_byte; RESIDUAL como repr(set) -> falha; GERACAO_TRUNCADA=False -> teto_atingido; sem a fumaca final -> funcao_quebrada; iterar reparo_de -> raciocinio_lista; sem o print -> limpador_truncado_e_avisado.
- Linhas: e6_codificador.py 200 (limite); medir.py 143; producao 15 arquivos, 1731 linhas.
- O codigo do briefing dava 203 linhas. Ficou em 200 so por: juntar `+=` consecutivos em `_raciocinio` (residual e "outras anotacoes") e inlinar a variavel `motor` em `_limpador` (comportamento identico). Nao usei template de string (testado: ficava maior).
- Concerns: e6_codificador.py esta no teto exato de 200 linhas, sem folga.

## Rodada de correcao 1

- Residual: `test_limpador_aplica_regras_e_residual` usa tabela com "16oz" (marcado pelo dominio, funcao nao muda) e afirma fontes `["", "dominio/normalizar", "residual", ""]`. Mutacao RESIDUAL vazio: teste falha.
- Avisos: novo `test_cabecalho_avisa_do_portao_e_da_memoria_congelada` e linha do teto no .md no teste do teto. Mutacoes (SEM->COM, "Memoria congelada:", `teto de chamadas: 0`): as tres falham o teste nomeado.
- Refatoracao: teto calculado uma vez em `escrever`; `cliente.chamadas`/`cliente.registro` passados adiante; `+=` e variavel `motor` restaurados. Resultado 201 linhas; para chegar a 200 inlinei a variavel `celulas` (uso unico) no f-string do .md (linha longa). Julgue se isso e aceitavel.
- Saida: pytest dos dois arquivos 28 passed (sem erro); suite completa toda verde; e6_codificador.py = 200 linhas.

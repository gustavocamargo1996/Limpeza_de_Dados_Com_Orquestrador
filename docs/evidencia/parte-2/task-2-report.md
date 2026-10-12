# Relatorio da tarefa 2

Status: DONE. Commit f5bd4e7. Suite: 203 passed (197 apos o passo 4, 203 apos o passo 6).

Implementado: tests/apoio.py (monta_entrada movida sem mudanca), tipos.regras_literais e Residual.caidas,
limites.guia_na_coluna/exemplos_do_guia (teto_da_coluna e celulas_sujas_do_guia refatoradas),
e3_crivo._celulas_certas via guia_na_coluna, e3_crivo.crivar_residual, tests/test_tipos.py, 7 testes novos no crivo.

TDD: RED de test_tipos (ImportError regras_literais) e de test_e3_crivo (ImportError crivar_residual, obtido
renomeando a funcao temporariamente, pois a implementacao ja estava escrita). GREEN apos implementar.
Passo 4 (refatoracao): suite existente passou sem mudanca.

Mutacoes (todas derrubaram o teste nomeado, revertidas): as 7 da tabela (a 1a em duas metades: indice e busca).
Incidente: o 1o script de mutacao falhou ao lancar o pytest e deixou a mutacao 1 em tipos.py; revertida a mao e
repetida; arvore final limpa, 203 passed.

Linhas (producao): tipos.py 70, limites.py 46, e3_crivo.py 193 (<=200). Total do projeto: motor 193 e e3 193 sao os maiores.
Conferencia da frase de tipos.py: "o que viaja entre as etapas, ate o limpador gerado" cobre regras_literais
(forma literal que viaja ao limpador); mantida em tipos.py. Efeito: tipos importa motor.TIPOS (sem ciclo; motor nao importa tipos).

Concerns: nenhum. Aviso de LF/CRLF do git nos arquivos novos, inofensivo.

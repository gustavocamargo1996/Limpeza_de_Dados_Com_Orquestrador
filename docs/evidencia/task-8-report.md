# Relatório da Tarefa 8: `limpeza2/e3_crivo.py`

## Implementado
`limpeza2/e3_crivo.py` (125 linhas) e `tests/test_e3_crivo.py`, transcritos do brief (extraídos por `sed` das linhas do brief, sem retranscrição manual). Dois `try`, ambos com degradação nomeada (`lancou`). `metricas` é preenchido em toda candidata. A ordem dos testes em `_reprovar` é a do brief.

## Testes
- `tests/test_e3_crivo.py`: **14 passed**. O brief diz 15; a contagem real do arquivo do brief é 14 (9 testes simples + 2 parametrizados de `sem_perfil` + 3 de reparo). Erro de contagem no brief, não na transcrição: todos os testes listados estão presentes.
- Suíte inteira: **134 passed**.

## TDD
- RED: `pytest tests/test_e3_crivo.py -q` sem o módulo: `ModuleNotFoundError: No module named 'limpeza2.e3_crivo'` na coleta (esperado, o módulo não existia). Nota de honestidade: rodei antes uma vez, por engano, com o módulo já presente; removi o módulo e refiz o RED limpo.
- GREEN: com o módulo, `14 passed`.

## Provas por mutação (as sete, executadas por script que reescreve o arquivo, roda o pytest e restaura; `cmp` final confirmou restauração)
```
=== Mutacao A | if candidata.metricas["marcadas"] == 0: => if False:
.F............
FAILED tests/test_e3_crivo.py::test_reprova_regra_vacua
=== Mutacao B | > config.TETO_MARCACAO => > 1.1
..F...........
FAILED tests/test_e3_crivo.py::test_reprova_regra_que_marca_a_coluna_inteira
=== Mutacao C | bloco toca_linha_limpa de _reprovar => (removido)
...F..........
FAILED tests/test_e3_crivo.py::test_reprova_regra_que_toca_linha_limpa_do_guia
=== Mutacao D | not bool(mascara.loc[alvos].all()) => False
....F.........
FAILED tests/test_e3_crivo.py::test_reprova_regra_que_perde_par_do_guia
=== Mutacao E | par["frac_ambiguos"] > config.TETO_AMBIGUIDADE => > 2.0
......F.......
FAILED tests/test_e3_crivo.py::test_reprova_dependencia_ambigua
=== Mutacao F | taxa < anterior => taxa > anterior
........F.....
FAILED tests/test_e3_crivo.py::test_entre_variantes_fica_a_que_marca_menos
=== Mutacao G | .get(...) + if None => .get(..., {"frac_ambiguos": 0.0}) sem o if
..........F...
FAILED tests/test_e3_crivo.py::test_reprova_dependencia_sem_perfil[sem_entrada]
```
Todas as sete mordem, e cada uma no teste previsto. Observação: o texto da mutação E no brief fala em `par.get("frac_ambiguos", 0.0)`, mas o código do brief usa `par["frac_ambiguos"]`; apliquei a mutação equivalente sobre o código real.

## Orçamento
Arquivos `.py` fora de `tests/`: 9 (teto 13). Linhas: 810 (teto 1.400). Maior arquivo: `motor.py` com 159 (teto 200); `e3_crivo.py` tem 125.

## Arquivos alterados
Criados: `limpeza2/e3_crivo.py`, `tests/test_e3_crivo.py`. Editados: `CLAUDE.md` e `docs/superpowers/specs/2026-10-11-geracao-de-limpador-design.md` (`metricas_crivo` virou `metricas`, que é o nome real em `tipos.py`; o código ganha). Commit `f1c8cd3`.

## Auto-revisão
- `crivar_reparo` chama `detectar` fora do `try`: se a detecção lançar ali, a exceção sobe. Só acontece se a candidata já tiver passado no crivo de detecção (que a executou), então é inalcançável no fluxo normal; mantido por obediência ao brief e ao limite de dois `try`.
- A guarda do reparo fora da máscara compara só as linhas do guia, não todas as linhas fora da máscara; é o que o brief especifica.
- `taxa` usa `len(sujo)`; tabela vazia daria divisão por zero (fora de escopo).

## Preocupações
- Contagem do brief (15 vs 14), acima.
- Avisos de LF/CRLF do git no Windows; sem efeito nos testes.
- Um processo Python interativo ficou em loop por um erro meu de heredoc (comando em background); não consegui encerrá-lo pelo PowerShell (bloqueado pelo classificador) e ele escreveu um arquivo de saída grande no diretório de tool-results da sessão. Vale encerrar manualmente se estiver consumindo CPU.

# Rodada de correcao 1

Mudancas: (I1) o caso `composto` agora tem `("cidade","estado")` no perfil com `frac_ambiguos` 0.0, e o caso `sem_entrada` limpa os pares; (I2) novos testes `perde_par_do_guia` do reparo (dicionario `XX -> TX`, par espera `MA`) e `lancou` do reparo (`normalizar` com funcao que levanta); (M1) `detectar` de `crivar_reparo` movido para dentro do `try` existente, sem `try` novo; (M2) variantes com a ordem invertida e novo teste de `marca_demais` com taxa 0,5 (valores `["MA"]`); (M3) comentario de 3 linhas reduzido a 2 e `_reprovar_reparo` importado no topo.

Testes: tests/test_e3_crivo.py 17 passed. Suite completa: 137 passed. Orcamento: 9 arquivos, 810 linhas.

## Mutacoes (saida bruta; arquivo restaurado e conferido com cmp)
```
=== Mutacao H (Importante 1) remove a ramificacao de len
..........F......
FAILED tests/test_e3_crivo.py::test_reprova_dependencia_sem_perfil[composto]
=== Mutacao I (Importante 2) apaga o laco do par no reparo
...............F.
FAILED tests/test_e3_crivo.py::test_crivar_reparo_reprova_quem_repara_o_par_para_o_valor_errado
=== Mutacao J (Importante 2) remove o try de crivar_reparo (except vira KeyboardInterrupt)
................F
FAILED tests/test_e3_crivo.py::test_crivar_reparo_reprova_estrategia_que_lanca
=== Mutacao K (Menor 2) a ultima ganha
........F........
FAILED tests/test_e3_crivo.py::test_entre_variantes_fica_a_que_marca_menos
=== Mutacao L (Menor 2) teto de marcacao 0.30 -> 0.6
.........F.......
FAILED tests/test_e3_crivo.py::test_reprova_taxa_acima_do_teto_sem_ser_a_coluna_inteira
```
Todas mordem. Nota: a mutacao K passa a falhar so por causa da ordem invertida (a versao anterior do teste nao a pegava).

Nota (aviso do pytest): a regex invalida de `test_reprova_regra_que_lanca` passou de `"[["` para `"("` (subpadrao nao terminado). O caso continua reprovando com motivo `lancou` (teste passa) e a suite completa roda sem aviso: `137 passed in 2.49s`, sem secao de warnings.

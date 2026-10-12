# Relatorio da Tarefa 3: medir.py

## Implementado
`medir.py` (140 linhas) copiado do brief literalmente; seis arquivos copiados da POC 1 (somente leitura) para `tests/fixtures/`; `tests/test_medir.py`.

## Testes
`pytest tests/test_medir.py`: 5 passed (o brief diz 6, mas o parametrize gera 2 + 3 = 5 testes; nao falta nenhum). Suite completa passa.
O placar da POC 1 foi reproduzido exatamente (beers 495/121/121/71 flags, environment 334/44/44/663), sem ajuste de numeros.

## TDD
- RED: `pytest tests/test_medir.py` -> `ModuleNotFoundError: No module named 'medir'` (esperado: modulo ainda nao existia).
- GREEN: apos criar `medir.py`, `5 passed`.

## Provas por mutacao
- A (`tp = int(mudanca.sum())`): FALHOU `test_f1_reparo_conta_so_a_mudanca_que_acertou`. **`test_reproduz_o_placar_da_poc_1` NAO falhou**: nos limpadores congelados mudancas == tp (121/121, 44/44), entao a mutacao e invisivel ao placar. O brief previa que falharia; a previsao estava errada. A formula de precisao fica travada so pelo teste unitario. Revertido.
- B (`manter = sujo.index`): FALHOU `test_holdout_reduz_os_erros_contados` (`assert 495 ...`). Revertido; suite verde de novo.

## CLI (Step 7, guia do beers)
TOTAL: erros 478 (menor que 495), mudou 115, TP 115, precisao 100%, recall 24,1%, F1 38,8%, flags 69.
`holdout: 12 linhas fora da metrica` (5 linhas limpas + linhas dos pares, unioes).
Colunas: ounces 288 erros / 0 mudancas; ibu 108/108/100%; state 7 erros, 6 acertos.

## Orcamento
4 arquivos .py fora de tests/ (teto 13), 297 linhas (teto 1400), maior 140 (teto 200).

## Auto-revisao / preocupacoes
- A decomposicao por `fontes` nao tem exercicio: os limpadores congelados so tem `aplicar`. So produz numero quando a parte 2 gerar `aplicar_detalhado`.
- Mutacao A fraca no teste de integracao (acima); sugiro um teste com limpador que erra algo, se quiser travar a precisao no placar.
- Fixtures .py da POC 1 emitem UserWarning de regex; sao inofensivos e vem do codigo congelado.
- `linhas_do_guia` le sem LER_CSV de proposito (indice inteiro); nao alterado.

---

# Rodada de correcao 1

## O que mudou
- `medir.py`: `catch_warnings` saiu de `carregar` e passou a envolver carga e aplicacao do limpador em `avaliar` (onde os avisos nascem); comentario nomeia SyntaxWarning (import) e UserWarning (aplicar).
- `tests/test_medir.py`: 11 testes (eram 5). Novos: limpador minimo em `tmp_path` (acerta a1 e b4, erra a1 de proposito, 1 flag, `aplicar_detalhado` com fontes) cobrindo agregacao com precisao 2/3 e recall 2/5, fonte so conta se acertou (`{"regra1": 2}`), holdout em totais e fontes; 3 testes de `linhas_do_guia` (tipo inteiro via `numbers.Integral`, pares so com cabecalho, arquivos ausentes). Holdout do beers agora afirma 495 vs 491 erros (119 mudancas).

## Execucao
`.venv/Scripts/python -m pytest tests/test_medir.py` -> `11 passed in 1.64s`, sem bloco de warnings (antes eram 6 UserWarning).

## Provas por mutacao (executadas)
- LER_CSV em `guia_linhas.csv`: FALHARAM `test_linhas_do_guia_devolve_inteiros` e `test_linhas_do_guia_pares_so_com_cabecalho`.
- `n_mud += m["tp"]`: FALHARAM `test_total_soma_acertos_e_erros_com_limpador_que_erra` e `test_holdout_respeitado_em_totais_e_fontes`.
- filtro `acertou` invertido (`~acertou`): FALHARAM `test_fonte_so_conta_quando_a_alteracao_acertou` e `test_holdout_respeitado_em_totais_e_fontes`.
Todas revertidas (cmp identico ao backup).

## Orcamento
5 arquivos .py fora de tests/ (incl. os da tarefa 1-2), 297 linhas, maior 140.

## Preocupacoes
Nenhuma nova. O ramo `aplicar_detalhado` agora e exercitado so por limpador sintetico; a fixture congelada continua sem ele.

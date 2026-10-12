# Relatorio: guia-do-limpo

## O que mudou
- `preparar_guia.py`: `sortear` sorteia entre todas as linhas e toma os valores do `limpo` (comentario velho removido). CLI ganhou `--linhas`, `--pares`, `--destino`. `gravar` escreve `guia_receita.txt` (dataset, semente, linhas, pares_por_coluna).
- Assinatura nova: `gravar(dataset, sujo, limpo, semente, n_linhas, pares_por_coluna, destino=None)` -> `(caminho_linhas, caminho_pares, n_linhas, n_pares)`; pasta = `config.GUIA / (destino or dataset)`.
- `limpeza2/e3_crivo.py`: `toca_linha_limpa` virou `marca_celula_correta` (por celula, so na coluna da candidata, helper `_celulas_certas`); novo `corrompe_celula_do_guia` (helper `_escreveu_errado_no_guia`). O antigo `toca_linha_limpa` do reparo foi SUBSTITUIDO por `corrompe_celula_do_guia`, nao somado: manteria reprovando reparo que corrige celula errada do guia. Ele e subsumido pelo novo (em celula certa, guia == sujo, logo escrever = valor diferente do guia). Ordem dos motivos inalterada (a verificacao ocupa o mesmo lugar, primeiro).
- Testes: `test_preparar_guia.py` reescrito (8 testes); `test_e3_crivo.py` +6 e 2 renomeados/ajustados; `monta_entrada` ganhou `corrigidos`.
- Docs: CLAUDE.md §1, REGRAS_DO_LIMPADOR §3, §5, §6, §7, §8, DECISOES `#guia-sorteado` e a linha do crivo. A §9 do CLAUDE.md nao mencionava `toca_linha_limpa` nem `gravar`.
- Guias canonicos regenerados e commitados, com `guia_receita.txt` (nao esta na allowlist de CSV; teste de vazamento passa).

## Provas por mutacao (todas executadas; saidas completas na sessao, trechos-chave)
Preparar guia:
- M1 `limpo.loc` -> `sujo.loc`: `FAILED test_linhas_do_guia_tem_os_valores_do_limpo` (1 failed, 7 passed; Denvr != Denver).
- M2 filtro antigo (so linhas sem erro): 4 failed (valores_do_limpo, pede_mais_linhas, sempre_ha_o_numero_pedido, gravar_escreve_a_receita).
- M3 receita sem semente: `FAILED test_gravar_escreve_a_receita...`.
- M4 `destino` ignorado: `FAILED test_gravar_escreve_a_receita...` (FileNotFoundError).
- M5 semente tirada dos pares / M5b das linhas: `FAILED test_a_mesma_semente_da_o_mesmo_guia` (1 failed, 7 passed) nos dois.
Crivo:
- D1 "qualquer marca em linha do guia reprova": `FAILED test_aprova_regra_que_marca_so_celula_errada_do_guia` (1 failed, 26 passed).
- D2 sem guarda de coluna ausente: `FAILED test_controle_negativo_so_olha_a_coluna_da_candidata` (KeyError: 'estado').
- D3 `==` -> `!=`: 2 failed (marca_celula_correta e aprova_so_errada).
- D4 sem controle: `FAILED test_reprova_regra_que_marca_celula_correta_do_guia` (marca_demais != marca_celula_correta).
- R1 sem verificacao de corrupcao: 3 failed (guarda_contra_reparo_fora_da_mascara, escreve_valor_errado_no_guia, escreve_em_celula_certa_do_guia).
- R2 "nao escrever tambem reprova": `FAILED test_crivar_reparo_aprova_quem_nao_toca_celula_errada_do_guia` (1 failed, 26 passed).
- R3 mascara `escreveu` invertida: 4 failed.
- R4 "qualquer escrita no guia reprova": `FAILED test_crivar_reparo_aprova_quem_escreve_valor_certo_no_guia` (1 failed, 26 passed).

## Guias regenerados (semente 20261011)
| Dataset | Linhas | Pares | Celulas rotuladas | Celulas sujas no CSV sujo |
|---|---|---|---|---|
| beers | 20 | 10 | 220 | 35 (ounces 20, abv 7, ibu 8; as 20 linhas tem erro) |
| environment | 20 | 14 | 220 | 18 em 13 linhas (Measurement_Date 5, Climate_Zone 4, Monitoring_Station_ID 3, ...) |

Hipotese refinada: `ounces` esta suja em 20 de 20 linhas (confirmado), mas o total no `beers` e 35 de 220 (16%), nao "alto" em termos absolutos; abv e ibu contribuem. Guia de teste `--linhas 10 --destino beers_l10` gerou 10 linhas/10 pares com receita correta; pasta apagada.

## Testes
`156 passed in 3.11s` (era 148); tambem com `-W error`, sem secao de avisos. Nenhum teste pulado.

## Orcamento
9 arquivos `.py`, 839 linhas, maior 159 (motor.py); e3_crivo.py 146.

## Preocupacoes
- A suposicao de que linhas do guia sao "certas" (`sujo == guia`) so vale por celula; um par `sujo -> limpo` pode cair numa linha do guia (inofensivo, mas redundante).
- `git add` avisa que os `guia_receita.txt` serao CRLF (autocrlf do Windows); conteudo e LF.
- O passo 5 (residual) ainda nao existe; a regra da doc (nenhuma entrada escreve valor diferente do guia) esta so na documentacao.
- Resultados antigos de medicao (se houver) nao sao comparaveis: o guia mudou e o holdout muda (as 20 linhas agora sao outras).

# Parte 2: teto de marcacao por coluna
- `limpeza2/e3_crivo.py`: nova `teto_da_coluna(entrada, coluna)` = `max(TETO_MARCACAO, suja + 2*sqrt(0.25/n))`; guia vazio ou sem a coluna devolve exatamente `config.TETO_MARCACAO`. `_mascara` grava `candidata.metricas["teto"]` (float) e `_reprovar` compara a taxa com ele. Sem `try` novo.
- Verificado nos guias reais (so sujo + guia): beers ounces 1.224 (98% passa), abv 0.574, ibu 0.624, demais 0.30; environment State 0.324 (a regra de 300/300 continua morrendo), Climate_Zone 0.424, Measurement_Date 0.474; guia vazio: 0.3 em todas as colunas.
- Testes: +7 (163 passed, tambem com -W error). Os 156 anteriores seguiram verdes sem alteracao (guia vazio => 0,30).
- Mutacoes: T1 teto fixo: 3 failed (teto_sobe..., margem_alarga..., margem_diminui...). T2 sem max: 2 failed (guia_quase_limpo..., guia_sem_sujeira...). T3 sem margem: 3 failed (inclui margem_alarga_o_teto). T4 margem constante 0.2: 2 failed (teto_sobe, margem_diminui). T5 guia vazio devolve 0: 8 failed.
- Orcamento: 9 arquivos, 853 linhas, maior 160 (e3_crivo.py).
- Docs: DECISOES `#teto-de-marcacao` reescrita (com a nota de que a verificacao usou o gabarito), REGRAS secao 5 (tabela de taxas) e linhas 198/283.
- Preocupacoes: o guia agora tambem supervisiona o teto, e um guia azarado pode soltar o teto de coluna limpa (Climate_Zone: guia 0.20, real 0.09, teto 0.42). `DET_MINIMO` continua amarrado ao a priori de 30% (nao ao teto por coluna): coluna muito suja ainda nao ganha dependencia; vale decidir depois.

# Parte 3: veto por valor certificado, uniao por coluna, simetria do guia
- Veto (`marca_valor_certificado`, em `_reprovar` logo apos `marca_celula_correta`, antes de `vacua`): so tipos formato/dominio/faixa/ausente_disfarcado; igualdade de valor com os valores do guia na coluna. Posicao: mesma natureza de evidencia direta de falso positivo. Nenhum teste existente mudou de motivo.
- Uniao (`uniao_acima_do_teto`, `_limitar_uniao`): descarta do maior para o menor taxa ate a uniao caber no teto; empate por ordem alfabetica do tipo; grava `taxa_uniao`.
- Simetria: `_sujas_do_guia` soma as celulas do guia com sujo != guia (coluna-alvo) ao piso do par, motivo `perde_par_do_guia`; o teste "aprova quem nao toca celula errada do guia" mudou de comportamento POR DESENHO e virou "reprova quem deixa intacta celula suja do guia" (perde_par_do_guia).
- Testes: 172 passed (-W error). Mutacoes (todas executadas): V1 sem veto -> 1 failed (test_veta_regra...); V2 veto em dependencia -> 1 failed (test_dependencia_pode_marcar_valor_certificado); V3 substring -> 1 failed (test_veto_compara_valor_inteiro...); U1 nao descarta -> 2 failed; U2 descarta menor taxa -> 1 failed (test_uniao_acima_do_teto_descarta_o_tipo_de_maior_taxa); U3 sem desempate -> 1 failed (test_empate_de_taxa_nao_depende_da_ordem); S1 sem celulas sujas -> 1 failed (reprova_quem_deixa_intacta_celula_suja); S2 ignora mascara -> 1 failed (aprova_celula_suja_do_guia_fora_da_mascara).
- Guias reais (sujo + guia, sem gabarito): ounces certificados {12, 16}; regra precisa (formato `12|16|8\.4` e dominio equivalente) marca 295, teto 1.224 -> APROVADA; degenerada (dominio vazio) marca 300 -> VETADA `marca_valor_certificado`. environment State: degenerada vetada por `marca_celula_correta` (teto 0.324); a regra `[A-Z]{2}` marca 0 (vacua), pois State ja tem duas letras.
- Docs: DECISOES (#guia-sorteado, #par-exige-valor-exato, #teto-de-marcacao com ressalva dois datasets/uma semente, secao nova dos dois testes), REGRAS secao 5, spec (guia, motivos, teto, gravar). Plano intocado. Comentario historico do teste removido.
- ORCAMENTO: e3_crivo.py esta em 199 de 200 linhas (total 892 em 9 arquivos). Qualquer acrescimo estoura; a proxima mudanca precisa separar parte (por ex. as funcoes de teto/veto/uniao) -- decisao sua, nao fracionei.

# Parte 4: extracao de limites.py
- Novo `limpeza2/limites.py` (39 linhas): `teto_da_coluna`, `valores_certificados`, `taxa_da_uniao`, `celulas_sujas_do_guia`. So olham Entrada e coluna (ou mascaras). `e3_crivo.py` importa deles (169 -> 179 com `_escreveu_errado_no_guia`, que decide sobre o reparo, ficou no crivo). `_marca_valor_certificado` e `_limitar_uniao` ficaram no crivo (decisao), chamando as de limites.
- Unica mudanca em testes: o import de `teto_da_coluna` (agora de `limpeza2.limites`). Nenhum comportamento mudou.
- Suite: `174 passed` com `-W error`: os mesmos 172 mais 2 instancias que `test_vazamento` gera sozinho para o modulo novo (parametrizado por arquivo de `limpeza2/`).
- Orcamento: 10 arquivos, 218 linhas em e3_crivo+limites; total do projeto = ver abaixo; maior arquivo e3_crivo.py 179.
- CLAUDE.md §9 e spec: arvore com `limites.py`; a arvore planejada passa a ter 15 arquivos, no limite de §2, sem folga.

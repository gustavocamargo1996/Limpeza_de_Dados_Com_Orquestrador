# Relatorio: conformidade de schema e remocao do portao da uniao

Branch `conformidade-de-schema`. Commits: `3ffa610` (conformidade), segundo commit (portao da uniao; ver `git log`).

## O que mudou
- `limpeza2/motor.py`: recebe `padrao` (movida de `e1_perfil`), tipo `conformidade` em `TIPOS` e em `detectar` (`~padrao(v,2).isin(padroes)`). Continua importando so pandas (teste de vazamento verde).
- `limpeza2/e1_perfil.py`: importa `padrao` de `motor`. Teste que mudou de import: `tests/test_e1_perfil.py::test_padrao` (so a linha de import).
- `limpeza2/conformidade.py` (novo, 32 linhas): `schema_da_coluna`, `candidatas_de_conformidade`.
- `limpeza2/config.py`: `FRACAO_PADROES_SCHEMA = Fraction(1, 3)` (Fraction para a comparacao no limite exato nao sofrer com ponto flutuante).
- `limpeza2/e3_crivo.py`: `conformidade` sem teto de marcacao; entra em `TIPOS_DE_VALOR` para o veto por valor certificado continuar ativo como alarme. Portao da uniao removido; `_gravar_uniao` grava `taxa_uniao` em `metricas` de cada regra sobrevivente; motivo `uniao_acima_do_teto` saiu de `MOTIVOS`. 179 -> 175 linhas.
- `limpeza2/limites.py`: `taxa_da_uniao` removida (e o import de pandas); o calculo mora no crivo.
- Testes: novo `tests/test_conformidade.py` (5); `test_e3_crivo.py`: 4 novos de conformidade; os 3 testes do portao antigo (`test_uniao_acima_do_teto_descarta_o_tipo_de_maior_taxa`, `test_uniao_que_cabe_no_teto_mantem_os_dois_tipos`, `test_empate_de_taxa_nao_depende_da_ordem_da_lista`) foram reescritos como 4: ambos sobrevivem acima do teto e a taxa 0,35 vai a metricas; cabe no teto grava 0,25; celula marcada por duas regras conta uma vez; ordem da lista nao muda quem sobrevive.
- Docs: `DECISOES.md` (ancora `#conformidade-de-schema`; entrada da uniao agora conta "tentada e removida" com o caso Temperature), `REGRAS_DO_LIMPADOR.md` (secao 4.6 com roteamento; crivo), `CLAUDE.md` e spec (arvore), `CONTINUACAO.md` (secoes 3 e 4 como implementadas, secao 7 renumerada).

## Numeros reais (fixtures *_300, guia canonico; gabarito so para medir)
beers (guia 20 linhas): coluna | padroes | schema | marca | erradas | precisao | recall
- index | 2 | sim | 9 | 0 | 0,000 | n/a (coluna sem erro)
- id | 3 | sim | 1 | 0 | 0,000 | n/a
- beer-name 20, style 15, brewery-name 17, city 9 | nao | - 
- ounces | 1 | sim | 295 | 295 | 1,000 | 1,000
- abv | 2 | sim | 72 | 70 | 0,972 | 1,000
- ibu | 3 | sim | 117 | 112 | 0,957 | 1,000
- brewery_id | 2 | sim | 15 | 0 | 0,000 | n/a
- state | 1 | sim | 9 | 9 | 1,000 | 1,000

environment:
- City 6, Country 3 | sim | 0 marcadas | vacua (sem erros na coluna)
- State | 1 | sim | 0 | - | - | recall 0,000 (abstencao esperada)
- Climate_Zone | 2 | sim | 0 | - | - | recall 0,000 (abstencao esperada)
- Monitoring_Station_ID | 6 | sim | 44 | 44 | 1,000 | 1,000
- PM2.5 | 3 | sim | 10 | 0 | 0,000 | n/a
- Temperature | 3 | sim | 56 | 56 | 1,000 | 1,000
- Measurement_Date | 1 | sim | 48 | 48 | 1,000 | 1,000
- Project_Name 20, Eco_Status 20 | nao
- index | 2 | sim | 10 | 0 | 0,000 | n/a

Todos os numeros que voce previu reproduziram. `marca_celula_correta` e o veto por valor certificado: False em todas as colunas, nenhum disparo.

## Provas por mutacao (saida bruta resumida)
1. Aplicar o teto tambem a conformidade (remover `tipo != "conformidade"`): `FAILED test_conformidade_aprovada_acima_do_teto_da_coluna`, `FAILED test_conformidade_nunca_marca_celula_nem_valor_certificado` -> 2 failed, 45 passed.
2. Corte "sempre tem schema" (`if False`): `FAILED test_texto_livre_nao_tem_schema_e_nao_emite_candidata`, `FAILED test_um_padrao_acima_do_limite_nao_tem_schema` -> 2 failed, 3 passed.
3. Limite `>` vira `>=`: `FAILED test_schema_apertado_marca_so_o_que_foge`, `FAILED test_no_limite_exato_de_um_terco_tem_schema` -> 2 failed.
4. Vacuidade (`== 0` vira `< 0`): `FAILED test_reprova_regra_vacua`, `FAILED test_conformidade_vacua_e_reprovada` -> 2 failed.
5. Motor sem o `~`: `FAILED test_schema_apertado_marca_so_o_que_foge` -> 1 failed.
6. Guia vazio (tirar `len(guia) == 0`): `FAILED test_guia_vazio_ou_coluna_ausente_nao_emite_candidata` -> 1 failed.
7. Reintroduzir o descarte da uniao: `FAILED test_uniao_acima_do_teto_mantem_os_dois_tipos_e_grava_a_taxa`, `FAILED test_a_ordem_da_lista_nao_muda_quem_sobrevive` (+ 2 de conformidade, que dependem de `taxa_uniao`) -> 4 failed, 182 passed.
Todas revertidas; suite verde depois.

## Pytest
`186 passed` com `-W error`: nenhum aviso.

## Orcamento
11 arquivos .py fora de tests, 940 linhas, maior 182 (`motor.py`). Teto 16/1.800/200.

## Preocupacoes
1. Coluna sem erro e de largura variavel (`index`, `id`, `brewery_id`, `PM2.5`, `index` do environment) tem schema e e marcada com precisao 0,000 (1 a 15 celulas); o crivo aprova porque nao tem como saber. Hoje o reparo deve falhar com `nao_repara`, mas e decisao de roteamento da parte 2.
2. Nao reproduzi a regra ruim de 22 sentinelas do Temperature (a lista nao esta no repositorio); o teste usa a mesma forma com dados sinteticos, e a regra boa real sobrevive.
3. Mantive `conformidade` em `TIPOS_DE_VALOR` (alem do pedido) para o veto continuar como alarme; custo zero, pois nao dispara.
4. CLAUDE.md §9 ainda diz "quinze arquivos"; nao mexi na contagem planejada.

# ADENDO: nivel 3 do padrao (substitui as tabelas de numeros acima)
`motor.NIVEL_SCHEMA = 3`, usada por `detectar` e por `conformidade.py`. Corte de um terco mantido. Suite: 187 passed com `-W error`.
Mutacao (NIVEL_SCHEMA = 2): 5 failed, 182 passed, incluindo o novo `test_numerica_de_largura_variavel_sem_erro_nao_e_marcada`; revertida.

beers (padroes | marca | certas | precisao | recall): index 1 | 0 | vacua; id 1 | 0 | vacua; beer-name 12 e style 9: sem schema; ounces 1 | 295 | 295 | 1,000 | 1,000; abv 1 | 72 | 70 | 0,972 | 1,000; ibu 2 | 112 | 112 | 1,000 | 1,000; brewery_id 1 | 0 | vacua; brewery-name 6 | 31 | 0 | 0,000 | n/a (custo); city 2 | 16 | 9 | 0,562 | 1,000; state 1 | 9 | 9 | 1,000 | 1,000.
Total beers: 535 marcadas, 495 certas de 495 erros, precisao 0,925.
environment: City 2, Country 2, State 1, Climate_Zone 1, PM2.5 1, index 1: marcam 0; Monitoring_Station_ID 2 | 44 | 44 | 1,000 | 1,000; Temperature 2 | 56 | 56 | 1,000 | 1,000; Measurement_Date 1 | 48 | 48 | 1,000 | 1,000; Project_Name 3 | 36 | 35 | 0,972 | 0,625 (reprovada no crivo: perde_par_do_guia); Eco_Status 8: sem schema.
Total environment: 184 marcadas, 183 certas de 334 erros, precisao 0,995.
Total geral: 678 de 829 erros; 719 marcadas; precisao 0,943. Vetos (celula correta, valor certificado): nenhum disparo.
Notas: city tem precisao 0,562 (nao so recall 1,000); Project_Name nao chega ao limpador por perde_par_do_guia.

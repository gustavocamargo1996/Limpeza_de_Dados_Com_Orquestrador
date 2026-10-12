# Relatório da Tarefa 2

## Commits
- `44e9e93` test_vazamento: fecha três buracos do guardião do gabarito (+ `.pytest_cache/` no `.gitignore`)
- `b3e1f61` preparar_guia.py: sorteia o guia com semente fixa (+ guias de beers e environment + testes)

## Item prependido (test_vazamento.py)
`modulos()` agora ignora `__init__.py` e usa `rglob`; o ramo `ImportFrom` examina `no.module` e também cada `alias.name`; ids de parametrização usam o caminho relativo.

Provas por mutação (todas executadas):
1. Anti-vacuidade: movi `config.py` e `tipos.py` para fora, deixando só `__init__.py`. Resultado: `FAILED test_o_pacote_tem_modulos` (`assert [] ... modulos()`). Revertido.
2. Import: `from limpeza2 import medir` em `config.py` -> `FAILED test_nenhum_modulo_importa_os_guardioes[config.py]`; `from . import medir` -> mesma falha. Revertido.
3. Recursão: `limpeza2/sub/x.py` com `import medir` -> `FAILED ...[sub\x.py]`. Revertido.
Suíte após reverter: 5 passed.

## Tarefa 2
Implementado `preparar_guia.py` (75 linhas) com o código do brief, literal. Guias gerados em `dados/guia/{beers,environment}/`. `guia_linhas.csv` gravado com `index_label="_linha"`.

### TDD
- RED: `pytest tests/test_preparar_guia.py` -> `ModuleNotFoundError: No module named 'preparar_guia'` (esperado: módulo ainda não existia).
- GREEN: 6 passed.

### Provas por mutação do brief
- A (`~diferentes.any` -> `diferentes.any`): `FAILED test_so_entram_linhas_sem_erro_nenhum`.
- B (`n=len(erradas)`): `FAILED test_respeita_a_cota_por_coluna`.
- C (`random_state=None` na amostra de linhas): **os 6 testes do brief continuaram passando (não morde).** Causa: na fixture há 3 linhas certas e `n_linhas=3`, então a amostra é uma permutação das 3 e o `sorted()` posterior apaga a diferença. Não alterei o código; acrescentei um sétimo teste, `test_a_semente_decide_quais_linhas_entram` (60 linhas, 1 erro, `n_linhas=5`, duas chamadas com mesma semente). Com a mutação C: `FAILED test_a_semente_decide_quais_linhas_entram` em 3 execuções seguidas. Revertido. Suíte final: 12 passed.

### Conferência manual dos guias
- beers `guia_pares.csv`: abv, city, ibu, ounces, state (2 pares cada). Nenhuma de index/id/beer-name/style/brewery_id/brewery-name. Bate com o esperado.
- environment `guia_pares.csv`: Climate_Zone, Eco_Status, Measurement_Date, Monitoring_Station_ID, Project_Name, State, Temperature (2 cada). Nenhuma de City/Country/PM2.5/index. Bate com o esperado.
- Saída do script: beers = **5 linhas** e 10 pares; environment = 20 linhas e 14 pares.

### Orçamento
4 arquivos `.py` fora de tests (limite 13); 159 linhas totais no `wc` final (limite 1.400); maior arquivo `preparar_guia.py` com 75 (limite 200).

## Arquivos alterados
`.gitignore`, `tests/test_vazamento.py`, `preparar_guia.py`, `tests/test_preparar_guia.py`, `dados/guia/beers/guia_{linhas,pares}.csv`, `dados/guia/environment/guia_{linhas,pares}.csv`.

## Auto-revisão e preocupações
- Beers só tem 5 linhas 100% corretas no recorte de 300; o guia fica com 5 linhas, não 20. Isso diverge da meta de ~20 linhas limpas do CLAUDE.md; decisão do usuário (relaxar a exigência de linha 100% correta, por exemplo só nas colunas com formato conhecido, ou aceitar 5).
- Teste C do brief é vacuoso; corrigido com o teste extra. A semente dos pares não tem teste dedicado (a mesma semente é reaproveitada por coluna).
- Avisos de LF->CRLF do git no Windows, inofensivos.

# Rodada de correção 1

Commit: ver `git log` (assunto "Rodada de correcao da tarefa 2: guardiao e testes do guia"). Só `preparar_guia.py`, `tests/test_preparar_guia.py` e `tests/test_vazamento.py` entraram. `CLAUDE.md` e `docs/REGRAS_DO_LIMPADOR.md` aparecem modificados na árvore, não por mim, e ficaram fora do commit.

## Mudanças
- `test_vazamento.py`: import testa todos os segmentos (`set(nome.split("."))`) em `Import` e `ImportFrom`; o teste de literais agora também proíbe qualquer string igual a `medir` ou `preparar_guia`.
- `preparar_guia.py`: removido `Path`; `gravar` devolve `(caminho_linhas, caminho_pares, n_linhas, n_pares)` e `main` usa as contagens, sem reler CSV. Mudança de interface em relação ao brief (antes 2-tupla); nenhum consumidor existe ainda.
- `test_preparar_guia.py`: o teste de determinismo e o sétimo foram fundidos em `test_a_mesma_semente_da_o_mesmo_guia`, com 60 linhas, 40 erros na coluna `w`, `n_linhas=5`, comparando linhas e pares.

## Provas por mutação (tests/test_vazamento.py, anexando a limpeza2/config.py, revertido depois)
- `from limpeza2.medir import f` -> `FAILED test_nenhum_modulo_importa_os_guardioes[config.py]`
- `import limpeza2.medir` -> `FAILED test_nenhum_modulo_importa_os_guardioes[config.py]`
- `X = "medir"` -> `FAILED test_nenhum_modulo_cita_arquivo_csv[config.py]`
- `importlib.import_module("preparar_guia")` -> `FAILED test_nenhum_modulo_cita_arquivo_csv[config.py]`
- `random_state=None` na amostra de pares -> `FAILED test_a_mesma_semente_da_o_mesmo_guia` em 3 execuções seguidas.

## Verificação
`.venv/Scripts/python -m pytest tests/test_vazamento.py tests/test_preparar_guia.py -q` -> `...........` (11 passed). Reexecução do `main` no beers: "guia de beers: 5 linhas, 10 pares", CSVs idênticos (sem diff).
Orçamento: 4 arquivos .py fora de tests, 157 linhas totais.

# Relatorio da tarefa 6: motor.py, estrategias de reparo

Commit: 1284cbc "motor.py: as cinco estrategias de reparo" (branch fundacao-deterministica).

## Implementado
Acrescentados a `limpeza2/motor.py`, copiados literalmente do brief: `ESTRATEGIAS`, `distancia_edicao` (Damerau-Levenshtein restrita), `reparar`, `_mais_proximo`, `_reparar_por_moda`. `_reparar_por_moda` usa `moda_dominante` e nao recalcula a moda. Dois lacos mantidos separados. Nenhum import local; so `pandas`. Nenhum `try`.

## Testes
`tests/test_motor_reparo.py`, copiado do brief. Resultado final: 15 passed (o brief diz 14, mas o parametrize de distancia_edicao gera 5 casos; 10 funcoes + 5 = 15). Suite completa: toda verde.

## TDD
RED: `.venv/Scripts/python -m pytest tests/test_motor_reparo.py -q`
```
tests\test_motor_reparo.py:5: in <module>
    from limpeza2.motor import distancia_edicao, reparar
E   ImportError: cannot import name 'distancia_edicao' from 'limpeza2.motor' (...\limpeza2\motor.py)
ERROR tests/test_motor_reparo.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!
```
Esperado: as funcoes ainda nao existiam.
GREEN: `.venv/Scripts/python -m pytest tests/test_motor_reparo.py -v`
```
collected 15 items
tests\test_motor_reparo.py ...............                               [100%]
============================= 15 passed in 2.34s ==============================
```

## Provas por mutacao (saida bruta do pytest, filtrada por E/FAILED; mutacao aplicada, rodada, revertida)

### A: laco do determinante removido (`for det in []`) -> MORDEU
```
E       AssertionError: assert 'Bosotn' == 'Boston'
FAILED tests/test_motor_reparo.py::test_corrige_o_determinante_quando_ele_e_o_erro_de_digitacao
```

### B: dominancia ignorada -> MORDEU (com ajuste do plano)
O plano manda trocar `if contagem.iloc[0] / len(grupo) < dominancia: continue`, que NAO existe em `_reparar_por_moda`: essa guarda mora em `moda_dominante` (`len(serie)`, `return None`). Mutei la: `return None` -> `pass`.
```
E       AssertionError: assert ['10:30', '10...:30', '10:30'] == ['10:30', '10...:28', '10:39']
E         At index 1 diff: '10:30' != '10:31'
FAILED tests/test_motor_reparo.py::test_moda_condicionada_nao_repara_grupo_ambiguo
```

### C: `novo = df.copy()` -> `novo = df` -> MORDEU
```
FAILED tests/test_motor_reparo.py::test_normalizar_aplica_a_funcao_escalar
FAILED tests/test_motor_reparo.py::test_esvaziar_zera_a_celula
FAILED tests/test_motor_reparo.py::test_reparar_nao_altera_o_dataframe_recebido
```
(os dois primeiros falham junto porque, sem copia, `df.at[...] != ""` compara o valor ja mutado e a mascara reparada fica errada.)

### D: `return melhor if menor <= distancia_maxima else None` -> `return melhor` -> NAO MORDEU
Saida bruta: `...............                                                          [100%]` (15 passed).
Causa: mutante equivalente. `melhor` so deixa de ser None quando `d < menor`, e `menor` comeca em `distancia_maxima + 1`; logo `menor <= distancia_maxima` e verdadeiro sempre que `melhor` nao e None. A guarda final e redundante, e nenhum teste pode distingui-la. Defeito do plano, nao do teste. Nao ajustei o codigo para encaixar. O comportamento "desiste quando esta longe" e de fato protegido pela inicializacao de `menor`; uma mutacao que o quebra de verdade seria trocar `distancia_maxima + 1` por `float("inf")`, que nao testei por nao constar do plano. Sugestao: trocar a mutacao D por essa, ou simplificar `_mais_proximo` removendo a guarda (`return melhor`).

### E: bloco de transposicao desligado (`if False:`) -> MORDEU
```
E       AssertionError: assert 2 == 1
E        +  where 2 = distancia_edicao('Boston', 'Bosotn')
E       AssertionError: assert 2 == 1
E        +  where 2 = distancia_edicao('Tropcial', 'Tropical')
FAILED tests/test_motor_reparo.py::test_corrige_o_determinante_quando_ele_e_o_erro_de_digitacao
FAILED tests/test_motor_reparo.py::test_distancia_edicao[Boston-Bosotn-1]
FAILED tests/test_motor_reparo.py::test_distancia_edicao[Tropcial-Tropical-1]
```

Apos todas, motor.py restaurado (`git diff` so mostra o acrescimo de 108 linhas) e suite completa verde.

## Tamanho
`motor.py`: 152 linhas (teto 200; folga de 48). Nao precisou separar.

## Orcamento
`git ls-files "*.py" ":!tests/"`: 7 arquivos (teto 13), 555 linhas totais (teto 1.400), maior arquivo motor.py 152 (teto 200).

## Arquivos alterados
`limpeza2/motor.py`, `tests/test_motor_reparo.py` (novo). Este relatorio nao foi commitado.

## Auto-revisao e preocupacoes
- Mutacao D equivalente (acima); mutacao B apontava para linha inexistente (ajustada).
- Contagem de testes: 15, nao 14.
- Mensagem de commit: troquei a frase "cada uma derruba o teste" para registrar o mutante equivalente, por honestidade.
- `moda_condicionada` com multiplos determinantes: o laco do determinante usa `original`, entao dois determinantes raros na mesma linha sao corrigidos independentemente; nao testado, fora do escopo.
- Avisos LF/CRLF do git sao do ambiente Windows.

## Rodada de correcao 1

Mudancas: `_mais_proximo` sem a guarda morta (`return melhor`, docstring ajustada); `raros` e `comuns` viraram `set`; 6 testes novos (21 no arquivo; suite completa 96 passed). `motor.py` continua com 152 linhas; orcamento: 7 arquivos, 555 linhas, maior 152.

Testes novos: `test_nao_reescreve_chave_legitima_e_frequente`, `test_nao_corrige_chave_rara_para_outra_rara`, `test_dicionario_ignora_valor_fora_do_mapa`, `test_esvaziar_nao_conta_celula_ja_vazia`, `test_vizinho_no_dominio_aceita_distancia_igual_ao_limite`, `test_estrategia_desconhecida_falha_alto`.

Provas por mutacao (todas revertidas depois; saida filtrada do pytest):

- `n == 1` -> `n >= 1` (raros): MORDEU
```
E       AssertionError: assert ['Bosotn', 'B...on', 'Boston'] == ['Boston', 'B...tn', 'Bosotn']
E         At index 0 diff: 'Bosotn' != 'Boston'
FAILED tests/test_motor_reparo.py::test_nao_reescreve_chave_legitima_e_frequente
```
- `n >= 2` -> `n >= 1` (comuns): na primeira tentativa NAO MORDEU. Erro do meu teste: usei Bosotn/Bostno, que distam 2 (nao 1), entao nao havia vizinho a uma edicao. Troquei o par para dois singletons a uma edicao e sem valor comum por perto (Bosotn/Boston, com Austin x3). Depois disso MORDEU:
```
E       AssertionError: assert 'Boston' == 'Bosotn'
FAILED tests/test_motor_reparo.py::test_nao_corrige_chave_rara_para_outra_rara
```
- `if valor in mapa` -> `if True`: MORDEU
```
E                   KeyError: 'Tropical'
FAILED tests/test_motor_reparo.py::test_dicionario_ignora_valor_fora_do_mapa
```
- esvaziar `!= ""` -> `True`: MORDEU
```
E       assert [False, False...e, True, True] == [False, False..., True, False]
E         At index 5 diff: True != False
FAILED tests/test_motor_reparo.py::test_esvaziar_nao_conta_celula_ja_vazia
```
- `distancia_maxima + 1` -> `float("inf")`: MORDEU
```
E       AssertionError: assert 'Tropical' == 'N/A'
FAILED tests/test_motor_reparo.py::test_vizinho_no_dominio_desiste_quando_esta_longe
```
- `distancia_maxima + 1` -> `distancia_maxima` (limite inclusivo): MORDEU
```
E       AssertionError: assert 'Tropcial' == 'Tropical'
FAILED tests/test_motor_reparo.py::test_vizinho_no_dominio_aceita_distancia_igual_ao_limite
```
O teste do ValueError nao teve mutacao rodada (teste de uma linha, como o da tarefa 5); removendo o `raise` o teste falharia por nao levantar.

## Rodada de correcao 2

Codigo: `comuns` voltou a sequencia ordenada por `(-frequencia, valor)`, com comentario de 2 linhas; `raros` segue `set`. Regra: entre vizinhos a uma edicao vence o mais frequente; empate vai para o primeiro em ordem alfabetica.

**Divergencia com o pedido:** a mensagem pedia afirmar `Boston` "por ser o primeiro em ordem alfabetica" entre Boston e Bostan. Isso e falso: `"Bostan" < "Boston"` ('a' < 'o'). Primeira execucao do teste com `Boston` falhou nos 4 seeds (0,1,2,3) no codigo CORRETO, o que revelou o erro. O teste afirma `Bostan`, o valor que a regra declarada realmente produz.

Teste novo: `test_empate_entre_vizinhos_vai_para_o_primeiro_em_ordem_alfabetica` (Boston x2, Bostan x2, Bostn x1, mascara na linha de Bostn, afirma `Bostan`).

Verde, seeds 0-3 (`PYTHONHASHSEED=n pytest tests/test_motor_reparo.py -q`): todos `......................  [100%]` (22 passed).

Mutacao: `comuns` como `set`, seeds 0-3:
```
seed=0  E AssertionError: assert 'Boston' == 'Bostan'   FAILED ...test_empate_entre_vizinhos_vai_para_o_primeiro_em_ordem_alfabetica
seed=1  (passou: set por acaso iterou Bostan primeiro)
seed=2  E AssertionError: assert 'Boston' == 'Bostan'   FAILED ...test_empate...
seed=3  E AssertionError: assert 'Boston' == 'Bostan'   FAILED ...test_empate...
```
Mordeu em 3 de 4 seeds.

Mutacao do `raise ValueError` trocado por `pass`:
```
E       Failed: DID NOT RAISE ValueError
FAILED tests/test_motor_reparo.py::test_estrategia_desconhecida_falha_alto
```
(Na primeira execucao desta mutacao o teste de empate tambem aparecia falhando, mas era por ainda afirmar `Boston`, o erro descrito acima; nao e efeito do `pass`.)

Tamanhos: `motor.py` 154 linhas; orcamento 7 arquivos, 557 linhas, maior 154. Suite completa verde; arquivo de reparo com 22 testes.

## Rodada de correcao 3

Opcao 1: a ordenacao foi extraida para `vizinhos_ordenados(frequencia)` em `motor.py` (docstring de 1 linha, comentario de 1 linha); `_reparar_por_moda` faz `comuns = vizinhos_ordenados(frequencia)`, o que ficou mais curto que antes. Nada mais mudou.

Testes novos: `test_vizinhos_ordenados_por_frequencia_e_depois_alfabetica` (afirma a lista exata `["Boston", "Austin", "Bostan"]`, direto, sem seed) e `test_frequencia_vence_a_ordem_alfabetica` (Boston x3, Bostan x2, Bostn: sai `Boston`).

Mutacao, chave `(par[0], -par[1])`: MORDEU nos dois testes novos.
```
E       AssertionError: assert ['Austin', 'Bostan', 'Boston'] == ['Boston', 'Austin', 'Bostan']
E       AssertionError: assert 'Bostan' == 'Boston'
FAILED tests/test_motor_reparo.py::test_vizinhos_ordenados_por_frequencia_e_depois_alfabetica
FAILED tests/test_motor_reparo.py::test_frequencia_vence_a_ordem_alfabetica
```

Mutacao, retorno da funcao como `set`, seeds 0-3: agora FALHA EM TODOS, deterministicamente (um `set` nunca e igual a uma lista), com saida bruta por seed:
```
seed=0 E assert {'Austin', 'Bostan', 'Boston'} == ['Boston', 'Austin', 'Bostan']  FAILED ...test_vizinhos_ordenados_...  (+ test_empate_...)
seed=1 E assert {'Austin', 'Bostan', 'Boston'} == ['Boston', 'Austin', 'Bostan']  FAILED ...test_vizinhos_ordenados_...  (+ test_frequencia_vence_...)
seed=2 idem seed=0
seed=3 idem seed=0
```
O seed 1, que antes passava por sorte, agora e pego pelo teste direto.

Resumo do pytest (`-o addopts=""`, pois pyproject usa `-q`): `tests/test_motor_reparo.py`: `24 passed in 0.89s`; suite completa: `99 passed in 1.87s`.
`motor.py`: 159 linhas (teto 200). Orcamento: 7 arquivos, 562 linhas, maior 159.

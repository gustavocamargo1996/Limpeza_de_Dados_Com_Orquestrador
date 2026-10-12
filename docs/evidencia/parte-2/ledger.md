# SDD ledger — plan: docs/superpowers/plans/2026-10-12-parte-2-agentes.md

Branch: parte-2-agentes. Merge base com main: 166d48a. Spec: docs/superpowers/specs/2026-10-12-parte-2-agentes-design.md.

## Varredura pre-execucao

| Par / tarefa | Produz -> consome | Achado |
|---|---|---|
| T1 -> T2 | motor.TIPOS, aplicar_regras -> tipos.regras_literais (formato literal) | consistente: chaves coluna/tipo/deteccao/estrategia/reparo |
| T1 -> T7 | aplicar_regras(df, regras, residual, funcoes, dominancia) -> e5.resolver | consistente |
| T2 -> T3 | tests/apoio.py criado (monta_entrada) -> T3 acrescenta ok/CORTADA/Roteiro/em_fila e import json | consistente |
| T2 -> T4/T5/T6/T7 | limites.exemplos_do_guia -> prompts | consistente |
| T2 -> T9 | e3_crivo.crivar_residual(residuais, entrada) -> espinha | consistente |
| T3 -> T4..T9 | fixture roteiro, provedor.cliente/FalhaDoLLM/anotar -> agentes e testes | consistente |
| T5 -> T6 | Reparo.parametros["transformacao"] -> e6._funcao | consistente |
| T6 -> T8 | e6_codificador.py criado com imports curtos -> T8 troca o bloco de imports | consistente (T8 manda trocar) |
| T6 -> T8 testes | helpers BOM/proposta/oncas em test_e6_codificador -> gerar() do T8 | consistente |
| T8 -> T9 | medir.avaliar devolve truncada -> teste ponta a ponta | consistente |
| T0 | apaga __init__.py; contagem 10 | coerente consigo |
| T1 | contagens 188 -> 194 | coerente |
| T2 | 194+3=197; +6=203 | coerente (corrigido na auto-revisao do plano) |
| T3 | 203+15=218 | coerente |
| T4..T9 | "tudo passa" | sem numero fixo; ok |
| T10 | texto cita `medir.medir(...)`, funcao inexistente | ver Ruling 1 |
| T11 | Step 3 pede requesting-code-review | ver Ruling 2 |
| T12 | run pago | ver Ruling 3 |

Ruling 1: no paragrafo novo do CLAUDE.md §9 (T10), escrever `medir.avaliar(...)` em vez de `medir.medir(...)` — medir.py nao tem funcao `medir`; a funcao que mede e `avaliar` — custo se errado: uma palavra num documento.
Ruling 2: o Step 3 da T11 (revisao de codigo) e cumprido pela revisao final de branch inteiro do SDD; os Steps 1-2 (suite, teto, frase por arquivo) o controlador roda como checagem somente leitura — evita revisao duplicada — custo se errado: nenhum, a revisao final cobre o mesmo diff.
Ruling 3: a T12 (run pago) NAO e executada nesta rodada de SDD; o controlador para ao fim da T11 e entrega ao usuario, porque CLAUDE.md §8 diz que run que gasta API e decisao do usuario, anunciada antes — custo se errado: o usuario precisa dizer "pode rodar".

## Progresso
Ruling 4: o trailer Co-Authored-By de cada commit nomeia o modelo que o escreveu (Haiku/Sonnet nos subagentes), seguindo a regra de atribuicao do ambiente, e nao "Opus" fixo do plano — atribui a autoria a quem escreveu — custo se errado: reescrever trailers antes do merge.
Task 0: minor (deferred): CLAUDE.md §9 diz "Dezesseis arquivos" e o revisor contou 15 entradas na arvore; conferir na T10.
Task 0: complete (commits 6f9b0de..2931afa, review clean)
Task 1: minor (deferred): ancora docs/DECISOES.md#reparada-e-mudanca citada no teste so nasce na T10 (prevista).
Task 1: minor (deferred): aplicar_regras rotula "residual" mesmo se mapa[v]==v; a consolidacao do e5 (T7) ja tira limpo==sujo, entao nao ocorre pelo caminho normal.
Task 1: complete (commits 2931afa..9188570, review clean)
Task 2: minor (deferred): e3_crivo.py:188 comentario "Sem excecao: a chave do dicionario nao carrega contexto" e justificativa, nao mecanica (CLAUDE.md §5); trocar por link a DECISOES#residual-congelado.
Task 2: minor (deferred): crivar_residual muta e devolve; docstring nao diz. Residual.justificativas nao e podado quando a entrada cai.
Task 2: minor (deferred): limites.py espacamento PEP 8 entre funcoes.
Task 2: complete (commits 9188570..f5bd4e7, review clean)
Task 3: minor (deferred): plano previa 218 testes, suite deu 220 (o diff adiciona exatamente os 15 previstos; erro de contagem do plano). Linha longa em provedor.py (nota = {...}); Roteiro.responder sem docstring.
Task 3: complete (commits f5bd4e7..d637901, review clean)
Task 4: Ruling: o teste novo de e1 (contagens como int do Python) nao teve RED, porque o pandas 3 ja devolve int em .items(); a conversao int(n) e o teste ficam como contrato do formato do prompt (o LLM le "('12', 3)", nao "np.int64(3)") — mantem uma guarda barata contra regressao de versao do pandas — custo se errado: um teste que nao morde nesta versao; a revisao final decide se sai.
Task 4: minor (deferred): _valida nao checa se os determinantes de dependencia existem (o crivo reprova como sem_perfil); faixa nao guarda NaN/inf.
Task 4: complete (commits d637901..46a5902, review clean)
Task 5: minor (deferred): cobertura de mutacao fina em ramos de validacao (bool em distancia, truncamento VALORES_NO_PROMPT); testes de prompt dependem de formatacao exata.
Task 5: complete (commits 46a5902..8747ca5, review clean)
Task 6: minor (deferred): detalhe_reparo fica com a mensagem da 1a rejeicao mesmo quando a 2a tentativa passa (trilha de auditoria pode enganar); ramo FalhaDoLLM do codificar sem teste e sem detalhe_reparo.
Task 6: complete (commits 8747ca5..51c6f4b, review clean)
Task 7: Ruling: aceito o ajuste do implementador no teste do brief — a nota da coluna-sujeito e filtrada por status "escolha", porque pedir_json ja grava uma nota "ok" com a mesma unidade; o plano estava errado — custo se errado: nenhum, a nota especificada e a de status "escolha".
Task 7: Ruling: aceito o teste extra test_lote_exatamente_cheio_ainda_cabe — a mutacao <= -> < do plano sobrevivia aos testes do brief; sem ele o teste nao morde — custo se errado: um teste a mais.
Task 7: minor (deferred): e5_residual `chave in pedidos` lanca TypeError se o LLM devolver coluna/sujo nao-hashable (so possivel no plano B json_object); linhas com flag alem de LINHAS_POR_LOTE numa entidade somem do lote sem nota no registro.
Task 7: complete (commits 51c6f4b..93d22dd, review clean)
Task 8: Ruling: achado 3 (compactacao 203->200 linhas) — em vez de reabrir a conversa com o usuario, troca-se a compactacao por simplificacao real (teto calculado uma vez em escrever; provedor.cliente() buscado uma vez e passado adiante), desfazendo os += fundidos — o CLAUDE.md §2 manda simplificar o desenho e proibe espremer formatacao; a deduplicacao e simplificacao de verdade — custo se errado: se nao couber em 200 mesmo assim, ai sim vai ao usuario.
Task 8: Ruling: inline da variavel de uso unico celulas na f-string do cabecalho do .md e aceito — tirar variavel de uso unico e simplificacao, nao formatacao espremida — custo se errado: uma linha longa.
Task 8: fix round 1/5 (3 addressed, 0 open; commits 555e45f..cb4a87e)
Task 8: minor (deferred): e6_codificador.py em exatamente 200 linhas, sem folga; duas linhas >110 caracteres; renomear nao trata funcao recursiva; main() do limpador sem teste; motivo aparece duas vezes no .md.
Task 8: complete (commits 93d22dd..cb4a87e, review clean)
Task 9: minor (deferred): o guarda do teste de vazamento so exige que algo tenha sido aberto, nao que o sujo, o guia e o motor tenham sido; destino do CLI colide em dois runs no mesmo minuto; linha de help longa.
Task 9: complete (commits cb4a87e..b715a8b, review clean). Medidas: 16 arquivos, 1772 linhas, maior 200 (e6_codificador.py); suite 282 passed.
Task 10: fix round 1/5 (3 addressed, 0 open; commits 830a02c..722d148)
Task 10: minor (deferred): REGRAS_DO_LIMPADOR.md:53-60 ainda descreve "sete etapas" com numeracao antiga, enquanto a espinha tem outra contagem.
Task 10: complete (commits b715a8b..722d148, review clean)
Task 11: complete (checagens do controlador: 282 passed; 16 arquivos; 1772 linhas; maior 200; docstrings de 1 frase. Step 3 = revisao final, Ruling 2)
Revisao final (opus): Ready to merge: With fixes. 1 Critical, 3 Important, 7 Minor; triagem do ledger com 4 "fix before merge".
Ruling 5: Critical 1 — reparar captura excecao de escalar(antes) e a celula vira flag (degradacao nomeada, como a spec de 11/10 §9 promete); o codificar passa a rodar a fumaca em TODOS os valores marcados distintos, para o crivo continuar vendo "lancou" na tabela de origem — custo se errado: falha de funcao gerada vira flag silenciosa em tabela nova (e o comportamento prometido).
Ruling 6: Important 1 — a origem da geracao (provedor, modelo, esforco) vai como primeiro registro do respostas.jsonl; o Cliente expoe `origem`, e sob PROVEDOR=gravado ela vem do arquivo; cabecalho e .md usam cliente.origem — sem isso o replay nao e byte a byte e o cabecalho mente o modelo — custo se errado: formato do respostas.jsonl muda antes de qualquer congelamento, sem custo de migracao.
Ruling 7: Important 2 — candidata aprovada que perdeu a disputa de menor taxa recebe motivo "superada" (novo em MOTIVOS) — o .md nao pode mostrar como aprovada regra que nao esta no limpador — custo se errado: um rotulo.
Ruling 8: Important 3 — o teste de vazamento exige que o sujo, os dois CSVs do guia e o motor.py tenham sido abertos — custo: nenhum.
Ruling 9: conformidade passa a ser o PRIMEIRO tipo em motor.TIPOS (ordem de aplicacao no limpador): e a regra derivada de dado certificado, e numa celula disputada ela deve vencer a regra proposta pelo LLM — custo se errado: celulas disputadas resolvidas diferente; reversivel numa linha antes do primeiro congelamento.
Ruling 10: o cabecalho do limpador NAO traz a receita do guia (spec §6 pede), so linhas e pares do guia — ler guia_receita.txt quebraria o invariante de vazamento em execucao (so os dois CSVs do guia podem ser lidos) — custo se errado: o usuario quer a semente no cabecalho; dai passa-se por config.
Ruling 11: o teste de e1 (contagens int) fica, com comentario de 1 linha dizendo que e guarda de versao do pandas (sem RED no pandas 3) — custo se errado: um teste que nao morde nesta versao.
Ruling 12: o Minor "falha do LLM rotulada codigo_rejeitado" fica sem correcao — e6_codificador.py esta em 200 linhas e o registro do provedor ja mostra a causa real — custo se errado: rotulo impreciso no .md.
Ruling 13: o comentario longo em e6_codificador.py:177 fica — dividi-lo estoura 200 linhas — custo: estetico.
Ruling 14: aceito o desvio do item 4 da leva final — cada espia (read_csv e open) tem lista propria; read_csv tem de ver os tres CSVs e open os quatro arquivos — a mutacao do brief nao mordia porque o pandas abre pelo open espiado — custo se errado: nenhum, o teste ficou mais forte.
Ruling 15: aceito que funcao que lanca em toda celula passe a ser reprovada no crivo como nao_repara (e nao lancou), com dois testes antigos ajustados — consequencia direta do Ruling 5; o codificar ja rejeita essa funcao antes, pela fumaca em todos os valores marcados — custo se errado: o motivo no .md muda de nome nesse caso.
Leva final: re-revisao (opus) — todos os achados ADDRESSED, sem nova quebra Critical/Important (commits 722d148..02d83ba; 292 passed; 16 arquivos; 1794 linhas; maiores 200/197/196).
Final: parked — portao.materializar deixa escapar NameError na execucao do def (ex.: default `valor=desconhecida`), e _funcao so captura FalhaDoLLM e CodigoRejeitado: o LLM pode derrubar uma geracao paga — Ruling: real e pre-existente; deve ser corrigido ANTES do primeiro run pago (embrulhar o exec em CodigoRejeitado, ~3 linhas no portao); fica para o usuario decidir, sem segunda leva.
Final: parked — e2_detector._valida: math.isfinite lanca OverflowError com inteiro de 400 digitos, fora do except FalhaDoLLM — Ruling: real, improvavel (o modelo teria de mandar um inteiro gigante); correcao de 1 linha junto com a anterior antes do run pago.
Final: parked — motor.reparar captura Exception de toda estrategia escalar, nao so normalizar: bug interno de dicionario/vizinho/esvaziar vira flag silenciosa — Ruling: fica; essas estrategias tem testes proprios e a degradacao e a prometida na spec.
Final: parked — a chamada modulo.aplicar(...) da fumaca final ficou sem teste que a derrube — Ruling: fica; com a falha por celula virando flag, quase nada chega a ela; o teste de ponta a ponta executa o limpador gerado.
Final: parked — sob Ollama a origem grava `esforco` de config embora o _Api nao o envie — Ruling: fica; cosmetico no cabecalho, Ollama nao e o provedor desta POC.

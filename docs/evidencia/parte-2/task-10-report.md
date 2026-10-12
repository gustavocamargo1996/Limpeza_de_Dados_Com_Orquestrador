# Tarefa 10: relatório
Commit 830a02c. Somente documentos.
- docs/DECISOES.md: #provedor (gpt-6-luna + ressalva de método); acréscimos em #residual-congelado, #portao-ast, #conformidade-de-schema; novas seções #roteamento-do-detector, #determinismo-da-geracao, #falha-de-api, #reparada-e-mudanca.
- docs/REGRAS_DO_LIMPADOR.md §7: memória do domínio e braço sem guia.
- CLAUDE.md §9: espinha nova, parágrafo do crivo (com medir.avaliar, por ordem do controlador), tipos que viajam, comentários de espinha.py e motor.py. A árvore já listava os 16 arquivos.
- docs/CONTINUACAO.md: seções 1 e 7 reescritas (16 arquivos, 1.772 linhas, maior 200, 282 testes, sem API, gpt-6-luna, degraus pagos); itens obsoletos (espinha inexistente, __init__ como vaga livre) corrigidos; seção 8 intacta.
Concerns: CONTINUACAO ainda tem seções 3-5 históricas com trechos antigos (ex.: "nível 2" explicado como correção posterior) mantidas por serem fatos datados.

## Rodada de correção 1
- REGRAS_DO_LIMPADOR.md:63: "etapas 3 e 5 a 7 ainda não existem" trocado por "todas implementadas e testadas com provedor falso; nenhum run pago". Varredura do arquivo: sem outro "ainda não existe" nem "parte 2" obsoleto.
- DECISOES.md #motor-unico: pendência e "será verificada" reescritos no presente, nomeando test_bloco_embutido_e_motor_byte_a_byte.
- DECISOES.md fim de #par-do-guia (linha ~444): código (_reprovar) cobre só pares explícitos, de propósito; reescrito como decisão, não pendência.
- Suíte: ver linha final do pytest no commit (282 passed esperado).

"""Etapa 5: rodada residual por entidade -> dicionario congelado no limpador."""
from limpeza2 import config, provedor
from limpeza2.limites import exemplos_do_guia
from limpeza2.motor import aplicar_regras
from limpeza2.tipos import Residual, regras_literais

INSTRUCAO_SUJEITO = """Voce ajuda uma ferramenta de limpeza de dados a agrupar linhas por entidade.
Recebe as colunas da tabela, algumas linhas e as colunas candidatas a identificar a entidade
(a coisa que cada linha descreve: uma cervejaria, uma estacao, um hospital).
Escolha a candidata que NOMEIA a entidade, ou null se nenhuma nomeia.
"raciocinio": uma frase. Responda em JSON."""

INSTRUCAO = """Voce corrige valores que as regras de uma ferramenta de limpeza de dados marcaram
como errados e nao souberam corrigir.
Recebe linhas da mesma entidade, como contexto, e a lista de valores suspeitos, cada um com a coluna.
Linhas da mesma entidade costumam repetir informacao: use essa redundancia.
Para cada valor suspeito, devolva o valor correto em "limpo", ou null se nao tiver certeza ou se o
valor ja estiver certo. Os exemplos sujo -> limpo do guia sao corretos e mostram o formato esperado.
"justificativa": uma frase. Responda em JSON."""

_CORRECAO = {"type": "object", "additionalProperties": False,
             "required": ["coluna", "sujo", "limpo", "justificativa"],
             "properties": {"coluna": {"type": "string"}, "sujo": {"type": "string"},
                            "limpo": {"type": ["string", "null"]}, "justificativa": {"type": "string"}}}
ESQUEMA = {"type": "object", "additionalProperties": False, "required": ["correcoes"],
           "properties": {"correcoes": {"type": "array", "items": _CORRECAO}}}


def resolver(deteccoes, reparos, funcoes, entrada):
    """Pergunta pelos valores marcados que nenhum reparo corrigiu; um Residual por coluna."""
    regras = regras_literais(deteccoes, reparos)
    _, flags, _ = aplicar_regras(entrada.sujo, regras, {}, funcoes, config.DOMINANCIA_MODA)
    if not flags.to_numpy().any():
        return []
    respostas = {}
    for numero, lote in enumerate(lotes_por_entidade(entrada.sujo, flags, _sujeito(entrada)), 1):
        if numero > config.MAX_LOTES_RESIDUAL:
            provedor.cliente().anotar("residual", f"lote {numero}", "sem_lote", f"{len(lote)} linhas")
            continue
        pedidos = {(coluna, entrada.sujo.at[linha, coluna])
                   for linha in lote for coluna in entrada.sujo.columns if flags.at[linha, coluna]}
        try:
            resposta = provedor.cliente().pedir_json(
                "residual", f"lote {numero}", INSTRUCAO, _conteudo(entrada, lote, pedidos), ESQUEMA)
        except provedor.FalhaDoLLM:
            # Degradacao nomeada: as celulas do lote ficam como flag.
            continue
        for item in resposta.get("correcoes") or []:
            chave = (item.get("coluna"), item.get("sujo")) if isinstance(item, dict) else None
            limpo = item.get("limpo") if chave in pedidos else None
            if isinstance(limpo, str) and limpo != chave[1]:
                respostas.setdefault(chave, set()).add((limpo, str(item.get("justificativa") or "")))
    return consolidar(respostas)


def lotes_por_entidade(sujo, flags, sujeito):
    """Lotes de ate LINHAS_POR_LOTE linhas, cada entidade inteira, na ordem da primeira linha."""
    marcadas = flags.any(axis=1)
    if sujeito is None:
        grupos = [[linha] for linha in sujo.index[marcadas]]
    else:
        afetadas = sujo[sujo[sujeito].isin(sujo.loc[marcadas, sujeito])]
        # Quando a entidade nao cabe num lote, a linha com flag vem antes do contexto.
        grupos = [sorted(sorted(g.index, key=lambda i: not marcadas[i])[: config.LINHAS_POR_LOTE])
                  for _, g in afetadas.groupby(sujeito, sort=False)]
    lotes = []
    for grupo in grupos:
        if lotes and len(lotes[-1]) + len(grupo) <= config.LINHAS_POR_LOTE:
            lotes[-1] += grupo
        else:
            lotes.append(list(grupo))
    return lotes


def consolidar(respostas):
    """Um Residual por coluna; respostas divergentes para o mesmo valor saem como conflitante."""
    residuais = {}
    for (coluna, sujo), opcoes in sorted(respostas.items()):
        residual = residuais.setdefault(coluna, Residual(coluna=coluna, mapa={}, justificativas={}))
        limpos = sorted({limpo for limpo, _ in opcoes})
        if len(limpos) > 1:
            residual.caidas[sujo] = f"conflitante: {limpos}"
            continue
        residual.mapa[sujo] = limpos[0]
        residual.justificativas[sujo] = min(j for _, j in opcoes)
    return list(residuais.values())


def _sujeito(entrada):
    """A coluna que nomeia a entidade, escolhida pelo LLM entre as mineradas, ou None."""
    candidatas = entrada.perfil.candidatas_sujeito
    if not candidatas:
        return None
    esquema = {"type": "object", "additionalProperties": False, "required": ["coluna", "raciocinio"],
               "properties": {"coluna": {"type": ["string", "null"], "enum": [*candidatas, None]},
                              "raciocinio": {"type": "string"}}}
    conteudo = (f"colunas: {list(entrada.sujo.columns)}\ncandidatas: {candidatas}\n"
                f"linhas:\n{entrada.sujo.head(10).to_csv()}")
    try:
        resposta = provedor.cliente().pedir_json(
            "residual", "coluna_sujeito", INSTRUCAO_SUJEITO, conteudo, esquema)
    except provedor.FalhaDoLLM:
        # Degradacao nomeada: sem sujeito, os lotes seguem a ordem das linhas.
        return None
    coluna = resposta.get("coluna") if resposta.get("coluna") in candidatas else None
    provedor.cliente().anotar("residual", "coluna_sujeito", "escolha",
                              f"{coluna}: {resposta.get('raciocinio', '')}")
    return coluna


def _conteudo(entrada, lote, pedidos):
    """Os valores suspeitos, os exemplos do guia e as linhas do lote como contexto."""
    linhas = [f"suspeito: coluna {c!r}, valor {v!r}" for c, v in sorted(pedidos)]
    for coluna in sorted({c for c, _ in pedidos}):
        linhas += [f"exemplo do guia em {coluna}: {s!r} -> {limpo!r}"
                   for s, limpo in exemplos_do_guia(entrada, coluna)]
    return "\n".join(linhas) + "\nlinhas da entidade:\n" + entrada.sujo.loc[lote].to_csv()

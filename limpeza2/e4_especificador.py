"""Etapa 4: agente especificador -> JSON de reparo, uma chamada por deteccao aprovada."""
from limpeza2 import config, provedor
from limpeza2.limites import exemplos_do_guia, valores_certificados
from limpeza2.motor import ESTRATEGIAS, detectar
from limpeza2.tipos import Reparo

INSTRUCAO = """Voce e o agente especificador de uma ferramenta de limpeza de dados.
Recebe uma regra de deteccao ja aprovada e os valores que ela marcou numa coluna. Escolha COMO
corrigi-los, com uma estrategia do catalogo fechado. Voce nao escreve codigo.
- normalizar: transformacao previsivel do texto; descreva-a em "transformacao" com precisao
  (ex.: "remover o sufixo ' oz' e a parte decimal .0"). Um programador a traduzira em Python.
- moda_condicionada: o valor certo e o mais comum entre as linhas que tem o mesmo valor nas
  colunas "determinantes".
- vizinho_no_dominio: o valor certo e o valor valido mais parecido, a ate "distancia" edicoes (1 a 3).
- dicionario: pares literais em "mapa", para o que nao segue padrao.
- esvaziar: o valor marcado significa ausencia e deve virar vazio.
Os exemplos sujo -> limpo do guia sao corretos: a estrategia tem de reproduzi-los.
"raciocinio": tres frases curtas: "padrao" (o que os valores certos seguem), "analise" (o que esta
errado nos marcados) e "acao" (o que fazer). Campos que nao se aplicam vao null. Responda em JSON."""

_LISTA = {"type": ["array", "null"], "items": {"type": "string"}}
_PAR = {"type": "object", "additionalProperties": False, "required": ["sujo", "limpo"],
        "properties": {"sujo": {"type": "string"}, "limpo": {"type": "string"}}}
_COT = {"type": "object", "additionalProperties": False, "required": ["padrao", "analise", "acao"],
        "properties": {k: {"type": "string"} for k in ("padrao", "analise", "acao")}}
ESQUEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["estrategia", "transformacao", "determinantes", "distancia", "mapa", "raciocinio"],
    "properties": {
        "estrategia": {"type": "string", "enum": list(ESTRATEGIAS)},
        "transformacao": {"type": ["string", "null"]}, "determinantes": _LISTA,
        "distancia": {"type": ["integer", "null"]},
        "mapa": {"type": ["array", "null"], "items": _PAR}, "raciocinio": _COT,
    },
}


def especificar(deteccoes, entrada):
    """Uma chamada por deteccao aprovada; devolve as propostas de reparo validas."""
    propostas = []
    for candidata in deteccoes:
        mascara = detectar(entrada.sujo, candidata.coluna, candidata.tipo, candidata.parametros,
                           config.DOMINANCIA_MODA).fillna(False)
        try:
            resposta = provedor.cliente().pedir_json(
                "especificador", f"{candidata.coluna}/{candidata.tipo}", INSTRUCAO,
                _conteudo(candidata, entrada, mascara), ESQUEMA,
            )
        except provedor.FalhaDoLLM:
            # Degradacao nomeada: a deteccao fica sem reparo, e suas celulas viram flag.
            candidata.metricas["motivo_reparo"] = "sem_especificacao"
            continue
        parametros = _parametros(resposta, entrada, candidata.coluna, mascara)
        if parametros is None:
            candidata.metricas["motivo_reparo"] = "especificacao_invalida"
            continue
        propostas.append(Reparo(candidata=candidata, estrategia=resposta["estrategia"],
                                parametros=parametros, raciocinio=_raciocinio(resposta)))
    return propostas


def dominio(entrada, coluna, mascara):
    """Valores nao marcados com duas ou mais ocorrencias, mais os que o guia certifica."""
    contagem = entrada.sujo.loc[~mascara, coluna].value_counts()
    return sorted(set(contagem[contagem >= 2].index) | valores_certificados(entrada, coluna))


def _parametros(resposta, entrada, coluna, mascara):
    """Os parametros da estrategia no formato do motor, ou None se a resposta e invalida."""
    estrategia = resposta.get("estrategia")
    if estrategia == "normalizar":
        texto = resposta.get("transformacao")
        return {"transformacao": texto} if isinstance(texto, str) and texto else None
    if estrategia == "moda_condicionada":
        det = resposta.get("determinantes")
        valido = isinstance(det, list) and det and all(
            c in entrada.sujo.columns and c != coluna for c in det)
        return {"determinantes": det} if valido else None
    if estrategia == "vizinho_no_dominio":
        d = resposta.get("distancia")
        valido = isinstance(d, int) and not isinstance(d, bool) and 1 <= d <= 3
        return {"distancia": d, "dominio": dominio(entrada, coluna, mascara)} if valido else None
    if estrategia == "dicionario":
        mapa = {p["sujo"]: p["limpo"] for p in resposta.get("mapa") or []
                if isinstance(p, dict) and isinstance(p.get("sujo"), str)
                and isinstance(p.get("limpo"), str)}
        return {"mapa": mapa} if mapa else None
    if estrategia == "esvaziar":
        return {}
    return None


def _raciocinio(resposta):
    """As tres frases do CoT, numa linha."""
    cot = resposta.get("raciocinio")
    if not isinstance(cot, dict):
        return ""
    return " ".join(str(cot.get(k) or "") for k in ("padrao", "analise", "acao")).strip()


def _conteudo(candidata, entrada, mascara):
    """A regra, os valores que ela marcou, os exemplos do guia e os pares minerados."""
    coluna = candidata.coluna
    marcados = entrada.sujo.loc[mascara, coluna].value_counts().head(config.VALORES_NO_PROMPT)
    certificados = sorted(valores_certificados(entrada, coluna))[: config.VALORES_NO_PROMPT]
    linhas = [
        f"colunas da tabela: {', '.join(entrada.sujo.columns)}",
        f"coluna: {coluna}",
        f"regra de deteccao: {candidata.tipo} {candidata.parametros}",
        f"raciocinio do detector: {candidata.raciocinio}",
        f"valores marcados ({int(mascara.sum())} celulas): {[(v, int(n)) for v, n in marcados.items()]}",
        f"valores que o guia certifica: {certificados}",
    ]
    linhas += [f"exemplo do guia: {s!r} -> {c!r}" for s, c in exemplos_do_guia(entrada, coluna)]
    linhas += [f"par minerado: {det} -> {coluna}" for det, alvo in entrada.perfil.pares if alvo == coluna]
    decisao = entrada.decisao(coluna, candidata.tipo, candidata.parametros)
    if decisao and decisao.get("instrucao"):
        linhas.append("instrucao do usuario, valida desde que reproduza os exemplos do guia: "
                      + decisao["instrucao"])
    return "\n".join(linhas)

"""Etapa 2: agente detector -> predicados candidatos, uma chamada por coluna."""
import sys

from limpeza2 import config, provedor
from limpeza2.limites import exemplos_do_guia
from limpeza2.tipos import Candidata

CAMPOS = {
    "formato": ("regex",), "dominio": ("valores",), "faixa": ("minimo", "maximo"),
    "ausente_disfarcado": ("sentinelas",), "dependencia": ("determinantes",),
}

INSTRUCAO = """Voce e o agente detector de uma ferramenta de limpeza de dados.
Recebe o perfil de UMA coluna de uma tabela suja e propoe regras que apontam as celulas
erradas dela. Voce nao corrige nada: so detecta.
Cada regra e de um tipo do catalogo fechado, e voce so pode usar os tipos listados em "catalogo":
- formato: "regex" (sintaxe Python, casada com fullmatch) que todo valor VALIDO casa.
- dominio: "valores", a lista dos valores validos; o que estiver fora e erro.
- faixa: "minimo" e "maximo" numericos; numero fora da faixa e erro (texto nunca e marcado por faixa).
- ausente_disfarcado: "sentinelas", valores que significam ausencia (ex.: N/A, -, 0) no lugar de um dado.
- dependencia: "determinantes", colunas que determinam esta, escolhidas entre os pares minerados.
A linha "conformidade de schema" diz o que uma regra derivada do guia ja cobre nesta coluna.
Proponha ate 3 variantes por tipo, da mais estrita a mais permissiva, e so os tipos que fazem sentido.
Uma regra que marca celula que o guia mostra correta e reprovada; uma que marca mais de 30% da coluna
tambem. Preencha so os campos do tipo; os outros vao null. "raciocinio": uma frase.
Responda em JSON."""


def propor(entrada, schema, conformes):
    """Uma chamada por coluna; devolve as candidatas validas de todas as colunas."""
    candidatas = []
    for coluna in entrada.sujo.columns:
        tipos = catalogo(entrada, coluna, schema)
        conteudo = _conteudo(entrada, coluna, tipos, caso_da_conformidade(coluna, schema, conformes))
        try:
            resposta = provedor.cliente().pedir_json(
                "detector", coluna, INSTRUCAO, conteudo, _esquema(tipos)
            )
        except provedor.FalhaDoLLM:
            # Degradacao nomeada: a coluna fica sem regra do LLM; o motivo esta no registro.
            continue
        candidatas += _candidatas(coluna, resposta.get("regras"), tipos)
    return candidatas + herdadas(entrada, conformes + candidatas)


def herdadas(entrada, propostas):
    """As regras aprovadas pelo usuario que nao foram propostas de novo, como candidatas."""
    ja = [(c.coluna, c.tipo, c.parametros) for c in propostas]
    return [Candidata(coluna=d["coluna"], tipo=d["tipo"], parametros=d["parametros"],
                      raciocinio=f"aprovada pelo usuario na versao {d.get('versao') or '?'}")
            for d in entrada.decisoes
            if d["decisao"] == "aprovar" and d["tipo"] != "residual"
            and (d["coluna"], d["tipo"], d["parametros"]) not in ja]


def catalogo(entrada, coluna, schema):
    """Os tipos que o detector pode propor na coluna; ver a spec da parte 2, secao 3.2."""
    tipos = list(CAMPOS)
    if any(c.coluna == coluna for c in schema):
        tipos.remove("formato")
    if not any(determinado == coluna for _, determinado in entrada.perfil.pares):
        tipos.remove("dependencia")
    return tipos


def caso_da_conformidade(coluna, schema, conformes):
    """A frase que diz ao LLM o que a conformidade ja cobre na coluna."""
    if any(c.coluna == coluna for c in schema):
        return "aprovada: a forma ja esta coberta; procure erro de valor, de magnitude, de ausencia ou contextual"
    propria = [c for c in conformes if c.coluna == coluna]
    if not propria:
        return "sem schema: o guia mostra formatos variados, ou nao ha guia"
    motivo = propria[0].metricas.get("motivo")
    if motivo == "vacua":
        return "vacua: schema apertado sem nenhuma violacao; o erro, se existe, e contextual"
    return f"reprovada ({motivo}): existe schema, mas a regra dele nao passou"


def _conteudo(entrada, coluna, tipos, caso):
    """O perfil da coluna em uma linha por item, no estilo do catalogo do CatDB."""
    p = entrada.perfil.colunas[coluna]
    linhas = [
        f"colunas da tabela: {', '.join(entrada.sujo.columns)} ({len(entrada.sujo)} linhas)",
        f"coluna: {coluna}",
        f"catalogo: {', '.join(tipos)}",
        f"conformidade de schema: {caso}",
        f"distintos: {p['n_distintos']}; vazios: {p['n_vazios']}; comprimentos: {p['comprimentos']}",
        f"frequentes: {p['frequentes']}",
        f"raros: {p['raros']}",
        f"padroes: {p['padroes']}",
    ]
    linhas += [f"par minerado: {det} -> {coluna} {_arredondado(numeros)}"
               for (det, alvo), numeros in entrada.perfil.pares.items() if alvo == coluna]
    linhas += [f"exemplo do guia: {s!r} -> {c!r}" for s, c in exemplos_do_guia(entrada, coluna)]
    guia = (entrada.guia_linhas.to_csv(lineterminator=provedor.FIM_DE_LINHA)
            if len(entrada.guia_linhas) else "nenhuma\n")
    return "\n".join(linhas) + "\nlinhas corrigidas do guia:\n" + guia


def _arredondado(numeros):
    """Os numeros do par com tres casas, para o prompt."""
    return {k: round(v, 3) for k, v in numeros.items()}


def _esquema(tipos):
    """O esquema estrito de uma resposta: lista de variantes num objeto plano com nulos."""
    texto, numero = {"type": ["string", "null"]}, {"type": ["number", "null"]}
    lista = {"type": ["array", "null"], "items": {"type": "string"}}
    campos = {"tipo": {"type": "string", "enum": list(tipos)}, "regex": texto, "valores": lista,
              "minimo": numero, "maximo": numero, "sentinelas": lista, "determinantes": lista,
              "raciocinio": {"type": "string"}}
    variante = {"type": "object", "additionalProperties": False,
                "required": list(campos), "properties": campos}
    return {"type": "object", "additionalProperties": False, "required": ["regras"],
            "properties": {"regras": {"type": "array", "items": variante}}}


def _candidatas(coluna, regras, tipos):
    """Converte as variantes validas em Candidatas; a malformada cai sozinha."""
    candidatas, por_tipo = [], {}
    for regra in regras if isinstance(regras, list) else []:
        if not isinstance(regra, dict) or regra.get("tipo") not in tipos:
            continue
        tipo = regra["tipo"]
        parametros = {campo: regra.get(campo) for campo in CAMPOS[tipo]}
        if not _valida(tipo, parametros) or por_tipo.get(tipo, 0) >= config.VARIANTES_POR_TIPO:
            continue
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        candidatas.append(Candidata(coluna=coluna, tipo=tipo, parametros=parametros,
                                    raciocinio=str(regra.get("raciocinio") or "")))
    return candidatas


def _valida(tipo, parametros):
    """Os parametros tem a forma que o motor espera; regex invalida o crivo reprova como lancou."""
    if tipo == "formato":
        return isinstance(parametros["regex"], str) and parametros["regex"] != ""
    if tipo == "faixa":
        minimo, maximo = parametros["minimo"], parametros["maximo"]
        numeros = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (minimo, maximo))
        # O limite tem de caber num float finito: o motor o compara com pd.to_numeric.
        return numeros and all(abs(v) <= sys.float_info.max for v in (minimo, maximo)) and minimo <= maximo
    (lista,) = parametros.values()
    return isinstance(lista, list) and len(lista) > 0 and all(isinstance(v, str) for v in lista)

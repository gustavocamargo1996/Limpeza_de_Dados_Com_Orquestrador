"""Le o raciocinio do gerador e o traduz no relatorio de geracao, em linguagem de usuario."""
import ast
import re
from pathlib import Path

CONTRADIZ = {"marca_celula_correta", "marca_valor_certificado", "perde_par_do_guia",
             "corrompe_celula_do_guia", "contradiz_o_guia", "valor_certificado"}
MOTIVO = {
    "aprovada": "aprovada: passou em todos os testes e está no limpador",
    "superada": "outra variante do mesmo tipo, que marca menos células, ficou no lugar dela",
    "vacua": "não marcou nenhuma célula",
    "marca_demais": "marcou mais células do que a coluna admite",
    "ambigua": "a coluna determinante não decide o valor desta",
    "sem_perfil": "não há relação minerada entre as colunas que ela cita",
    "lancou": "quebrou ao rodar",
    "marca_celula_correta": "marcou como erro uma célula que você confirmou como correta no guia",
    "marca_valor_certificado": "marcou como erro um valor que o guia mostra como correto",
    "perde_par_do_guia": "não marca um erro que o guia aponta",
    "rejeitada_pelo_usuario": "rejeitada por você",
}
REPARO = {
    "aprovada": "o reparo está no limpador",
    "nao_repara": "o reparo não mudou nenhuma célula; as marcadas ficam só sinalizadas",
    "sem_especificacao": "o especificador não respondeu",
    "especificacao_invalida": "o especificador respondeu fora do catálogo",
    "codigo_rejeitado": "a função escrita pelo LLM não passou no portão de segurança",
    "lancou": "o reparo quebrou ao rodar",
    "corrompe_celula_do_guia": "escreveria numa célula do guia um valor diferente do guia",
    "perde_par_do_guia": "não reproduz a correção que o guia mostra",
}
CAIDA = {"contradiz_o_guia": "contradiz um exemplo do guia",
         "valor_certificado": "trocaria um valor que o guia certifica",
         "conflitante": "sugestões conflitantes para o mesmo valor",
         "rejeitada_pelo_usuario": "rejeitada por você"}
CAMPOS = {"raciocinio": "raciocinio", "reparo": "reparo", "raciocinio do reparo": "raciocinio_reparo"}


def _valor(texto):
    """O valor literal de uma metrica, ou o proprio texto quando nao e literal."""
    try:
        return ast.literal_eval(texto)
    except (ValueError, SyntaxError):
        return texto


def _linha_do_residual(residual, corpo):
    """Acrescenta ao residual uma entrada do mapa ou uma caida."""
    if achado := re.fullmatch(r"caiu `(.*)`: (\w+).*", corpo):
        residual["caidas"].append(achado.groups())
    elif achado := re.fullmatch(r"`(.*)` -> `(.*)`: (.*)", corpo):
        residual["mapa"].append(achado.groups())


def ler(caminho):
    """O raciocinio em dict: cabecalho e, por coluna, candidatas, residual e registro."""
    cabecalho, colunas, coluna, atual, codigo = {}, {}, None, None, False
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        if linha.startswith("```"):
            codigo = not codigo
        elif codigo:
            continue
        elif linha.startswith("## "):
            coluna, atual = linha[3:], None
            if coluna != "Outras anotacoes do registro":
                colunas[coluna] = {"candidatas": [], "registro": [],
                                   "residual": {"mapa": [], "caidas": []}}
        elif linha.startswith("### "):
            tipo, _, motivo = linha[4:].partition(": ")
            atual = "residual" if tipo == "residual" else {"tipo": tipo, "motivo": motivo,
                                                           "metricas": {}}
            if atual != "residual":
                colunas[coluna]["candidatas"].append(atual)
        elif linha.startswith("- "):
            corpo = linha[2:]
            chave, _, valor = corpo.partition(": ")
            if coluna is None:
                cabecalho[chave] = valor
            elif coluna not in colunas:
                continue
            elif chave == "registro":
                colunas[coluna]["registro"].append(valor)
            elif atual == "residual":
                _linha_do_residual(colunas[coluna]["residual"], corpo)
            elif atual is not None and chave == "parametros":
                atual["parametros"] = ast.literal_eval(valor.strip("`"))
            elif atual is not None:
                if chave in CAMPOS:
                    atual[CAMPOS[chave]] = valor
                else:
                    atual["metricas"][chave] = _valor(valor)
    return {"cabecalho": cabecalho, "colunas": colunas}


def descrever(c):
    """O que a regra exige, em linguagem de usuario."""
    p, lista = c.get("parametros", {}), lambda v: ", ".join(f"`{x}`" for x in v[:12])
    return {
        "conformidade": lambda: f"os valores têm de seguir o formato que o guia mostra: {lista(p['padroes'])}",
        "formato": lambda: f"os valores têm de casar com a expressão `{p['regex']}`",
        "dominio": lambda: f"os valores têm de estar na lista: {lista(p['valores'])}",
        "faixa": lambda: f"os números têm de estar entre {p['minimo']} e {p['maximo']}",
        "ausente_disfarcado": lambda: f"estes valores significam ausência: {lista(p['sentinelas'])}",
        "dependencia": lambda: f"o valor é determinado por {', '.join(p['determinantes'])}",
    }.get(c["tipo"], lambda: f"{c['tipo']} {p}")()


def contradiz(c):
    """A candidata foi reprovada por contradizer o guia: o usuario nao pode aprova-la."""
    return c["motivo"] in CONTRADIZ or c["metricas"].get("motivo_reparo") in CONTRADIZ


def justificar(c):
    """A situacao da candidata e do reparo dela, em linguagem de usuario."""
    texto = MOTIVO.get(c["motivo"], c["motivo"])
    reparo = c["metricas"].get("motivo_reparo")
    if c["motivo"] == "aprovada" and reparo:
        texto += f"; reparo: {REPARO.get(reparo, reparo)}"
    return texto


def _marca(c):
    """As marcas da regra: decisao do usuario, heranca e contradicao ao guia."""
    marcas = []
    if c.get("raciocinio", "").startswith("aprovada pelo usuario"):
        marcas.append("herdada de versão anterior")
    if decisao := c["metricas"].get("decisao"):
        marcas.append("aprovada por você" if decisao == "aprovar" else "rejeitada por você")
    if contradiz(c):
        marcas.append("**contradiz o guia**")
    return f" ({'; '.join(marcas)})" if marcas else ""


def montar(raciocinio, parametros, sorteio, chamadas, truncada):
    """O relatorio de geracao em Markdown."""
    total, novas = chamadas
    cab = raciocinio["cabecalho"]
    base = ("tabela inteira" if (parametros or {}).get("base") == "inteira"
            else f"amostra de {(parametros or {}).get('tamanho', '?')} linhas")
    trocas = len((sorteio or {}).get("trocas", []))
    linhas = ["# Relatório de geração", "",
              f"- modelo: {cab.get('modelo', '?')}; {total} chamadas ({novas} novas)",
              f"- supervisão: {cab.get('supervisao', '?')}; {trocas} troca(s) de \"sortear de novo\"",
              f"- base da geração: {base}, semente {(parametros or {}).get('semente', '?')}"]
    if truncada:
        linhas += ["", "> **GERAÇÃO TRUNCADA** pelo teto de chamadas: esta versão não pode ser aprovada."]
    for coluna, dados in raciocinio["colunas"].items():
        linhas += ["", f"## {coluna}"]
        for c in dados["candidatas"]:
            linhas += ["", f"- **{c['tipo']}**: {descrever(c)}{_marca(c)}",
                       f"  - situação: {justificar(c)}"]
            if c.get("reparo"):
                linhas.append(f"  - reparo `{c['reparo']}`: {c.get('raciocinio_reparo', '')}")
            if c.get("raciocinio"):
                linhas.append(f"  - raciocínio do detector: {c['raciocinio']}")
        for sujo, limpo, _ in dados["residual"]["mapa"]:
            linhas.append(f"- residual: `{sujo}` → `{limpo}`")
        for sujo, motivo in dados["residual"]["caidas"]:
            linhas.append(f"- residual caído: `{sujo}`, {CAIDA.get(motivo, motivo)}")
    linhas += ["", "## Limites conhecidos", "",
               "- O dicionário residual e o domínio de `vizinho_no_dominio` só cobrem valores já vistos.",
               "- Nenhuma regra move um valor de uma coluna para outra."]
    return "\n".join(linhas) + "\n"

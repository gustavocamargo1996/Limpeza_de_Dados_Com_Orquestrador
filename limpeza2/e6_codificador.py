"""Etapa 6: agente codificador -> escreve os artefatos de saida."""
from limpeza2 import config, portao, provedor
from limpeza2.limites import exemplos_do_guia
from limpeza2.motor import detectar

INSTRUCAO = """Voce e o agente codificador de uma ferramenta de limpeza de dados.
Traduza a transformacao pedida numa funcao Python pura, exatamente com esta assinatura:

def corrigir(valor):
    ...
    return novo_valor

Regras: recebe e devolve str; sem import (o modulo re ja esta disponivel); sem arquivo, rede,
eval, exec, getattr nem nomes com __; sem .format (use f-string ou concatenacao).
Se a transformacao nao se aplica ao valor, devolva o valor sem mudanca.
Os exemplos sujo -> limpo do guia sao corretos: a funcao tem de reproduzi-los.
Responda em JSON com o campo "codigo", que contem so a definicao da funcao."""
ESQUEMA = {"type": "object", "additionalProperties": False, "required": ["codigo"],
           "properties": {"codigo": {"type": "string"}}}


def codificar(propostas, entrada):
    """Escreve uma corrigir(valor) por proposta normalizar; devolve (codificadas, funcoes)."""
    codificadas, funcoes = [], {}
    for proposta in propostas:
        if proposta.estrategia == "normalizar":
            funcao = _funcao(proposta, entrada)
            if funcao is None:
                proposta.candidata.metricas["motivo_reparo"] = "codigo_rejeitado"
                continue
            nome = f"corrigir_{len(funcoes) + 1}"
            funcoes[nome] = funcao
            proposta.parametros["funcao"] = nome
        codificadas.append(proposta)
    return codificadas, funcoes


def _funcao(proposta, entrada):
    """Pede o codigo e o passa no portao; uma nova tentativa com a mensagem do portao."""
    c = proposta.candidata
    mascara = detectar(entrada.sujo, c.coluna, c.tipo, c.parametros, config.DOMINANCIA_MODA).fillna(False)
    exemplos = exemplos_do_guia(entrada, c.coluna)
    amostras = sorted(set(entrada.sujo.loc[mascara, c.coluna]))[: config.VALORES_NO_PROMPT]
    conteudo = "\n".join([
        f"coluna: {c.coluna}", f"transformacao: {proposta.parametros['transformacao']}",
        f"valores a corrigir: {amostras}",
        *[f"exemplo do guia: {s!r} -> {limpo!r}" for s, limpo in exemplos],
    ])
    for _ in range(2):
        try:
            resposta = provedor.cliente().pedir_json(
                "codificador", f"{c.coluna}/{c.tipo}", INSTRUCAO, conteudo, ESQUEMA)
            codigo = str(resposta.get("codigo"))
            funcao = portao.materializar(codigo)
            portao.testar_fumaca(funcao, amostras + [s for s, _ in exemplos])
        except provedor.FalhaDoLLM:
            # Degradacao nomeada: a regra fica sem reparo; o motivo esta no registro.
            return None
        except portao.CodigoRejeitado as erro:
            c.metricas["detalhe_reparo"] = str(erro)
            conteudo += f"\n\nA tentativa anterior foi rejeitada: {erro}\ncodigo rejeitado:\n{codigo}"
            continue
        proposta.codigo = codigo
        return funcao
    return None

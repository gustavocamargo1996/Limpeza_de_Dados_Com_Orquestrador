"""Apoio dos testes: entrada montada a mao e o duble do provedor de LLM."""
import json

import pandas as pd

from limpeza2.tipos import Entrada, Perfil


def monta_entrada(sujo, linhas_guia=(), pares=(), corrigidos=None):
    """O guia traz o valor do sujo, salvo nas celulas de `corrigidos` {(linha, coluna): valor}."""
    guia_linhas = sujo.loc[list(linhas_guia)].copy() if linhas_guia else pd.DataFrame(
        columns=sujo.columns
    )
    for (linha, coluna), valor in (corrigidos or {}).items():
        guia_linhas.at[linha, coluna] = valor
    guia_pares = pd.DataFrame(
        list(pares), columns=["linha", "coluna", "sujo", "limpo"]
    ) if pares else pd.DataFrame(columns=["linha", "coluna", "sujo", "limpo"])
    return Entrada(
        sujo=sujo,
        guia_linhas=guia_linhas,
        guia_pares=guia_pares,
        perfil=Perfil(colunas={}, pares={}, candidatas_sujeito=[]),
    )


def ok(dados):
    """A resposta crua de uma chamada que deu certo."""
    return {"texto": json.dumps(dados), "fim": "stop", "tokens": 5, "recusa": None}


CORTADA = {"texto": "", "fim": "length", "tokens": 0, "recusa": None}


class Roteiro:
    """API falsa: responde o que `responder(instrucao, conteudo)` devolver e guarda os pedidos."""

    def __init__(self, responder):
        self.responder_fn, self.pedidos = responder, []

    def responder(self, chave, instrucao, conteudo, esquema):
        self.pedidos.append((instrucao, conteudo))
        resposta = self.responder_fn(instrucao, conteudo)
        if isinstance(resposta, Exception):
            raise resposta
        # Resposta crua (com "fim" ou "rede") passa direto; dict de dados vira resposta valida.
        return resposta if ("fim" in resposta or "rede" in resposta) else ok(resposta)


def em_fila(*respostas):
    """Um Roteiro que devolve as respostas na ordem, uma por chamada."""
    fila = list(respostas)
    return Roteiro(lambda instrucao, conteudo: fila.pop(0))

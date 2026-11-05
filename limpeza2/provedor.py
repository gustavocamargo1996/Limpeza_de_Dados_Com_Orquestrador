"""Entrega o cliente do provedor de LLM escolhido; nenhum outro modulo conhece provedor."""
import hashlib
import json
from pathlib import Path

import openai

from limpeza2 import config

# Falhas transitorias que o SDK ja tentou de novo; viram FalhaDoLLM("rede").
_REDE = (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)
_atual = None


class FalhaDoLLM(Exception):
    """Chamada que falhou com degradacao nomeada: a unidade fica sem regra."""

    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


def iniciar(destino):
    """Abre uma geracao: registro e contador zerados, respostas gravadas em `destino`."""
    global _atual
    _atual = Cliente(Path(destino), _construir_api())
    return _atual


def cliente():
    """O cliente da geracao aberta por `iniciar`."""
    if _atual is None:
        raise RuntimeError("provedor.iniciar(destino) nao foi chamado")
    return _atual


def _construir_api():
    """A API do provedor em config.PROVEDOR; valor desconhecido levanta."""
    provedor = config.PROVEDOR.strip().lower()
    if provedor in ("openai", "ollama"):
        return _api_viva(provedor)
    if provedor == "gravado":
        return _Gravado(Path(config.RESPOSTAS_GRAVADAS))
    if provedor == "reaproveitar":
        return _Reaproveitar(_Gravado(Path(config.RESPOSTAS_GRAVADAS)),
                             _api_viva(config.PROVEDOR_VIVO.strip().lower()))
    raise ValueError(
        f"PROVEDOR={provedor!r} nao e suportado. Use openai, ollama, gravado ou reaproveitar. "
        "Nao caio para openai em silencio: isso mandaria dado para fora da rede."
    )


def _api_viva(provedor):
    """A API de rede de `provedor`; so openai e ollama existem."""
    if provedor == "openai":
        return _Api(esforco=config.ESFORCO_RACIOCINIO)
    if provedor == "ollama":
        return _Api(esforco=None, base_url=config.OLLAMA_URL, api_key="ollama")
    raise ValueError(
        f"PROVEDOR_VIVO={provedor!r} nao e suportado. Use openai ou ollama. "
        "Nao caio para openai em silencio: isso mandaria dado para fora da rede."
    )


class Cliente:
    """Pede JSON ao modelo, grava cada resposta crua e anota cada chamada no registro."""

    def __init__(self, destino, api):
        destino.mkdir(parents=True, exist_ok=True)
        self.api, self.registro, self.chamadas = api, [], 0
        # A origem abre o arquivo; o replay a le dele e a regrava igual.
        self.origem = getattr(api, "origem", None) or {
            "provedor": config.PROVEDOR, "modelo": config.MODELO,
            "esforco": config.ESFORCO_RACIOCINIO,
        }
        self.arquivo = destino / "respostas.jsonl"
        linha = json.dumps({"origem": self.origem}, ensure_ascii=False)
        self.arquivo.write_text(linha + "\n", encoding="utf-8")

    def anotar(self, etapa, unidade, status, detalhe=""):
        """Acrescenta uma nota ao registro da geracao e a devolve."""
        nota = {"etapa": etapa, "unidade": unidade, "status": status, "detalhe": detalhe, "tokens": 0}
        self.registro.append(nota)
        return nota

    def pedir_json(self, etapa, unidade, instrucao, conteudo, esquema):
        """Uma chamada: devolve o dict da resposta ou levanta FalhaDoLLM."""
        if self.chamadas >= config.TETO_CHAMADAS:
            self.anotar(etapa, unidade, "teto")
            raise FalhaDoLLM("teto")
        self.chamadas += 1
        chave = hashlib.sha256(json.dumps([instrucao, conteudo]).encode()).hexdigest()
        try:
            bruto = self.api.responder(chave, instrucao, conteudo, esquema)
        except _REDE:
            bruto = {"rede": True}
        with self.arquivo.open("a", encoding="utf-8") as saida:
            saida.write(json.dumps({"chave": chave, "etapa": etapa, "unidade": unidade,
                                    "bruto": bruto}, ensure_ascii=False) + "\n")
        nota = self.anotar(etapa, unidade, "ok")
        nota["tokens"] = bruto.get("tokens", 0)
        motivo, dados = _interpretar(bruto)
        if motivo:
            nota["status"] = motivo
            raise FalhaDoLLM(motivo)
        return dados


def _interpretar(bruto):
    """O motivo da falha e None, ou None e o dict da resposta."""
    if bruto.get("rede"):
        return "rede", None
    if bruto.get("recusa"):
        return "recusada", None
    if bruto.get("fim") == "length":
        return "cortada", None
    try:
        dados = json.loads(bruto.get("texto") or "")
    except json.JSONDecodeError:
        return "json_invalido", None
    return (None, dados) if isinstance(dados, dict) else ("json_invalido", None)


class _Api:
    """Chat Completions do SDK openai, que serve a OpenAI e ao Ollama."""

    def __init__(self, esforco, **conexao):
        self.sdk = openai.OpenAI(
            timeout=config.TIMEOUT_LLM, max_retries=config.TENTATIVAS_API, **conexao
        )
        self.esforco = esforco

    def responder(self, chave, instrucao, conteudo, esquema):
        """A resposta crua: texto, motivo de parada, tokens e recusa."""
        if config.SAIDA_ESTRITA:
            formato = {"type": "json_schema",
                       "json_schema": {"name": "resposta", "strict": True, "schema": esquema}}
        else:
            formato = {"type": "json_object"}
            instrucao += "\nResponda em JSON com este esquema: " + json.dumps(esquema)
        opcionais = {"temperature": config.TEMPERATURA, "seed": config.SEMENTE,
                     "reasoning_effort": self.esforco}
        resposta = self.sdk.chat.completions.create(
            model=config.MODELO, response_format=formato,
            messages=[{"role": "system", "content": instrucao},
                      {"role": "user", "content": conteudo}],
            **{k: v for k, v in opcionais.items() if v is not None},
        )
        escolha = resposta.choices[0]
        return {"texto": escolha.message.content, "fim": escolha.finish_reason,
                "tokens": resposta.usage.total_tokens if resposta.usage else 0,
                "recusa": getattr(escolha.message, "refusal", None)}


class _Gravado:
    """Reproduz um respostas.jsonl, na ordem em que cada chamada foi feita."""

    def __init__(self, caminho):
        self.fila, self.origem = {}, None
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            registro = json.loads(linha)
            if "origem" in registro:
                self.origem = registro["origem"]
            else:
                self.fila.setdefault(registro["chave"], []).append(registro["bruto"])

    def responder(self, chave, instrucao, conteudo, esquema):
        """A proxima resposta gravada para esta chamada; ausente levanta, nao degrada."""
        if not self.fila.get(chave):
            raise KeyError(f"resposta nao gravada para a chamada {chave}")
        return self.fila[chave].pop(0)


class _Reaproveitar:
    """Responde do respostas.jsonl gravado e chama a API viva so para o que falta."""

    def __init__(self, gravado, vivo):
        modelo = (gravado.origem or {}).get("modelo")
        if modelo != config.MODELO:
            raise ValueError(f"MODELO={config.MODELO!r} difere do gravado {modelo!r}: "
                             "uma versao com respostas de dois modelos seria inexplicavel")
        self.gravado, self.vivo, self.origem = gravado, vivo, gravado.origem

    def responder(self, chave, instrucao, conteudo, esquema):
        """A resposta gravada desta chamada ou, sem ela ou se ela falhou por rede, a da API viva."""
        if self.gravado.fila.get(chave):
            bruto = self.gravado.responder(chave, instrucao, conteudo, esquema)
            # Falha de rede e transitoria: repeti-la congelaria a coluna sem regra para sempre.
            if not bruto.get("rede"):
                return bruto
        return self.vivo.responder(chave, instrucao, conteudo, esquema)

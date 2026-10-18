"""Caminhos, limiares, semente e modelo: a unica configuracao ajustavel."""
import os
from fractions import Fraction
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
GUIA = RAIZ / "dados" / "guia"
SAIDA = RAIZ / "saida"

LER_CSV = {"dtype": str, "keep_default_na": False, "na_values": []}

SEMENTE = 20261011
LINHAS_GUIA = 20
PARES_POR_COLUNA = 2

# Fixados a priori: calibrar com o gabarito seria vazamento.
# Ver docs/DECISOES.md#teto-de-marcacao.
TETO_MARCACAO = 0.30
DOMINANCIA_MODA = 0.70
TETO_AMBIGUIDADE = 0.30
# DET_MINIMO e o complemento de TETO_MARCACAO: ninguem acredita em coluna mais de 30% errada.
DET_MINIMO = 0.70
COBERTURA_MINIMA = 0.50
GRUPOS_MINIMOS_PAR = 2
VARIANTES_POR_TIPO = 3
# Coluna tem schema se os padroes distintos do guia forem no maximo esta fracao das linhas.
FRACAO_PADROES_SCHEMA = Fraction(1, 3)

PROVEDOR = os.getenv("PROVEDOR", "openai")
MODELO = os.getenv("MODELO", "gpt-6-luna")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
# O respostas.jsonl que PROVEDOR=gravado reproduz.
RESPOSTAS_GRAVADAS = os.getenv("RESPOSTAS_GRAVADAS", "")
# A API que PROVEDOR=reaproveitar chama para o que nao tem resposta gravada.
PROVEDOR_VIVO = os.getenv("PROVEDOR_VIVO", "")
# So com raciocinio em none o modelo aceita temperature; None tira o parametro do pedido.
ESFORCO_RACIOCINIO = "none"
TEMPERATURA = 0
SAIDA_ESTRITA = True
TIMEOUT_LLM = 120
TENTATIVAS_API = 2
TETO_CHAMADAS = 80
VALORES_NO_PROMPT = 30
LINHAS_POR_LOTE = 40
MAX_LOTES_RESIDUAL = 10

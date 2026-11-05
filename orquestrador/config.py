"""Endpoint, bucket, caminhos e tamanhos padrao: a unica configuracao do orquestrador."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://127.0.0.1:8333")
S3_BUCKET = os.getenv("S3_BUCKET", "limpeza")
SQLITE = Path(os.getenv("SQLITE", RAIZ / "var" / "controle.sqlite"))
TRABALHO = Path(os.getenv("TRABALHO", RAIZ / "var" / "trabalho"))
# O Python que roda o app roda tambem os filhos (gerador e limpador).
PYTHON = sys.executable
PROVEDOR = os.getenv("PROVEDOR", "openai")
MODELO = os.getenv("MODELO", "gpt-6-luna")

LER_CSV = {"dtype": str, "keep_default_na": False, "na_values": []}
DOMINIOS = ("Meio Ambiente", "Segurança", "Transporte", "Demografia", "Economia", "Saúde",
            "Educação", "Outros")

LINHAS_GUIA_PADRAO = 20
LINHAS_GUIA_MINIMO = 10
AMOSTRA_PADRAO = 300
AMOSTRA_MINIMO = 100
# Acima disto a geracao sai do regime medido: 300 linhas e 11 colunas.
REGIME_TESTADO = 300
SEMENTE = 20261017
TIMEOUT_GERACAO = 1800
TIMEOUT_APLICACAO = 600
CELULAS_POR_REGRA = 5

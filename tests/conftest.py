"""Fixtures compartilhadas: o provedor de mentira."""
import pytest

from limpeza2 import provedor
from tests.apoio import Roteiro


@pytest.fixture
def roteiro(monkeypatch, tmp_path):
    """Abre uma geracao com a API falsa; devolve a funcao que instala as respostas."""
    def instalar(responder, destino=None):
        api = Roteiro(responder)
        monkeypatch.setattr(provedor, "_construir_api", lambda: api)
        provedor.iniciar(destino or tmp_path / "geracao")
        return api
    return instalar

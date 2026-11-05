"""Fixtures do orquestrador: SQLite e pasta de trabalho em tmp, e o bucket simulado pelo moto."""
import pytest
from moto import mock_aws

from orquestrador import config, controle


@pytest.fixture(autouse=True)
def isolado(tmp_path, monkeypatch):
    """Nenhum teste toca o var/ do repositorio."""
    monkeypatch.setattr(config, "SQLITE", tmp_path / "var" / "controle.sqlite")
    monkeypatch.setattr(config, "TRABALHO", tmp_path / "var" / "trabalho")


@pytest.fixture
def con():
    return controle.conectar()


@pytest.fixture
def lago_falso(monkeypatch):
    """O S3 em memoria do moto, atendendo no endpoint do SeaweedFS."""
    monkeypatch.setenv("MOTO_S3_CUSTOM_ENDPOINTS", config.S3_ENDPOINT)
    with mock_aws():
        yield

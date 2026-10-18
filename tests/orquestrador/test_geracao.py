"""O filho do gerador: etapa pelo respostas.jsonl, contagem de chamadas e um disparo real offline."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from orquestrador import geracao

RAIZ = Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "tests" / "fixtures"


def grava(pasta, etapas, final=""):
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = [json.dumps({"origem": {}})] + [
        json.dumps({"chave": f"k{i}", "etapa": e, "unidade": "u", "bruto": {}})
        for i, e in enumerate(etapas)]
    (pasta / "respostas.jsonl").write_text("\n".join(linhas) + "\n" + final, encoding="utf-8")


def test_etapa_corrente_pela_ultima_chamada(tmp_path):
    assert geracao.etapa_corrente(tmp_path / "nada") == 4
    for etapas, esperada in [([], 4), (["detector"], 4), (["detector", "especificador"], 5),
                             (["especificador", "residual"], 5), (["residual", "codificador"], 6)]:
        grava(tmp_path / "g", etapas)
        assert geracao.etapa_corrente(tmp_path / "g") == esperada, etapas


def test_linha_final_pela_metade_e_ignorada(tmp_path):
    grava(tmp_path / "g", ["detector", "especificador"], final='{"chave": "k9", "eta')
    assert geracao.etapa_corrente(tmp_path / "g") == 5


def test_chamadas_novas_contam_o_que_nao_veio_do_anterior(tmp_path):
    grava(tmp_path / "antes", ["detector", "detector"])
    (tmp_path / "depois").mkdir()
    linhas = [json.dumps({"origem": {}})] + [json.dumps({"chave": c, "etapa": "detector"})
                                             for c in ("k0", "k0", "k1", "kz")]
    (tmp_path / "depois" / "respostas.jsonl").write_text("\n".join(linhas), encoding="utf-8")
    assert geracao.chamadas(tmp_path / "depois") == (4, 4)
    assert geracao.chamadas(tmp_path / "depois", tmp_path / "antes" / "respostas.jsonl") == (4, 2)


def test_vivo_distingue_processo_rodando_de_encerrado():
    assert geracao.vivo(os.getpid())
    filho = subprocess.Popen([sys.executable, "-c", "pass"])
    filho.wait()
    assert not geracao.vivo(filho.pid)
    dorminhoco = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    assert geracao.vivo(dorminhoco.pid)
    geracao.encerrar(dorminhoco.pid)
    dorminhoco.wait(timeout=30)
    assert not geracao.vivo(dorminhoco.pid)


def test_disparo_real_offline_reproduz_o_mvp(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVEDOR", "gravado")
    monkeypatch.setenv("RESPOSTAS_GRAVADAS", str(FIXTURES / "respostas_beers_poc2.jsonl"))
    destino = tmp_path / "beers_2026-10-12_2152"
    filho = geracao.disparar(FIXTURES / "beers_dirty_300.csv", RAIZ / "dados" / "guia" / "beers", destino)
    assert geracao.situacao(destino, filho.pid) in ("rodando", "ok")
    filho.wait(timeout=600)
    time.sleep(0.2)
    assert geracao.situacao(destino, filho.pid) == "ok", geracao.erro(destino)
    gerado = (destino / "limpador_beers_2026-10-12_2152.py").read_bytes().replace(b"\r\n", b"\n")
    assert gerado == (FIXTURES / "limpador_beers_poc2.py").read_bytes().replace(b"\r\n", b"\n")
    assert geracao.chamadas(destino) == (31, 31)
    # O residual roda depois do codificador: a ultima chamada e dele, e o painel
    # nao volta atras porque o fluxo guarda a maior etapa ja vista.
    assert geracao.etapa_corrente(destino) == 5


def test_filho_que_falha_fica_em_erro_com_o_log(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVEDOR", "gravado")
    monkeypatch.setenv("RESPOSTAS_GRAVADAS", str(FIXTURES / "respostas_beers_poc2.jsonl"))
    destino = tmp_path / "v1"
    filho = geracao.disparar(tmp_path / "nao_existe.csv", None, destino)
    filho.wait(timeout=300)
    assert geracao.situacao(destino, filho.pid) == "erro"
    assert "nao_existe.csv" in geracao.erro(destino)


def test_reaproveitar_usa_como_api_viva_o_provedor_que_a_tela_anuncia(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "ollama")
    monkeypatch.setenv("PROVEDOR_VIVO", "openai")
    ambiente = geracao.ambiente(Path("a/respostas.jsonl"))
    assert (ambiente["PROVEDOR"], ambiente["PROVEDOR_VIVO"]) == ("reaproveitar", "ollama")
    assert ambiente["RESPOSTAS_GRAVADAS"] == str(Path("a/respostas.jsonl"))
    # So com PROVEDOR=gravado (testes e desenvolvimento) o PROVEDOR_VIVO do ambiente vale.
    monkeypatch.setenv("PROVEDOR", "gravado")
    assert geracao.ambiente(Path("x"))["PROVEDOR_VIVO"] == "openai"
    assert geracao.ambiente(None)["PROVEDOR"] == "gravado"


def test_vivo_confere_a_hora_de_criacao_contra_pid_reaproveitado():
    filho = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    agora = time.time()
    assert geracao.vivo(filho.pid, agora)
    assert not geracao.vivo(filho.pid, agora - 3600)
    geracao.encerrar(filho.pid)
    filho.wait(timeout=30)


def test_falha_de_rede_gravada_conta_como_chamada_nova(tmp_path):
    (tmp_path / "antes").mkdir()
    (tmp_path / "antes" / "respostas.jsonl").write_text("\n".join([
        json.dumps({"origem": {}}), json.dumps({"chave": "k0", "bruto": {"rede": True}}),
        json.dumps({"chave": "k1", "bruto": {"texto": "{}"}})]), encoding="utf-8")
    grava(tmp_path / "depois", ["detector", "detector"])
    assert geracao.chamadas(tmp_path / "depois", tmp_path / "antes" / "respostas.jsonl") == (2, 1)

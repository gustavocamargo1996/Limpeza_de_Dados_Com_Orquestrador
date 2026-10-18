"""O bucket: nomes de pasta, layout da especificacao, hash na metadado e o aviso de fora do ar."""
import pytest

from orquestrador import config, lago


def test_nome_de_pasta_em_ascii():
    assert lago.nome_de_pasta("Meio Ambiente") == "Meio_Ambiente"
    assert lago.nome_de_pasta("Saúde") == "Saude"
    assert lago.nome_de_pasta(" cervejas/2026 ") == "cervejas_2026"


def test_prefixo_segue_o_layout_da_especificacao():
    assert lago.prefixo("Meio Ambiente", "beers", "Original", "2026-10-17_101500") == (
        "Meio_Ambiente/beers/Original/2026-10-17_101500")


def test_envia_lista_e_baixa_com_o_hash_na_metadado(lago_falso, tmp_path):
    assert lago.disponivel()
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "dados.csv").write_bytes(b"x,y\n1,2\n")
    (tmp_path / "a" / "flags.csv").write_bytes(b"x\nTrue\n")
    prefixo = lago.prefixo("Outros", "beers", "Corrigido", "t1")
    lago.enviar(tmp_path / "a" / "dados.csv", f"{prefixo}/dados.csv", {"sha256": "abc"})
    assert lago.enviar_pasta(tmp_path / "a", prefixo, nomes=["flags.csv"]) == [f"{prefixo}/flags.csv"]
    assert lago.listar("Outros/beers/") == [f"{prefixo}/dados.csv", f"{prefixo}/flags.csv"]
    assert lago.metadados(f"{prefixo}/dados.csv") == {"sha256": "abc"}
    destino = lago.baixar_pasta(prefixo, tmp_path / "b")
    assert (destino / "dados.csv").read_bytes() == b"x,y\n1,2\n"
    assert sorted(p.name for p in destino.iterdir()) == ["dados.csv", "flags.csv"]


def test_pastas_irmas_nao_se_misturam(lago_falso, tmp_path):
    lago.disponivel()
    (tmp_path / "f.txt").write_text("1")
    lago.enviar(tmp_path / "f.txt", "Outros/beers/Limpador/t1/f.txt")
    lago.enviar(tmp_path / "f.txt", "Outros/beers/Limpador/t10/f.txt")
    assert [p.name for p in lago.baixar_pasta("Outros/beers/Limpador/t1", tmp_path / "b").iterdir()] == ["f.txt"]
    assert lago.subpastas("Outros/beers/Limpador") == ["t1", "t10"]


def test_bucket_fora_do_ar_e_falso(monkeypatch):
    monkeypatch.setattr(config, "S3_ENDPOINT", "http://127.0.0.1:9")
    assert lago.disponivel() is False


@pytest.mark.parametrize("texto", ["", "   ", "///"])
def test_nome_sem_letra_nem_digito_fica_vazio(texto):
    assert lago.nome_de_pasta(texto).strip("_") == ""

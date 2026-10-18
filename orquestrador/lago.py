"""Le e grava artefatos no bucket S3 do SeaweedFS, no layout da especificacao."""
import unicodedata
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from orquestrador import config


def cliente():
    """O cliente S3 do SeaweedFS local, que aceita acesso anonimo."""
    return boto3.client(
        "s3", endpoint_url=config.S3_ENDPOINT, aws_access_key_id="local",
        aws_secret_access_key="local", region_name="us-east-1",
        config=Config(connect_timeout=3, read_timeout=60, retries={"max_attempts": 2}),
    )


def disponivel():
    """O bucket responde; ele e criado no primeiro uso."""
    s3 = cliente()
    try:
        if config.S3_BUCKET not in {b["Name"] for b in s3.list_buckets().get("Buckets", [])}:
            s3.create_bucket(Bucket=config.S3_BUCKET)
    except (BotoCoreError, ClientError):
        # Degradacao nomeada: a interface avisa e bloqueia a ingestao.
        return False
    return True


def nome_de_pasta(texto):
    """O texto em ASCII, com _ no lugar de espaco e do que nao for letra, digito ou hifen."""
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() or c == "-" else "_" for c in ascii_.strip())


def prefixo(dominio, esquema, area, carimbo):
    """A pasta `<Dominio>/<Esquema>/<area>/<carimbo>` no bucket."""
    return f"{nome_de_pasta(dominio)}/{nome_de_pasta(esquema)}/{area}/{carimbo}"


def enviar(local, chave, metadados=None):
    """Grava um arquivo local no bucket, com metadados opcionais."""
    extra = {"Metadata": metadados} if metadados else {}
    cliente().put_object(Bucket=config.S3_BUCKET, Key=chave, Body=Path(local).read_bytes(), **extra)


def enviar_pasta(pasta, prefixo_, nomes=None):
    """Grava os arquivos da pasta (todos, ou so `nomes`) sob o prefixo; devolve as chaves."""
    arquivos = sorted(p for p in Path(pasta).iterdir() if p.is_file())
    chaves = []
    for arquivo in (a for a in arquivos if nomes is None or a.name in nomes):
        enviar(arquivo, f"{prefixo_}/{arquivo.name}")
        chaves.append(f"{prefixo_}/{arquivo.name}")
    return chaves


def listar(prefixo_):
    """As chaves sob o prefixo, em ordem."""
    paginas = cliente().get_paginator("list_objects_v2").paginate(
        Bucket=config.S3_BUCKET, Prefix=prefixo_)
    return sorted(o["Key"] for pagina in paginas for o in pagina.get("Contents", []))


def subpastas(prefixo_):
    """Os nomes das pastas logo abaixo do prefixo, como os carimbos de uma area."""
    resto = (chave[len(prefixo_) + 1:] for chave in listar(prefixo_ + "/"))
    return sorted({nome.split("/")[0] for nome in resto if "/" in nome})


def baixar_pasta(prefixo_, pasta):
    """Copia para `pasta` os arquivos logo abaixo do prefixo e devolve a pasta."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    s3 = cliente()
    for chave in listar(prefixo_ + "/"):
        nome = chave[len(prefixo_) + 1:]
        if "/" not in nome:
            corpo = s3.get_object(Bucket=config.S3_BUCKET, Key=chave)["Body"].read()
            (pasta / nome).write_bytes(corpo)
    return pasta


def metadados(chave):
    """Os metadados gravados com o objeto."""
    return cliente().head_object(Bucket=config.S3_BUCKET, Key=chave)["Metadata"]

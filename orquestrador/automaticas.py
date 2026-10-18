"""Executa as etapas que o sistema faz sozinho, gravando os artefatos de cada uma no lago."""
import json
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

from orquestrador import (config, controle, decisoes, geracao, lago, relatorio_geracao,
                          relatorio_limpeza)
from orquestrador.controle import ERRO

ESPERA_NOME, ESPERA_PARAMETROS = "aguardando nome do esquema", "aguardando parametros"


def carimbo():
    """O carimbo das pastas do lago e das versoes; os testes o substituem."""
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def sujo_de(ctx):
    """A extracao ingerida no processo, lida como texto literal."""
    return pd.read_csv(Path(ctx["trabalho"]) / "original.csv", **config.LER_CSV)


def armazenar_original(con, processo):
    """Etapa 2: grava a extracao no lago, salvo se o mesmo hash ja foi ingerido no esquema."""
    ctx = controle.iniciar_etapa(con, processo, 2)
    repetido = controle.dado_existente(con, ctx["dominio"], ctx["esquema"], ctx["hash"])
    if repetido:
        controle.atualizar_contexto(con, processo, id_dado=repetido["ID_CONTROLE_DADO"],
                                    repetido=repetido["DATA_HORA_INGESTAO"])
        return
    prefixo = lago.prefixo(ctx["dominio"], ctx["esquema"], "Original", carimbo())
    lago.enviar(Path(ctx["trabalho"]) / "original.csv", f"{prefixo}/dados.csv",
                {"sha256": ctx["hash"]})
    id_dado = controle.registrar_dado(con, ctx["hash"], ctx["dominio"], ctx["esquema"], prefixo)
    controle.atualizar_contexto(con, processo, id_dado=id_dado)


def falhar(con, processo, detalhe):
    """Fecha a etapa aberta com erro e guarda o motivo no lago, ao lado da versao."""
    ctx = controle.contexto(con, processo)
    controle.concluir_etapa(con, processo, ERRO, detalhe)
    if ctx.get("versao_em"):
        arquivo = Path(ctx["pasta_versao"]) / "erro.log"
        arquivo.write_text(detalhe, encoding="utf-8")
        pasta = lago.prefixo(ctx["dominio"], ctx["esquema"], "Limpador", ctx["versao_em"])
        lago.enviar(arquivo, f"{pasta}/erro.log")
    return controle.etapa_atual(con, processo)["ID_ETAPA"]


def versionar(con, processo):
    """Etapa 7: monta o relatorio de geracao e grava a versao do limpador no lago."""
    ctx = controle.iniciar_etapa(con, processo, 7)
    destino, pasta = Path(ctx["destino"]), Path(ctx["pasta_versao"])
    anterior = ctx["geracao"]["reaproveitar"]
    sorteio = json.loads((pasta / "guia_lago" / "sorteio.json").read_text(encoding="utf-8"))
    limpador = (destino / f"limpador_{ctx['versao']}.py").read_text(encoding="utf-8")
    texto = relatorio_geracao.montar(
        relatorio_geracao.ler(destino / f"raciocinio_{ctx['versao']}.md"), ctx["parametros"],
        sorteio, geracao.chamadas(destino, anterior), "GERACAO_TRUNCADA = True" in limpador)
    (destino / "relatorio_geracao.md").write_text(texto, encoding="utf-8")
    (destino / "parametros.json").write_text(json.dumps(ctx["parametros"]), encoding="utf-8")
    decisoes.gravar(destino, ctx["geracao"]["decisoes"])
    prefixo = lago.prefixo(ctx["dominio"], ctx["esquema"], "Limpador", ctx["versao_em"])
    lago.enviar_pasta(destino, prefixo)
    id_limpador = controle.registrar_limpador(con, ctx["dominio"], ctx["esquema"], prefixo,
                                              ctx.get("id_limpador"))
    controle.atualizar_contexto(con, processo, id_limpador=id_limpador)


def aplicar(con, processo, aprovado=None):
    """Etapa 8: aplica a versao a tabela inteira e monta o relatorio de limpeza."""
    ctx = controle.iniciar_etapa(con, processo, 8)
    if aprovado is not None:
        destino = lago.baixar_pasta(aprovado["DIRETORIO_BUCKET"], Path(ctx["trabalho"]) / "aprovado")
        versao = next(destino.glob("limpador_*.py")).stem.removeprefix("limpador_")
        ctx = controle.atualizar_contexto(con, processo, destino=str(destino), versao=versao,
                                          id_limpador=aprovado["ID_LIMPADOR"], gerou=False)
    pasta = Path(ctx["trabalho"]) / "corrigido" / ctx["versao"]
    limpador = Path(ctx["destino"]) / f"limpador_{ctx['versao']}.py"
    try:
        aplicacao = relatorio_limpeza.aplicar(limpador, Path(ctx["trabalho"]) / "original.csv", pasta)
    except (RuntimeError, subprocess.TimeoutExpired) as erro:
        # Degradacao nomeada: a etapa 8 fica com erro e a saida e gerar nova versao.
        return falhar(con, processo, str(erro))
    resumo = relatorio_limpeza.resumir(aplicacao)
    (pasta / "relatorio_limpeza.md").write_text(relatorio_limpeza.montar(resumo, ctx["versao"]),
                                                encoding="utf-8")
    controle.atualizar_contexto(con, processo, corrigido=str(pasta), truncada=resumo["truncada"],
                                regras=aplicacao["regras"])
    controle.iniciar_etapa(con, processo, 9)
    return 9


def guia_do_esquema(con, processo):
    """Etapa 3 do esquema conhecido: a amostra-guia da primeira ingestao, sem novo sorteio."""
    ctx = controle.iniciar_etapa(con, processo, 3)
    area = f"{lago.nome_de_pasta(ctx['dominio'])}/{lago.nome_de_pasta(ctx['esquema'])}/Amostra_Guia"
    primeira = lago.subpastas(area)[0]
    controle.atualizar_contexto(con, processo, guia=f"{area}/{primeira}", guia_deste_processo=False)
    controle.marcar(con, processo, ESPERA_PARAMETROS)

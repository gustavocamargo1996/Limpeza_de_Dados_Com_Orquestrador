"""A ordem das etapas do processo e as transicoes entre elas, gravadas no SQLite."""
import hashlib
from datetime import datetime
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError

from orquestrador import amostra, automaticas, config, controle, decisoes, geracao, lago
from orquestrador.automaticas import ESPERA_NOME, ESPERA_PARAMETROS
from orquestrador.controle import ANDAMENTO, ERRO, SUCESSO


def iniciar(con, conteudo, nome_arquivo, dominio):
    """Etapa 1: le o dataset, abre o processo e identifica o esquema."""
    sujo = amostra.ler_dataset(conteudo)
    processo = controle.abrir_processo(con, {
        "inicio": controle.agora(), "dominio": dominio, "nome_arquivo": nome_arquivo,
        "hash": hashlib.sha256(conteudo).hexdigest(), "campos": sorted(sujo.columns),
        "n_linhas": len(sujo)})
    trabalho = config.TRABALHO / str(processo)
    trabalho.mkdir(parents=True, exist_ok=True)
    (trabalho / "original.csv").write_bytes(conteudo)
    controle.atualizar_contexto(con, processo, trabalho=str(trabalho))
    controle.iniciar_etapa(con, processo, 1)
    esquema = controle.buscar_esquema(con, dominio, sujo.columns)
    if esquema is None:
        controle.atualizar_contexto(con, processo, conhecido=False)
        controle.marcar(con, processo, ESPERA_NOME)
        return processo
    controle.atualizar_contexto(con, processo, conhecido=True, esquema=esquema["NOME_ESQUEMA"],
                                id_esquema=esquema["ID_ESQUEMA"])
    automaticas.armazenar_original(con, processo)
    aprovado = controle.limpador_aprovado(con, dominio, esquema["NOME_ESQUEMA"])
    if aprovado:
        automaticas.aplicar(con, processo, aprovado)
    else:
        automaticas.guia_do_esquema(con, processo)
    return processo


def nomear(con, processo, nome):
    """Etapa 1 do esquema novo: cria o esquema com o nome dado e sorteia o guia."""
    ctx = controle.contexto(con, processo)
    nome = nome.strip()
    diretorio = f"{lago.nome_de_pasta(ctx['dominio'])}/{lago.nome_de_pasta(nome)}"
    if not lago.nome_de_pasta(nome).strip("_"):
        raise ValueError("o nome precisa ter ao menos uma letra ou digito")
    if controle.esquema_por_diretorio(con, diretorio):
        raise ValueError(f"ja existe um esquema chamado {nome!r} em {ctx['dominio']}")
    id_esquema = controle.criar_esquema(con, ctx["dominio"], nome, ctx["campos"], diretorio)
    controle.atualizar_contexto(con, processo, esquema=nome, id_esquema=id_esquema)
    automaticas.armazenar_original(con, processo)
    ressortear(con, processo, min(config.LINHAS_GUIA_PADRAO, ctx["n_linhas"]))
    controle.iniciar_etapa(con, processo, 3)


def ressortear(con, processo, n):
    """Sorteia de novo com `n` linhas; as trocas anteriores se perdem."""
    ctx = controle.contexto(con, processo)
    sorteio = amostra.sortear(ctx["n_linhas"], n, config.SEMENTE)
    controle.atualizar_contexto(con, processo, sorteio=sorteio)


def trocar_linha(con, processo, posicao):
    """Troca a linha da `posicao` do sorteio pela proxima livre."""
    ctx = controle.contexto(con, processo)
    controle.atualizar_contexto(con, processo, sorteio=amostra.trocar(ctx["sorteio"], posicao))


def confirmar_guia(con, processo, guia, pares):
    """Etapa 3: valida o guia corrigido, grava a Amostra_Guia no lago e espera os parametros."""
    ctx = controle.contexto(con, processo)
    sujo = automaticas.sujo_de(ctx)
    pares, problemas = amostra.completar_pares(pares, sujo)
    problemas = amostra.divergencias(guia, sujo, ctx["sorteio"]) + problemas
    if problemas:
        raise ValueError("; ".join(problemas))
    pasta = Path(ctx["trabalho"]) / "guia"
    amostra.gravar_guia(pasta, guia, pares, sujo, ctx["sorteio"])
    prefixo = lago.prefixo(ctx["dominio"], ctx["esquema"], "Amostra_Guia", automaticas.carimbo())
    lago.enviar_pasta(pasta, prefixo)
    controle.atualizar_contexto(con, processo, guia=prefixo, guia_deste_processo=True)
    controle.marcar(con, processo, ESPERA_PARAMETROS)


def gerar(con, processo, base, tamanho, decisoes_=None, reaproveitar=None):
    """Etapas 4 a 6: monta a entrada, grava as decisoes e sobe o filho do gerador."""
    ctx = controle.contexto(con, processo)
    versao_em = automaticas.carimbo()
    versao = f"{lago.nome_de_pasta(ctx['esquema'])}_{versao_em}"
    pasta = Path(ctx["trabalho"]) / versao
    guia = lago.baixar_pasta(ctx["guia"], pasta / "guia_lago")
    if decisoes_:
        decisoes.gravar(guia, decisoes_)
    antigas = None if ctx["guia_deste_processo"] else amostra.linhas_sujas(guia)
    parametros = amostra.montar_entrada(automaticas.sujo_de(ctx), guia, pasta / "entrada", base,
                                        tamanho, config.SEMENTE, antigas)
    destino = pasta / "gerador" / versao
    filho = geracao.disparar(pasta / "entrada" / "sujo.csv", pasta / "entrada" / "guia", destino,
                             reaproveitar)
    controle.atualizar_contexto(
        con, processo, versao=versao, versao_em=versao_em, pasta_versao=str(pasta),
        destino=str(destino), pid=filho.pid, parametros=parametros, gerou=True,
        corrigido=None, truncada=False,
        geracao={"base": base, "tamanho": tamanho, "decisoes": decisoes_ or [],
                 "reaproveitar": str(reaproveitar) if reaproveitar else None,
                 "inicio": datetime.now().timestamp()})
    controle.iniciar_etapa(con, processo, 4, pid=filho.pid)


def acompanhar(con, processo):
    """Avanca as etapas 4 a 6 pelo filho do gerador e, ao fim dele, a 7 e a 8."""
    atual = controle.etapa_atual(con, processo)
    if atual["ID_ETAPA"] not in (4, 5, 6) or atual["STATUS"] != ANDAMENTO:
        return atual["ID_ETAPA"]
    ctx = controle.contexto(con, processo)
    destino, pid = Path(ctx["destino"]), ctx["pid"]
    situacao = geracao.situacao(destino, pid, ctx["geracao"]["inicio"])
    if situacao == "rodando":
        if datetime.now().timestamp() - ctx["geracao"]["inicio"] > config.TIMEOUT_GERACAO:
            geracao.encerrar(pid)
            return automaticas.falhar(con, processo, "timeout: a geracao passou do limite")
        # O residual roda depois do codificador: o painel so anda para a frente, e a
        # etapa que passou entre duas consultas e registrada mesmo assim.
        for etapa in range(atual["ID_ETAPA"] + 1, geracao.etapa_corrente(destino) + 1):
            controle.iniciar_etapa(con, processo, etapa, pid=pid)
        return controle.etapa_atual(con, processo)["ID_ETAPA"]
    if situacao == "erro":
        motivo = geracao.erro(destino) or "interrompido: o gerador parou sem deixar log"
        return automaticas.falhar(con, processo, motivo)
    try:
        automaticas.versionar(con, processo)
    except (BotoCoreError, ClientError, OSError, ValueError) as erro:
        # Degradacao nomeada: o lago ou um arquivo falhou; a etapa 7 fica com erro.
        return automaticas.falhar(con, processo, f"{type(erro).__name__}: {erro}")
    return automaticas.aplicar(con, processo)


def aprovar(con, processo):
    """Etapas 9 e 10: aprova a versao, grava o corrigido no lago e encerra o processo."""
    ctx = controle.contexto(con, processo)
    if ctx.get("truncada"):
        raise ValueError("geracao truncada pelo teto de chamadas nao pode ser aprovada")
    atual = controle.etapa_atual(con, processo)
    if (atual["ID_ETAPA"], atual["STATUS"]) != (9, ANDAMENTO):
        raise ValueError("so a versao aplicada ao dataset, na etapa 9, pode ser aprovada")
    controle.iniciar_etapa(con, processo, 10)
    prefixo = lago.prefixo(ctx["dominio"], ctx["esquema"], "Corrigido", automaticas.carimbo())
    lago.enviar_pasta(ctx["corrigido"], prefixo, ["dados.csv", "flags.csv", "relatorio_limpeza.md"])
    controle.mudar_status(con, ctx["id_limpador"], "aprovado")
    controle.concluir_dado(con, ctx["id_dado"], prefixo, ctx["versao"])
    controle.concluir_etapa(con, processo, SUCESSO)
    controle.encerrar_processo(con, processo)


def aperfeicoar(con, processo, novas):
    """Etapa 9 para a 4: reprova a versao e gera outra com as decisoes, reaproveitando respostas."""
    ctx = controle.contexto(con, processo)
    g = ctx["geracao"]
    gerar(con, processo, g["base"], g["tamanho"], decisoes.acumular(g["decisoes"], novas),
          Path(ctx["destino"]) / "respostas.jsonl")
    # So depois de a nova geracao subir: se ela falha antes, a versao continua decidivel.
    controle.mudar_status(con, ctx["id_limpador"], "reprovado")


def nova_versao(con, processo, base, tamanho):
    """Etapa 9 para a 4 no esquema conhecido, com as regras aprovadas e o guia da 1a ingestao."""
    ctx = controle.contexto(con, processo)
    # REGRAS lidas do arquivo, e nao da aplicacao: a aplicacao pode ter falhado.
    regras = decisoes.regras_do_limpador(Path(ctx["destino"]) / f"limpador_{ctx['versao']}.py")
    herdadas = decisoes.acumular(decisoes.ler(ctx["destino"]), [], regras=regras,
                                 versao=ctx["versao"])
    if not ctx.get("guia"):
        automaticas.guia_do_esquema(con, processo)
    gerar(con, processo, base, tamanho, herdadas)


def tentar_de_novo(con, processo):
    """Refaz a geracao que falhou, com os mesmos parametros e decisoes."""
    g = controle.contexto(con, processo)["geracao"]
    gerar(con, processo, g["base"], g["tamanho"], g["decisoes"],
          Path(g["reaproveitar"]) if g["reaproveitar"] else None)


def cancelar(con, processo):
    """Encerra o processo; o filho do gerador, se roda, e encerrado junto."""
    ctx, atual = controle.contexto(con, processo), controle.etapa_atual(con, processo)
    gerando = atual and atual["ID_ETAPA"] in (4, 5, 6) and atual["STATUS"] == ANDAMENTO
    if gerando and geracao.vivo(ctx["pid"], ctx["geracao"]["inicio"]):
        geracao.encerrar(ctx["pid"])
    if atual and atual["STATUS"] == ANDAMENTO:
        controle.concluir_etapa(con, processo, ERRO, "cancelado pelo usuario")
    controle.encerrar_processo(con, processo)

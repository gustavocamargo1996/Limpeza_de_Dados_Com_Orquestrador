"""Le e grava os metadados de controle no SQLite."""
import json
import sqlite3
from datetime import datetime

from orquestrador import config

ANDAMENTO, SUCESSO, ERRO = "em andamento", "concluido com sucesso", "concluido com erro"
ETAPAS = (
    (1, "Identificação do esquema", "verifica se o esquema é conhecido e se há limpador"),
    (2, "Armazenamento do original", "grava a extração no data lake, com data e hash"),
    (3, "Amostra-guia", "o usuário corrige as linhas sorteadas do dataset"),
    (4, "Detecção", "o gerador decide onde estão os erros"),
    (5, "Geração de regras", "o gerador especifica a correção de cada regra"),
    (6, "Geração de código", "o gerador escreve o limpador"),
    (7, "Versionamento do limpador", "grava a versão do limpador no data lake"),
    (8, "Aplicação e relatórios", "aplica o limpador à tabela inteira e monta os relatórios"),
    (9, "Decisão do usuário", "aprovar ou aperfeiçoar o limpador"),
    (10, "Armazenamento do corrigido", "grava o dataset corrigido no data lake"),
)
# As cinco tabelas da especificacao (secao 3), mais CONTEXTOS: o estado de cada processo.
TABELAS = """
CREATE TABLE IF NOT EXISTS ESQUEMAS (ID_ESQUEMA INTEGER PRIMARY KEY, DOMINIO TEXT,
  NOME_ESQUEMA TEXT, CAMPOS_ESQUEMA TEXT, DIRETORIO_BUCKET TEXT, DATA_CRIACAO TEXT);
CREATE TABLE IF NOT EXISTS LIMPADORES (ID_LIMPADOR INTEGER PRIMARY KEY, DOMINIO TEXT,
  NOME_ESQUEMA TEXT, DATA_CRIACAO TEXT, STATUS_APROVACAO TEXT, DIRETORIO_BUCKET TEXT,
  ID_LIMPADOR_ORIGEM INTEGER);
CREATE TABLE IF NOT EXISTS ETAPAS (ID_ETAPA INTEGER PRIMARY KEY, NOME_ETAPA TEXT,
  DESCRICAO_ETAPA TEXT);
CREATE TABLE IF NOT EXISTS PROCESSOS (ID INTEGER PRIMARY KEY, ID_PROCESSO INTEGER,
  ID_ESQUEMA INTEGER, NOME_ESQUEMA TEXT, HASH_DADO TEXT, ID_ETAPA INTEGER,
  DATA_INICIO_ETAPA TEXT, STATUS TEXT, DATA_HORA_INICIO_PROCESSO TEXT,
  DATA_HORA_CONCLUSAO TEXT, TEMPO_PROCESSAMENTO REAL, PID INTEGER, DETALHE TEXT);
CREATE TABLE IF NOT EXISTS DADOS (ID_CONTROLE_DADO INTEGER PRIMARY KEY, HASH TEXT,
  DOMINIO TEXT, NOME_ESQUEMA TEXT, DIRETORIO_ORIGINAL TEXT, DIRETORIO_CORRIGIDO TEXT,
  LIMPADOR_UTILIZADO TEXT, DATA_HORA_INGESTAO TEXT);
CREATE TABLE IF NOT EXISTS CONTEXTOS (ID_PROCESSO INTEGER PRIMARY KEY, CONTEXTO TEXT,
  ENCERRADO INTEGER DEFAULT 0);
"""


def agora():
    """O instante corrente em ISO 8601, ate o segundo."""
    return datetime.now().isoformat(timespec="seconds")


def conectar(caminho=None):
    """Abre o banco em autocommit, cria as tabelas e povoa as etapas."""
    caminho = caminho or config.SQLITE
    caminho.parent.mkdir(parents=True, exist_ok=True)
    # O fragmento do painel roda em outra thread do Streamlit, com a mesma conexao.
    con = sqlite3.connect(caminho, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(TABELAS)
    con.executemany("INSERT OR IGNORE INTO ETAPAS VALUES (?, ?, ?)", ETAPAS)
    return con


def _um(con, sql, *args):
    """A primeira linha da consulta como dict, ou None."""
    linha = con.execute(sql, args).fetchone()
    return dict(linha) if linha else None


def abrir_processo(con, contexto):
    """Registra um processo novo com seu contexto e devolve o ID_PROCESSO."""
    texto = json.dumps(contexto, ensure_ascii=False)
    return con.execute("INSERT INTO CONTEXTOS (CONTEXTO) VALUES (?)", (texto,)).lastrowid


def contexto(con, processo):
    """O contexto do processo: o que as etapas seguintes precisam saber dele."""
    return json.loads(_um(con, "SELECT CONTEXTO FROM CONTEXTOS WHERE ID_PROCESSO = ?",
                          processo)["CONTEXTO"])


def atualizar_contexto(con, processo, **campos):
    """Junta `campos` ao contexto do processo e devolve o contexto novo."""
    novo = {**contexto(con, processo), **campos}
    con.execute("UPDATE CONTEXTOS SET CONTEXTO = ? WHERE ID_PROCESSO = ?",
                (json.dumps(novo, ensure_ascii=False), processo))
    return novo


def processo_aberto(con):
    """O processo mais recente ainda nao encerrado, ou None."""
    linha = _um(con, "SELECT ID_PROCESSO FROM CONTEXTOS WHERE ENCERRADO = 0 "
                     "ORDER BY ID_PROCESSO DESC LIMIT 1")
    return linha["ID_PROCESSO"] if linha else None


def encerrar_processo(con, processo):
    """Marca o processo como encerrado; a interface volta a ingestao."""
    con.execute("UPDATE CONTEXTOS SET ENCERRADO = 1 WHERE ID_PROCESSO = ?", (processo,))


def etapa_atual(con, processo):
    """A ultima linha de PROCESSOS do processo, ou None."""
    return _um(con, "SELECT * FROM PROCESSOS WHERE ID_PROCESSO = ? ORDER BY ID DESC LIMIT 1",
               processo)


def etapas(con, processo):
    """Todas as linhas de PROCESSOS do processo, na ordem em que aconteceram."""
    return [dict(linha) for linha in con.execute(
        "SELECT * FROM PROCESSOS WHERE ID_PROCESSO = ? ORDER BY ID", (processo,))]


def iniciar_etapa(con, processo, etapa, pid=None, detalhe=""):
    """Fecha com sucesso a etapa aberta, abre `etapa` em andamento e devolve o contexto."""
    atual = etapa_atual(con, processo)
    if atual and atual["STATUS"] == ANDAMENTO:
        concluir_etapa(con, processo, SUCESSO)
    ctx = contexto(con, processo)
    con.execute(
        "INSERT INTO PROCESSOS (ID_PROCESSO, ID_ESQUEMA, NOME_ESQUEMA, HASH_DADO, ID_ETAPA, "
        "DATA_INICIO_ETAPA, STATUS, DATA_HORA_INICIO_PROCESSO, PID, DETALHE) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (processo, ctx.get("id_esquema"), ctx.get("esquema"), ctx.get("hash"), etapa, agora(),
         ANDAMENTO, ctx.get("inicio"), pid, detalhe))
    return ctx


def concluir_etapa(con, processo, status, detalhe=None):
    """Fecha a etapa aberta com `status`, gravando conclusao e tempo em segundos."""
    atual = etapa_atual(con, processo)
    fim = datetime.now().replace(microsecond=0)
    tempo = (fim - datetime.fromisoformat(atual["DATA_INICIO_ETAPA"])).total_seconds()
    con.execute("UPDATE PROCESSOS SET STATUS = ?, DATA_HORA_CONCLUSAO = ?, "
                "TEMPO_PROCESSAMENTO = ?, DETALHE = COALESCE(?, DETALHE) WHERE ID = ?",
                (status, fim.isoformat(), tempo, detalhe, atual["ID"]))


def marcar(con, processo, detalhe):
    """Anota na etapa aberta o que ela espera do usuario."""
    con.execute("UPDATE PROCESSOS SET DETALHE = ? WHERE ID = ?",
                (detalhe, etapa_atual(con, processo)["ID"]))


def buscar_esquema(con, dominio, campos):
    """O esquema do dominio com exatamente este conjunto de colunas, ou None."""
    return _um(con, "SELECT * FROM ESQUEMAS WHERE DOMINIO = ? AND CAMPOS_ESQUEMA = ?",
               dominio, json.dumps(sorted(campos), ensure_ascii=False))


def esquema_por_diretorio(con, diretorio):
    """O esquema gravado neste diretorio do bucket, ou None."""
    return _um(con, "SELECT * FROM ESQUEMAS WHERE DIRETORIO_BUCKET = ?", diretorio)


def criar_esquema(con, dominio, nome, campos, diretorio):
    """Registra um esquema novo e devolve o ID_ESQUEMA."""
    return con.execute(
        "INSERT INTO ESQUEMAS (DOMINIO, NOME_ESQUEMA, CAMPOS_ESQUEMA, DIRETORIO_BUCKET, "
        "DATA_CRIACAO) VALUES (?, ?, ?, ?, ?)",
        (dominio, nome, json.dumps(sorted(campos), ensure_ascii=False), diretorio, agora()),
    ).lastrowid


def registrar_limpador(con, dominio, nome, diretorio, origem):
    """Registra uma versao do limpador como pendente e devolve o ID_LIMPADOR."""
    return con.execute(
        "INSERT INTO LIMPADORES (DOMINIO, NOME_ESQUEMA, DATA_CRIACAO, STATUS_APROVACAO, "
        "DIRETORIO_BUCKET, ID_LIMPADOR_ORIGEM) VALUES (?, ?, ?, 'pendente', ?, ?)",
        (dominio, nome, agora(), diretorio, origem),
    ).lastrowid


def mudar_status(con, id_limpador, status):
    """Grava `aprovado` ou `reprovado` na versao do limpador."""
    con.execute("UPDATE LIMPADORES SET STATUS_APROVACAO = ? WHERE ID_LIMPADOR = ?",
                (status, id_limpador))


def obter_limpador(con, id_limpador):
    """A linha da versao do limpador."""
    return _um(con, "SELECT * FROM LIMPADORES WHERE ID_LIMPADOR = ?", id_limpador)


def limpador_aprovado(con, dominio, nome):
    """A versao aprovada mais recente do esquema, ou None."""
    return _um(con, "SELECT * FROM LIMPADORES WHERE DOMINIO = ? AND NOME_ESQUEMA = ? AND "
                    "STATUS_APROVACAO = 'aprovado' ORDER BY ID_LIMPADOR DESC LIMIT 1",
               dominio, nome)


def dado_existente(con, dominio, nome, hash_):
    """A extracao com este hash ja ingerida no esquema, ou None."""
    return _um(con, "SELECT * FROM DADOS WHERE DOMINIO = ? AND NOME_ESQUEMA = ? AND HASH = ?",
               dominio, nome, hash_)


def registrar_dado(con, hash_, dominio, nome, diretorio):
    """Registra a extracao gravada em `diretorio` e devolve o ID_CONTROLE_DADO."""
    return con.execute(
        "INSERT INTO DADOS (HASH, DOMINIO, NOME_ESQUEMA, DIRETORIO_ORIGINAL, "
        "DATA_HORA_INGESTAO) VALUES (?, ?, ?, ?, ?)",
        (hash_, dominio, nome, diretorio, agora()),
    ).lastrowid


def concluir_dado(con, id_dado, diretorio_corrigido, limpador):
    """Grava onde ficou o corrigido e qual versao do limpador o produziu."""
    con.execute("UPDATE DADOS SET DIRETORIO_CORRIGIDO = ?, LIMPADOR_UTILIZADO = ? "
                "WHERE ID_CONTROLE_DADO = ?", (diretorio_corrigido, limpador, id_dado))

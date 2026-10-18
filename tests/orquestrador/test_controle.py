"""O banco de controle: as tabelas da especificacao, as etapas e o estado que sobrevive ao F5."""
from orquestrador import config, controle

CAMPOS_DA_ESPECIFICACAO = {
    "ESQUEMAS": {"ID_ESQUEMA", "DOMINIO", "NOME_ESQUEMA", "CAMPOS_ESQUEMA", "DIRETORIO_BUCKET",
                 "DATA_CRIACAO"},
    "LIMPADORES": {"ID_LIMPADOR", "DOMINIO", "NOME_ESQUEMA", "DATA_CRIACAO", "STATUS_APROVACAO"},
    "ETAPAS": {"ID_ETAPA", "NOME_ETAPA", "DESCRICAO_ETAPA"},
    "PROCESSOS": {"ID_PROCESSO", "ID_ESQUEMA", "NOME_ESQUEMA", "HASH_DADO", "ID_ETAPA",
                  "DATA_INICIO_ETAPA", "STATUS", "DATA_HORA_INICIO_PROCESSO",
                  "DATA_HORA_CONCLUSAO", "TEMPO_PROCESSAMENTO"},
    "DADOS": {"ID_CONTROLE_DADO", "HASH", "DOMINIO", "NOME_ESQUEMA", "DIRETORIO_ORIGINAL",
              "DIRETORIO_CORRIGIDO", "LIMPADOR_UTILIZADO", "DATA_HORA_INGESTAO"},
}


def test_as_cinco_tabelas_tem_os_campos_da_especificacao(con):
    for tabela, campos in CAMPOS_DA_ESPECIFICACAO.items():
        existentes = {linha[1] for linha in con.execute(f"PRAGMA table_info({tabela})")}
        assert campos <= existentes, (tabela, campos - existentes)


def test_as_dez_etapas_estao_povoadas_uma_vez(con):
    controle.conectar()
    nomes = [r["NOME_ETAPA"] for r in con.execute("SELECT * FROM ETAPAS ORDER BY ID_ETAPA")]
    assert len(nomes) == 10 and nomes[3:6] == ["Detecção", "Geração de regras", "Geração de código"]


def test_iniciar_etapa_fecha_a_anterior_com_sucesso(con):
    p = controle.abrir_processo(con, {"inicio": controle.agora(), "esquema": "beers", "hash": "h"})
    controle.iniciar_etapa(con, p, 1)
    controle.iniciar_etapa(con, p, 2, pid=42)
    primeira, segunda = controle.etapas(con, p)
    assert (primeira["ID_ETAPA"], primeira["STATUS"]) == (1, controle.SUCESSO)
    assert primeira["TEMPO_PROCESSAMENTO"] >= 0 and primeira["DATA_HORA_CONCLUSAO"]
    assert (segunda["ID_ETAPA"], segunda["STATUS"], segunda["PID"]) == (2, controle.ANDAMENTO, 42)
    assert (segunda["NOME_ESQUEMA"], segunda["HASH_DADO"]) == ("beers", "h")


def test_concluir_com_erro_guarda_o_detalhe(con):
    p = controle.abrir_processo(con, {"inicio": controle.agora()})
    controle.iniciar_etapa(con, p, 4)
    controle.concluir_etapa(con, p, controle.ERRO, "timeout")
    atual = controle.etapa_atual(con, p)
    assert (atual["STATUS"], atual["DETALHE"]) == (controle.ERRO, "timeout")


def test_o_estado_sobrevive_a_uma_conexao_nova(con):
    p = controle.abrir_processo(con, {"inicio": controle.agora(), "dominio": "Outros"})
    controle.atualizar_contexto(con, p, esquema="beers")
    controle.iniciar_etapa(con, p, 3)
    outra = controle.conectar(config.SQLITE)
    assert controle.processo_aberto(outra) == p
    assert controle.contexto(outra, p) == {"inicio": controle.contexto(con, p)["inicio"],
                                           "dominio": "Outros", "esquema": "beers"}
    assert controle.etapa_atual(outra, p)["ID_ETAPA"] == 3
    controle.encerrar_processo(outra, p)
    assert controle.processo_aberto(con) is None


def test_esquema_achado_pelo_conjunto_de_colunas_no_mesmo_dominio(con):
    controle.criar_esquema(con, "Outros", "beers", ["b", "a", "c"], "Outros/beers")
    assert controle.buscar_esquema(con, "Outros", ["c", "a", "b"])["NOME_ESQUEMA"] == "beers"
    assert controle.buscar_esquema(con, "Saúde", ["a", "b", "c"]) is None
    assert controle.buscar_esquema(con, "Outros", ["a", "b"]) is None
    assert controle.esquema_por_diretorio(con, "Outros/beers")["NOME_ESQUEMA"] == "beers"


def test_limpador_aprovado_e_o_mais_recente_aprovado(con):
    a = controle.registrar_limpador(con, "Outros", "beers", "x/1", None)
    b = controle.registrar_limpador(con, "Outros", "beers", "x/2", a)
    controle.registrar_limpador(con, "Outros", "beers", "x/3", b)
    assert controle.limpador_aprovado(con, "Outros", "beers") is None
    controle.mudar_status(con, a, "aprovado")
    controle.mudar_status(con, b, "aprovado")
    aprovado = controle.limpador_aprovado(con, "Outros", "beers")
    assert (aprovado["ID_LIMPADOR"], aprovado["ID_LIMPADOR_ORIGEM"]) == (b, a)
    assert controle.obter_limpador(con, b)["STATUS_APROVACAO"] == "aprovado"


def test_dado_registrado_e_concluido(con):
    d = controle.registrar_dado(con, "h1", "Outros", "beers", "Outros/beers/Original/t")
    assert controle.dado_existente(con, "Outros", "beers", "h1")["ID_CONTROLE_DADO"] == d
    assert controle.dado_existente(con, "Outros", "beers", "h2") is None
    controle.concluir_dado(con, d, "Outros/beers/Corrigido/t", "beers_t")
    linha = controle.dado_existente(con, "Outros", "beers", "h1")
    assert (linha["DIRETORIO_CORRIGIDO"], linha["LIMPADOR_UTILIZADO"]) == ("Outros/beers/Corrigido/t", "beers_t")

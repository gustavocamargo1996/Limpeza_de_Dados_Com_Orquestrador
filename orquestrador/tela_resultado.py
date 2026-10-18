"""Mostra os relatorios da versao e recolhe a aprovacao ou o aperfeicoamento do limpador."""
from pathlib import Path

import streamlit as st

from orquestrador import controle, decisoes, fluxo, relatorio_geracao, tela_guia
from orquestrador.controle import ERRO


def _texto(caminho, falta):
    """O Markdown do arquivo, ou o aviso de que ele nao existe."""
    return caminho.read_text(encoding="utf-8") if caminho.exists() else falta


def mostrar(con, processo):
    """Os dois relatorios e a decisao do usuario sobre a versao."""
    ctx = controle.contexto(con, processo)
    atual = controle.etapa_atual(con, processo)
    st.header(f"Versão {ctx['versao']}")
    if atual["STATUS"] == ERRO:
        st.error("O limpador falhou ao ser aplicado ao dataset; gere uma nova versão.")
        st.code(atual["DETALHE"] or "sem detalhe", language=None)
    geracao_aba, limpeza_aba, decisao_aba = st.tabs(
        ["Relatório de geração", "Relatório de limpeza", "Decisão"])
    with geracao_aba:
        st.markdown(_texto(Path(ctx["destino"]) / "relatorio_geracao.md", "Sem relatório de geração."))
    with limpeza_aba:
        st.markdown(_texto(Path(ctx.get("corrigido", ".")) / "relatorio_limpeza.md",
                           "Sem relatório de limpeza."))
    with decisao_aba:
        _decidir(con, processo, ctx, aplicada=atual["STATUS"] != ERRO)


def _decidir(con, processo, ctx, aplicada):
    """Aprovar, ou aperfeicoar a versao gerada, ou gerar uma nova para o esquema conhecido."""
    if ctx.get("truncada"):
        st.warning("Geração truncada pelo teto de chamadas: esta versão não pode ser aprovada.")
    if st.button("Aprovar e gravar o dataset corrigido", type="primary", icon=":material/done_all:",
                 disabled=bool(ctx.get("truncada")) or not aplicada):
        fluxo.aprovar(con, processo)
        st.rerun()
    if ctx.get("gerou"):
        _aperfeicoar(con, processo, ctx)
        return
    st.subheader("Gerar nova versão")
    st.write("A nova versão herda as regras aprovadas e usa a amostra-guia da primeira ingestão.")
    escolha = tela_guia.parametros(ctx["n_linhas"], "nova")
    if escolha:
        fluxo.nova_versao(con, processo, *escolha)
        st.rerun()


def _aperfeicoar(con, processo, ctx):
    """As opcoes de cada regra, a instrucao ao especificador e o pedido de nova versao."""
    st.subheader("Aperfeiçoar")
    st.caption("Regras que contradizem o guia não podem ser aprovadas. As escolhas valem para a "
               "próxima versão, que reaproveita as respostas já gravadas.")
    raciocinio = relatorio_geracao.ler(Path(ctx["destino"]) / f"raciocinio_{ctx['versao']}.md")
    escolhas = []
    with st.form("aperfeicoar"):
        for coluna, dados in raciocinio["colunas"].items():
            itens = [c for c in dados["candidatas"] if decisoes.opcoes(c)]
            if not itens and not dados["residual"]["mapa"]:
                continue
            with st.expander(coluna):
                for i, c in enumerate(itens):
                    st.markdown(f"**{c['tipo']}**: {relatorio_geracao.descrever(c)}  \n"
                                f"{relatorio_geracao.justificar(c)}")
                    escolha = st.selectbox("Decisão", ["manter", *decisoes.opcoes(c)],
                                           key=f"d_{coluna}_{i}")
                    instrucao = st.text_input("Instrução ao especificador (opcional)",
                                              key=f"i_{coluna}_{i}")
                    if escolha != "manter":
                        escolhas.append(("regra", c, coluna, escolha, instrucao))
                for sujo, limpo, _ in dados["residual"]["mapa"]:
                    if st.checkbox(f"Rejeitar o residual `{sujo}` → `{limpo}`", key=f"r_{coluna}_{sujo}"):
                        escolhas.append(("residual", None, coluna, sujo, None))
        tela_guia.aviso_do_provedor()
        enviar = st.form_submit_button("Gerar versão aperfeiçoada")
    if not enviar:
        return
    try:
        novas = [decisoes.decidir(c, coluna, escolha, instrucao, ctx["versao"]) if tipo == "regra"
                 else decisoes.decidir_residual(coluna, escolha, ctx["versao"])
                 for tipo, c, coluna, escolha, instrucao in escolhas]
    except ValueError as erro:
        st.error(str(erro))
        return
    fluxo.aperfeicoar(con, processo, novas)
    st.rerun()

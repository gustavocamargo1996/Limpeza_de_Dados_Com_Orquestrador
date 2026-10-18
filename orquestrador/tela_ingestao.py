"""Mostra a ingestao do dataset, com o dominio, e pede o nome quando o esquema e novo."""
import streamlit as st

from orquestrador import config, controle, fluxo


def mostrar(con):
    """O upload do dataset e a escolha do dominio."""
    st.header("Ingestão do dataset")
    with st.form("ingestao"):
        arquivo = st.file_uploader("Dataset em CSV (UTF-8)", type="csv")
        dominio = st.selectbox("Domínio do dataset", config.DOMINIOS)
        enviar = st.form_submit_button("Ingerir", type="primary")
    if not enviar:
        return
    if arquivo is None:
        st.warning("Escolha um arquivo CSV.")
        return
    try:
        with st.spinner("Identificando o esquema e gravando o original no data lake…"):
            fluxo.iniciar(con, arquivo.getvalue(), arquivo.name, dominio)
    except ValueError as erro:
        st.error(f"Dataset recusado: {erro}")
        return
    st.rerun()


def pedir_nome(con, processo):
    """O nome do novo conjunto de dados, quando as colunas ainda nao existem no dominio."""
    ctx = controle.contexto(con, processo)
    st.header("Esquema novo")
    st.write(f"O arquivo **{ctx['nome_arquivo']}** ({ctx['n_linhas']} linhas) tem um conjunto "
             f"de colunas que ainda não existe no domínio **{ctx['dominio']}**:")
    st.markdown(" ".join(f"`{c}`" for c in ctx["campos"]))
    with st.form("nome"):
        nome = st.text_input("Nome do novo conjunto de dados")
        criar = st.form_submit_button("Criar esquema", type="primary")
    if not criar:
        return
    try:
        fluxo.nomear(con, processo, nome)
    except ValueError as erro:
        st.error(str(erro))
        return
    st.rerun()

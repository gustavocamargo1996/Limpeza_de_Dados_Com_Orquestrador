"""Mostra a amostra-guia, em formulario e em template, e o quadro de parametros da geracao."""
import pandas as pd
import streamlit as st

from orquestrador import amostra, automaticas, config, controle, fluxo


def mostrar(con, processo):
    """A etapa 3: o guia a corrigir ou, ja confirmado, os parametros da geracao."""
    ctx = controle.contexto(con, processo)
    if ctx.get("repetido"):
        st.info(f"Esta extração já foi ingerida em {ctx['repetido']}; o original não foi "
                "gravado de novo.", icon=":material/content_copy:")
    if ctx.get("guia"):
        st.header("Parâmetros da geração")
        if not ctx["guia_deste_processo"]:
            st.info("Esquema conhecido sem limpador aprovado: a geração usa a amostra-guia da "
                    "primeira ingestão.")
        escolha = parametros(ctx["n_linhas"], "gerar")
        if escolha:
            fluxo.gerar(con, processo, *escolha)
            st.rerun()
        return
    _guia(con, processo, ctx)


def _guia(con, processo, ctx):
    """O sorteio a corrigir, pelo formulario ou pelo template, e os pares avulsos."""
    sujo, sorteio = automaticas.sujo_de(ctx), ctx["sorteio"]
    st.header("Amostra-guia")
    st.write("Corrija as linhas sorteadas do seu dataset para que fiquem **inteiramente "
             "corretas**. Elas mostram ao gerador o formato de cada campo e são a verdade que "
             "nenhuma regra pode contradizer.")
    n = st.number_input("Linhas no guia", min_value=min(config.LINHAS_GUIA_MINIMO, len(sujo)),
                        max_value=len(sujo), value=len(sorteio["linhas"]))
    if n != len(sorteio["linhas"]):
        fluxo.ressortear(con, processo, int(n))
        st.rerun()
    tabela = amostra.template(sujo, sorteio)
    formulario, template = st.tabs(["Formulário", "Template"])
    with formulario:
        editado = st.data_editor(tabela, disabled=["_linha"], hide_index=True,
                                 key=f"guia_{n}_{len(sorteio['trocas'])}")
        esquerda, direita = st.columns([3, 1], vertical_alignment="bottom")
        posicao = esquerda.selectbox(
            "Não sabe corrigir uma linha? Sorteie outra no lugar dela",
            range(len(sorteio["linhas"])), format_func=lambda i: f"_linha {sorteio['linhas'][i]}")
        if direita.button("Sortear de novo", icon=":material/casino:"):
            fluxo.trocar_linha(con, processo, posicao)
            st.rerun()
        if sorteio["trocas"]:
            st.caption(f"{len(sorteio['trocas'])} troca(s) registrada(s); o relatório de geração "
                       "as declara.")
    with template:
        st.download_button("Baixar template", tabela.to_csv(index=False).encode("utf-8"),
                           "guia_template.csv", "text/csv", icon=":material/download:")
        enviado = st.file_uploader("Enviar o template corrigido", type="csv")
    st.subheader("Erros fora destas linhas (opcional)")
    st.caption("Indique a linha, a coluna e o valor certo. Deixar o valor certo em branco "
               "diz que o certo é vazio, como num N/A que deve sumir.")
    pares = st.data_editor(
        pd.DataFrame({"linha": pd.Series(dtype="Int64"), "coluna": pd.Series(dtype="object"),
                      "limpo": pd.Series(dtype="object")}),
        num_rows="dynamic", hide_index=True, key="pares", column_config={
            "linha": st.column_config.NumberColumn(min_value=0, max_value=len(sujo) - 1, step=1),
            "coluna": st.column_config.SelectboxColumn(options=list(sujo.columns))})
    if st.button("Confirmar guia", type="primary"):
        guia = pd.read_csv(enviado, **config.LER_CSV) if enviado else editado
        try:
            fluxo.confirmar_guia(con, processo, guia, pares.dropna(how="all"))
        except ValueError as erro:
            st.error(f"Guia recusado: {erro}")
            return
        st.rerun()
    st.caption("Com um template enviado, ele vale no lugar do formulário.")


def parametros(n_total, chave):
    """O quadro Parametros da geracao: (base, tamanho) depois do clique, senao None."""
    base = st.segmented_control("Base da geração", ["Amostra", "Tabela inteira"],
                                default="Amostra", key=f"base_{chave}")
    tamanho = n_total
    if base != "Tabela inteira":
        tamanho = st.number_input(f"Tamanho da amostra (o dataset tem {n_total} linhas)",
                                  min_value=min(config.AMOSTRA_MINIMO, n_total), max_value=n_total,
                                  value=min(config.AMOSTRA_PADRAO, n_total), key=f"tamanho_{chave}")
    if tamanho > config.REGIME_TESTADO:
        st.warning("Fora do regime testado (até 300 linhas e 11 colunas): tempo e custo de API "
                   "podem crescer.", icon=":material/warning:")
    aviso_do_provedor()
    if st.button("Iniciar geração", type="primary", key=f"iniciar_{chave}"):
        return ("inteira" if base == "Tabela inteira" else "amostra"), int(tamanho)
    return None


def aviso_do_provedor():
    """Para onde os dados vao e quanto a geracao gasta, antes de ela comecar."""
    texto = (f"Provedor **{config.PROVEDOR}**, modelo **{config.MODELO}**: cerca de 30 chamadas "
             "numa geração nova, no máximo 80; no aperfeiçoamento, as chamadas que já têm "
             "resposta gravada não são cobradas.")
    if config.PROVEDOR == "openai":
        st.warning(f"{texto} As linhas da tabela vão para a API da OpenAI.", icon=":material/public:")
    else:
        st.info(texto)

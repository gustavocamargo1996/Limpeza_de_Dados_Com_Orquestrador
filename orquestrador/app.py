"""Ponto de entrada do Streamlit: escolhe a tela pelo estado do processo aberto."""
import sys
from pathlib import Path

# O Streamlit poe na busca so a pasta do script; o pacote mora na raiz do repositorio.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from orquestrador import controle, fluxo, lago, tela_guia, tela_ingestao, tela_painel, tela_resultado

MARCA = {controle.SUCESSO: ":material/check_circle:", controle.ANDAMENTO: ":material/pending:",
         controle.ERRO: ":material/error:"}

st.set_page_config(page_title="Orquestrador de limpeza", page_icon=":material/cleaning_services:",
                   layout="wide")
st.title("Orquestrador de limpeza de dados")

if not lago.disponivel():
    st.error("Bucket indisponível: rode `.\subir_seaweed.cmd` na raiz do repositório e "
             "recarregue a página.", icon=":material/cloud_off:")
    st.stop()

con = controle.conectar()
processo = controle.processo_aberto(con)
atual = controle.etapa_atual(con, processo) if processo else None

with st.sidebar:
    st.header("Etapas")
    if processo is None:
        st.caption("Nenhum processo aberto.")
    else:
        feitas = {e["ID_ETAPA"]: e["STATUS"] for e in controle.etapas(con, processo)}
        for etapa, nome, descricao in controle.ETAPAS:
            marca = MARCA.get(feitas.get(etapa), ":material/radio_button_unchecked:")
            st.markdown(f"{marca} {etapa}. {nome}", help=descricao)
        if st.button("Cancelar processo", icon=":material/close:"):
            fluxo.cancelar(con, processo)
            st.rerun()

if processo is None:
    tela_ingestao.mostrar(con)
elif atual is None or atual["ID_ETAPA"] == 1:
    tela_ingestao.pedir_nome(con, processo)
elif atual["ID_ETAPA"] in (2, 3):
    tela_guia.mostrar(con, processo)
elif atual["ID_ETAPA"] in (4, 5, 6, 7):
    tela_painel.mostrar(con, processo)
else:
    tela_resultado.mostrar(con, processo)

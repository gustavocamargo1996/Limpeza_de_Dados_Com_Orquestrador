"""Acompanha a geracao do limpador: etapa corrente, indicador de carregamento e cronometro."""
from datetime import datetime

import streamlit as st

from orquestrador import controle, fluxo, geracao
from orquestrador.controle import ANDAMENTO, ERRO

NOMES = {etapa: nome for etapa, nome, _ in controle.ETAPAS}


def mostrar(con, processo):
    """O painel da geracao ou, se ela falhou, o erro com a opcao de tentar de novo."""
    st.header("Geração do limpador")
    atual = controle.etapa_atual(con, processo)
    if atual["STATUS"] == ERRO:
        st.error(f"A geração falhou na etapa {atual['ID_ETAPA']}. {NOMES[atual['ID_ETAPA']]}.")
        st.code(atual["DETALHE"] or "sem detalhe", language=None)
        if st.button("Tentar de novo", type="primary", icon=":material/refresh:"):
            fluxo.tentar_de_novo(con, processo)
            st.rerun()
        return
    _acompanhar(con, processo)


@st.fragment(run_every=1)
def _acompanhar(con, processo):
    """A cada segundo: avanca o fluxo e mostra a etapa, o tempo e as chamadas."""
    etapa = fluxo.acompanhar(con, processo)
    if etapa not in (4, 5, 6) or controle.etapa_atual(con, processo)["STATUS"] != ANDAMENTO:
        st.rerun(scope="app")
    ctx = controle.contexto(con, processo)
    segundos = int(datetime.now().timestamp() - ctx["geracao"]["inicio"])
    total, novas = geracao.chamadas(ctx["destino"], ctx["geracao"]["reaproveitar"])
    with st.status(f"{NOMES[etapa]}…", state="running", expanded=True):
        for passo in (4, 5, 6):
            marca = (":material/check_circle:" if passo < etapa else
                     ":material/progress_activity:" if passo == etapa else
                     ":material/radio_button_unchecked:")
            st.markdown(f"{marca} {NOMES[passo]}")
    tempo, chamadas = st.columns(2)
    tempo.metric("Tempo de processamento", f"{segundos // 60:02d}:{segundos % 60:02d}")
    chamadas.metric("Chamadas ao LLM", total, help=f"{novas} sem resposta gravada")

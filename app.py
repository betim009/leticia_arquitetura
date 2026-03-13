from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

ARQUIVO_PROJETOS = "projetos.csv"
ARQUIVO_RELATORIOS = "relatorio.csv"

COLUNAS_PROJETOS = ["id", "projeto", "cliente", "data_inicial", "status"]
COLUNAS_BASE_RELATORIOS = ["id_projeto", "projeto"]
ETAPA_PADRAO = "Pesquisa de referências"

STATUS_ETAPA = ["não iniciado", "em andamento", "concluído"]
STATUS_PROJETO = ["não iniciado", "em andamento", "finalizado"]


def carregar_csv(caminho: str, colunas: list[str]) -> pd.DataFrame:
    try:
        df = pd.read_csv(caminho)
    except FileNotFoundError:
        df = pd.DataFrame(columns=colunas)
        df.to_csv(caminho, index=False)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=colunas)

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = ""
    return df[colunas]


def carregar_relatorios(caminho: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(caminho)
    except FileNotFoundError:
        df = pd.DataFrame(columns=[*COLUNAS_BASE_RELATORIOS, ETAPA_PADRAO])
        df.to_csv(caminho, index=False)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=[*COLUNAS_BASE_RELATORIOS, ETAPA_PADRAO])

    for coluna in COLUNAS_BASE_RELATORIOS:
        if coluna not in df.columns:
            df[coluna] = ""

    colunas_etapas = [c for c in df.columns if c not in COLUNAS_BASE_RELATORIOS]
    if not colunas_etapas:
        df[ETAPA_PADRAO] = "não iniciado"
        colunas_etapas = [ETAPA_PADRAO]

    return df[[*COLUNAS_BASE_RELATORIOS, *colunas_etapas]]


def salvar_csv(df: pd.DataFrame, caminho: str) -> None:
    df.to_csv(caminho, index=False)


def normalizar_texto(valor: object) -> str:
    return str(valor).strip().lower()


def normalizar_status_etapa(valor: object) -> str:
    mapa = {
        "nao iniciado": "não iniciado",
        "não iniciado": "não iniciado",
        "em andamento": "em andamento",
        "concluido": "concluído",
        "concluído": "concluído",
        "finalizado": "concluído",
    }
    return mapa.get(normalizar_texto(valor), "não iniciado")


def normalizar_status_projeto(valor: object) -> str:
    mapa = {
        "nao iniciado": "não iniciado",
        "não iniciado": "não iniciado",
        "em andamento": "em andamento",
        "concluido": "finalizado",
        "concluído": "finalizado",
        "finalizado": "finalizado",
    }
    return mapa.get(normalizar_texto(valor), "não iniciado")


def proximo_id(df_projetos: pd.DataFrame) -> int:
    if df_projetos.empty:
        return 1
    ids = pd.to_numeric(df_projetos["id"], errors="coerce").dropna()
    if ids.empty:
        return 1
    return int(ids.max()) + 1


def colunas_etapas(df_relatorios: pd.DataFrame) -> list[str]:
    return [c for c in df_relatorios.columns if c not in COLUNAS_BASE_RELATORIOS]


def garantir_relatorio_para_projeto(
    df_relatorios: pd.DataFrame, id_projeto: int, nome_projeto: str
) -> pd.DataFrame:
    existe = pd.to_numeric(df_relatorios["id_projeto"], errors="coerce").eq(id_projeto).any()
    if existe:
        return df_relatorios

    etapas = colunas_etapas(df_relatorios)
    dados_novo = {"id_projeto": id_projeto, "projeto": nome_projeto}
    for etapa in etapas:
        dados_novo[etapa] = "não iniciado"
    return pd.concat([df_relatorios, pd.DataFrame([dados_novo])], ignore_index=True)


def sincronizar_relatorios(df_projetos: pd.DataFrame, df_relatorios: pd.DataFrame) -> pd.DataFrame:
    atualizado = df_relatorios.copy()
    for linha in df_projetos.itertuples():
        try:
            pid = int(linha.id)
        except (ValueError, TypeError):
            continue

        atualizado = garantir_relatorio_para_projeto(atualizado, pid, str(linha.projeto).strip())
        mascara = pd.to_numeric(atualizado["id_projeto"], errors="coerce").eq(pid)
        atualizado.loc[mascara, "projeto"] = str(linha.projeto).strip()

    atualizado = atualizado.drop_duplicates(subset=["id_projeto"], keep="last")
    for etapa in colunas_etapas(atualizado):
        atualizado[etapa] = atualizado[etapa].apply(normalizar_status_etapa)
    return atualizado


def calcular_progresso(df_relatorios: pd.DataFrame) -> pd.DataFrame:
    etapas = colunas_etapas(df_relatorios)
    if not etapas:
        return pd.DataFrame(columns=["id_projeto", "progresso_pct", "proxima_etapa"])

    base = df_relatorios.copy()
    for etapa in etapas:
        base[etapa] = base[etapa].apply(normalizar_status_etapa)

    concluidas = base[etapas].eq("concluído").sum(axis=1)
    progresso = (concluidas / len(etapas) * 100).round(1)

    def proxima_linha(linha: pd.Series) -> str:
        for etapa in etapas:
            if linha[etapa] != "concluído":
                return etapa
        return "Projeto concluído"

    return pd.DataFrame(
        {
            "id_projeto": pd.to_numeric(base["id_projeto"], errors="coerce"),
            "progresso_pct": progresso,
            "proxima_etapa": base.apply(proxima_linha, axis=1),
        }
    )


def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filtros da visão geral", expanded=False):
        c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.0, 1.5, 1.3])
        clientes = sorted([c for c in df["cliente"].dropna().astype(str).unique() if c.strip()])
        projetos = sorted([p for p in df["projeto"].dropna().astype(str).unique() if p.strip()])
        status = sorted([s for s in df["status"].dropna().astype(str).unique() if s.strip()])

        cliente_sel = c1.multiselect("Cliente", clientes, placeholder="Todos")
        projeto_sel = c2.multiselect("Projeto", projetos, placeholder="Todos")
        status_sel = c3.multiselect("Status", status, placeholder="Todos")
        periodo_sel = c4.date_input("Período de início", value=(), format="DD/MM/YYYY")
        busca = c5.text_input("Busca rápida", placeholder="Projeto ou cliente")

    filtrado = df.copy()
    if cliente_sel:
        filtrado = filtrado[filtrado["cliente"].isin(cliente_sel)]
    if projeto_sel:
        filtrado = filtrado[filtrado["projeto"].isin(projeto_sel)]
    if status_sel:
        filtrado = filtrado[filtrado["status"].isin(status_sel)]
    if busca.strip():
        termo = busca.strip().lower()
        mascara_busca = filtrado["projeto"].astype(str).str.lower().str.contains(termo) | filtrado[
            "cliente"
        ].astype(str).str.lower().str.contains(termo)
        filtrado = filtrado[mascara_busca]

    if isinstance(periodo_sel, tuple) and len(periodo_sel) == 2:
        inicio = pd.to_datetime(periodo_sel[0])
        fim = pd.to_datetime(periodo_sel[1])
        filtrado = filtrado[
            (filtrado["data_inicial_dt"].notna())
            & (filtrado["data_inicial_dt"] >= inicio)
            & (filtrado["data_inicial_dt"] <= fim)
        ]
    return filtrado


def mensagem_sucesso(texto: str) -> None:
    instante = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.session_state["mensagem_sucesso"] = f"{texto} | Última atualização: {instante}"


if __name__ == "__main__":
    st.set_page_config(page_title="Gestão de Projetos de Arquitetura", layout="wide")

    st.title("Gestão de Projetos de Arquitetura Civil")
    st.caption("Cadastro, acompanhamento de etapas e atualização de progresso")
    if st.session_state.get("mensagem_sucesso"):
        st.success(st.session_state["mensagem_sucesso"])
        del st.session_state["mensagem_sucesso"]

    df_projetos = carregar_csv(ARQUIVO_PROJETOS, COLUNAS_PROJETOS)
    df_relatorios = carregar_relatorios(ARQUIVO_RELATORIOS)

    df_projetos["status"] = df_projetos["status"].apply(normalizar_status_projeto)
    df_projetos["id"] = pd.to_numeric(df_projetos["id"], errors="coerce")
    df_projetos["data_inicial_dt"] = pd.to_datetime(
        df_projetos["data_inicial"], dayfirst=True, errors="coerce"
    )

    df_relatorios = sincronizar_relatorios(df_projetos, df_relatorios)
    salvar_csv(df_relatorios, ARQUIVO_RELATORIOS)

    progresso = calcular_progresso(df_relatorios)
    df_geral = df_projetos.merge(progresso, left_on="id", right_on="id_projeto", how="left")
    df_geral["progresso_pct"] = df_geral["progresso_pct"].fillna(0.0)
    df_geral["proxima_etapa"] = df_geral["proxima_etapa"].fillna("Sem etapas")
    df_geral["status"] = df_geral["status"].fillna("não iniciado")

    abas = ["Dashboard", "Projetos", "Etapas", "Excluir"]
    aba_ativa = st.radio(
        "Navegação",
        abas,
        horizontal=True,
        label_visibility="collapsed",
        key="aba_ativa",
    )

    if aba_ativa == "Dashboard":
        df_filtrado = aplicar_filtros(df_geral)
        st.caption(f"{len(df_filtrado)} projeto(s) encontrado(s)")
        st.markdown("### Distribuição de status e indicadores")
        status_serie = df_filtrado["status"].apply(normalizar_status_projeto)
        status_serie = status_serie.replace({"finalizado": "concluído"})
        resumo_status = (
            status_serie.value_counts()
            .reindex(["não iniciado", "em andamento", "concluído"], fill_value=0)
            .rename_axis("status")
            .reset_index(name="quantidade")
        )

        col_grafico, col_metricas = st.columns([1.2, 1.0], gap="large")
        with col_grafico:
            if int(resumo_status["quantidade"].sum()) == 0:
                st.info("Sem projetos para exibir no gráfico.")
            else:
                fig_status = px.pie(
                    resumo_status,
                    names="status",
                    values="quantidade",
                    hole=0.55,
                    color="status",
                    color_discrete_map={
                        "não iniciado": "#9CA3AF",
                        "em andamento": "#F59E0B",
                        "concluído": "#10B981",
                    },
                )
                fig_status.update_traces(textposition="inside", textinfo="percent+label")
                fig_status.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    legend_title_text="Status",
                    width=420,
                    height=280,
                )
                st.plotly_chart(fig_status, use_container_width=False)

        with col_metricas:
            st.metric("Projetos", int(df_filtrado["id"].notna().sum()))
            st.metric("Média de progresso", f"{df_filtrado['progresso_pct'].mean():.1f}%")
            st.metric("Concluídos", int((df_filtrado["progresso_pct"] == 100).sum()))

        st.markdown("### Visão geral")
        cols = [
            "id",
            "projeto",
            "cliente",
            "data_inicial",
            "status",
            "progresso_pct",
            "proxima_etapa",
        ]
        tabela = (
            df_filtrado[cols]
            .sort_values(["progresso_pct", "projeto"], ascending=[True, True])
            .rename(
            columns={"id": "ID", "progresso_pct": "Progresso (%)", "proxima_etapa": "Próxima etapa"}
        )
        )
        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", format="%d", width="small"),
                "projeto": st.column_config.TextColumn("Projeto", width="medium"),
                "cliente": st.column_config.TextColumn("Cliente", width="medium"),
                "data_inicial": st.column_config.TextColumn("Data inicial", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "Progresso (%)": st.column_config.ProgressColumn(
                    "Progresso (%)", min_value=0, max_value=100, format="%.1f%%"
                ),
                "Próxima etapa": st.column_config.TextColumn("Próxima etapa", width="large"),
            },
        )

        st.markdown("### Próximas etapas pendentes")
        cards = df_filtrado.sort_values("progresso_pct", ascending=True).head(6)
        if cards.empty:
            st.info("Nenhum projeto para exibir.")
        else:
            for _, linha in cards.iterrows():
                progresso_item = max(0, min(100, int(round(float(linha["progresso_pct"])))))
                st.write(
                    f"**{linha['projeto']}**  |  Cliente: {linha['cliente']}  |  Próxima etapa: {linha['proxima_etapa']}"
                )
                st.progress(progresso_item)

    if aba_ativa == "Projetos":
        st.subheader("Cadastro de Projeto")
        c_form, c_acao = st.columns([1.4, 1.0], gap="large")
        with c_form:
            with st.form("form_projeto", clear_on_submit=True):
                nome_projeto = st.text_input("Projeto")
                cliente = st.text_input("Cliente")
                data_inicial = st.date_input("Data inicial", format="DD/MM/YYYY")
                status = st.selectbox("Status", STATUS_PROJETO, index=0)
                enviar = st.form_submit_button("Salvar projeto", type="primary")

                if enviar:
                    nome_limpo = nome_projeto.strip()
                    if not nome_limpo:
                        st.error("Informe o nome do projeto.")
                    elif normalizar_texto(nome_limpo) in {
                        normalizar_texto(v) for v in df_projetos["projeto"].astype(str).tolist()
                    }:
                        st.error("Já existe um projeto com esse nome.")
                    else:
                        novo_id = proximo_id(df_projetos)
                        novo = pd.DataFrame(
                            [
                                {
                                    "id": novo_id,
                                    "projeto": nome_limpo,
                                    "cliente": cliente.strip(),
                                    "data_inicial": data_inicial.strftime("%d/%m/%Y"),
                                    "status": status,
                                }
                            ]
                        )
                        df_projetos_atualizado = pd.concat(
                            [df_projetos[COLUNAS_PROJETOS], novo], ignore_index=True
                        )
                        salvar_csv(df_projetos_atualizado, ARQUIVO_PROJETOS)

                        df_relatorios_atualizado = garantir_relatorio_para_projeto(
                            df_relatorios.copy(), int(novo_id), nome_limpo
                        )
                        salvar_csv(df_relatorios_atualizado, ARQUIVO_RELATORIOS)
                        mensagem_sucesso("Projeto cadastrado e vinculado ao relatório")
                        st.rerun()

        with c_acao:
            st.markdown("##### Atualização rápida de status")
            if df_projetos.dropna(subset=["id"]).empty:
                st.info("Sem projetos cadastrados.")
            else:
                opcoes_status = {
                    f"{int(linha.id)} - {linha.projeto}": int(linha.id)
                    for linha in df_projetos.dropna(subset=["id"]).itertuples()
                }
                with st.form("form_status_rapido"):
                    projeto_status = st.selectbox("Projeto", list(opcoes_status.keys()))
                    novo_status = st.selectbox("Novo status", STATUS_PROJETO)
                    enviar_status = st.form_submit_button("Atualizar status")

                    if enviar_status:
                        pid = opcoes_status[projeto_status]
                        df_projetos_atualizado = df_projetos.copy()
                        mascara_status = pd.to_numeric(
                            df_projetos_atualizado["id"], errors="coerce"
                        ).eq(pid)
                        df_projetos_atualizado.loc[mascara_status, "status"] = novo_status
                        salvar_csv(df_projetos_atualizado[COLUNAS_PROJETOS], ARQUIVO_PROJETOS)
                        mensagem_sucesso("Status do projeto atualizado")
                        st.rerun()

        st.markdown("### Projetos cadastrados")
        st.dataframe(
            df_projetos[COLUNAS_PROJETOS].sort_values("id", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", format="%d", width="small"),
                "projeto": st.column_config.TextColumn("Projeto", width="medium"),
                "cliente": st.column_config.TextColumn("Cliente", width="medium"),
                "data_inicial": st.column_config.TextColumn("Data inicial", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
            },
        )

    if aba_ativa == "Etapas":
        st.subheader("Atualização de Etapas")
        if df_projetos.empty:
            st.info("Cadastre um projeto antes de atualizar etapas.")
        else:
            opcoes = {
                f"{int(linha.id)} - {linha.projeto}": (int(linha.id), str(linha.projeto))
                for linha in df_projetos.dropna(subset=["id"]).itertuples()
            }
            projeto_sel = st.selectbox("Projeto", list(opcoes.keys()))
            id_projeto, nome_projeto = opcoes[projeto_sel]

            df_relatorios_base = garantir_relatorio_para_projeto(
                df_relatorios.copy(), id_projeto, nome_projeto
            )
            mascara = pd.to_numeric(df_relatorios_base["id_projeto"], errors="coerce").eq(id_projeto)
            linha = df_relatorios_base.loc[mascara].iloc[-1]
            etapas = colunas_etapas(df_relatorios_base)
            etapas_concluidas = sum(
                1 for etapa in etapas if normalizar_status_etapa(linha[etapa]) == "concluído"
            )
            progresso_atual = 0.0 if not etapas else round((etapas_concluidas / len(etapas)) * 100, 1)
            proxima = "Projeto concluído"
            for etapa in etapas:
                if normalizar_status_etapa(linha[etapa]) != "concluído":
                    proxima = etapa
                    break

            m1, m2, m3 = st.columns(3)
            m1.metric("Progresso atual", f"{progresso_atual:.1f}%")
            m2.metric("Etapas concluídas", f"{etapas_concluidas}/{len(etapas)}")
            m3.metric("Próxima etapa", proxima)
            st.progress(int(max(0, min(100, round(progresso_atual)))))

            editor_df = pd.DataFrame(
                {
                    "Etapa": etapas,
                    "Status": [normalizar_status_etapa(linha[etapa]) for etapa in etapas],
                }
            )
            modo = st.radio("Exibição", ["Todas as etapas", "Apenas pendentes"], horizontal=True)
            if modo == "Apenas pendentes":
                editor_df = editor_df[editor_df["Status"] != "concluído"].reset_index(drop=True)

            if editor_df.empty:
                st.info("Todas as etapas deste projeto já estão concluídas.")
                c1, c2 = st.columns(2)
                concluir_tudo = c1.button("Marcar tudo como concluído", use_container_width=True)
                resetar = c2.button("Resetar projeto", use_container_width=True)
                if concluir_tudo:
                    for etapa in etapas:
                        df_relatorios_base.loc[mascara, etapa] = "concluído"
                    salvar_csv(df_relatorios_base, ARQUIVO_RELATORIOS)
                    mensagem_sucesso("Todas as etapas foram concluídas")
                    st.rerun()
                if resetar:
                    for etapa in etapas:
                        df_relatorios_base.loc[mascara, etapa] = "não iniciado"
                    salvar_csv(df_relatorios_base, ARQUIVO_RELATORIOS)
                    mensagem_sucesso("Etapas resetadas para não iniciado")
                    st.rerun()
            else:
                editado = st.data_editor(
                    editor_df,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="fixed",
                    column_config={
                        "Etapa": st.column_config.TextColumn("Etapa", disabled=True),
                        "Status": st.column_config.SelectboxColumn("Status", options=STATUS_ETAPA),
                    },
                    key=f"editor_{id_projeto}_{modo}",
                )

                c1, c2, c3 = st.columns(3)
                salvar = c1.button("Salvar atualização", type="primary", use_container_width=True)
                concluir_tudo = c2.button("Marcar tudo como concluído", use_container_width=True)
                resetar = c3.button("Resetar projeto", use_container_width=True)

                if salvar:
                    mapa = {
                        str(linha_editada["Etapa"]): normalizar_status_etapa(linha_editada["Status"])
                        for _, linha_editada in editado.iterrows()
                    }
                    for etapa, valor in mapa.items():
                        df_relatorios_base.loc[mascara, etapa] = valor

                    df_relatorios_base.loc[mascara, "projeto"] = nome_projeto
                    df_relatorios_base = df_relatorios_base.drop_duplicates(
                        subset=["id_projeto"], keep="last"
                    )
                    salvar_csv(df_relatorios_base, ARQUIVO_RELATORIOS)
                    mensagem_sucesso("Etapas atualizadas com sucesso")
                    st.rerun()

                if concluir_tudo:
                    for etapa in etapas:
                        df_relatorios_base.loc[mascara, etapa] = "concluído"
                    salvar_csv(df_relatorios_base, ARQUIVO_RELATORIOS)
                    mensagem_sucesso("Todas as etapas foram concluídas")
                    st.rerun()

                if resetar:
                    for etapa in etapas:
                        df_relatorios_base.loc[mascara, etapa] = "não iniciado"
                    salvar_csv(df_relatorios_base, ARQUIVO_RELATORIOS)
                    mensagem_sucesso("Etapas resetadas para não iniciado")
                    st.rerun()

    if aba_ativa == "Excluir":
        st.subheader("Excluir projeto")
        if df_projetos.dropna(subset=["id"]).empty:
            st.info("Não há projetos para excluir.")
        else:
            opcoes_exclusao = {
                f"{int(linha.id)} - {linha.projeto}": int(linha.id)
                for linha in df_projetos.dropna(subset=["id"]).itertuples()
            }
            with st.form("form_excluir_projeto"):
                projeto_excluir = st.selectbox("Projeto", list(opcoes_exclusao.keys()))
                confirmar = st.checkbox("Confirmo que desejo excluir projeto e relatório")
                excluir = st.form_submit_button("Excluir projeto", type="primary")

                if excluir:
                    if not confirmar:
                        st.error("Marque a confirmação para prosseguir.")
                    else:
                        id_excluir = opcoes_exclusao[projeto_excluir]
                        df_projetos_atualizado = df_projetos.copy()
                        df_relatorios_atualizado = df_relatorios.copy()

                        mask_proj = pd.to_numeric(
                            df_projetos_atualizado["id"], errors="coerce"
                        ).ne(id_excluir)
                        mask_rel = pd.to_numeric(
                            df_relatorios_atualizado["id_projeto"], errors="coerce"
                        ).ne(id_excluir)

                        salvar_csv(
                            df_projetos_atualizado.loc[mask_proj, COLUNAS_PROJETOS],
                            ARQUIVO_PROJETOS,
                        )
                        salvar_csv(df_relatorios_atualizado.loc[mask_rel], ARQUIVO_RELATORIOS)
                        mensagem_sucesso("Projeto e relatório excluídos com sucesso")
                        st.rerun()

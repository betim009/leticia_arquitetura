import pandas as pd
import streamlit as st

ARQUIVO_PROJETOS = "projetos.csv"
ARQUIVO_RELATORIOS = "relatorio.csv"

COLUNAS_PROJETOS = ["id", "projeto", "cliente", "data_inicial", "status"]
COLUNAS_RELATORIOS = ["id_projeto", "projeto", "pesquisa de referencias"]


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


def salvar_csv(df: pd.DataFrame, caminho: str) -> None:
    df.to_csv(caminho, index=False)


def proximo_id(df_projetos: pd.DataFrame) -> int:
    if df_projetos.empty:
        return 1
    ids = pd.to_numeric(df_projetos["id"], errors="coerce")
    ids = ids.dropna()
    if ids.empty:
        return 1
    return int(ids.max()) + 1


def garantir_relatorio_para_projeto(
    df_relatorios: pd.DataFrame, id_projeto: int, nome_projeto: str
) -> pd.DataFrame:
    existe = pd.to_numeric(df_relatorios["id_projeto"], errors="coerce").eq(id_projeto).any()
    if existe:
        return df_relatorios

    novo_relatorio = pd.DataFrame(
        [
            {
                "id_projeto": id_projeto,
                "projeto": nome_projeto,
                "pesquisa de referencias": "nao iniciado",
            }
        ]
    )
    return pd.concat([df_relatorios, novo_relatorio], ignore_index=True)


if __name__ == "__main__":
    st.set_page_config(page_title="Gestao de Projetos de Arquitetura", layout="wide")
    st.title("Sistema de Projetos e Relatorios")
    st.caption("Arquitetura civil - cadastro e acompanhamento")

    df_projetos = carregar_csv(ARQUIVO_PROJETOS, COLUNAS_PROJETOS)
    df_relatorios = carregar_csv(ARQUIVO_RELATORIOS, COLUNAS_RELATORIOS)

    aba_inicio, aba_cadastro = st.tabs(["Pagina Inicial", "Cadastro de Projeto"])

    with aba_inicio:
        c1, c2 = st.columns(2)
        c1.metric("Total de Projetos", len(df_projetos))
        c2.metric("Total de Relatorios", len(df_relatorios))

        st.subheader("Projetos")
        st.dataframe(df_projetos, use_container_width=True, hide_index=True)

        st.subheader("Relatorios")
        st.dataframe(df_relatorios, use_container_width=True, hide_index=True)

    with aba_cadastro:
        st.subheader("Cadastrar Projeto")
        with st.form("form_projeto", clear_on_submit=True):
            nome_projeto = st.text_input("Projeto")
            cliente = st.text_input("Cliente")
            data_inicial = st.date_input("Data inicial", format="DD/MM/YYYY")
            status = st.selectbox(
                "Status",
                ["nao iniciado", "em andamento", "finalizado"],
                index=0,
            )
            enviar_projeto = st.form_submit_button("Salvar projeto")

            if enviar_projeto:
                if not nome_projeto.strip():
                    st.error("Informe o nome do projeto.")
                else:
                    novo_id = proximo_id(df_projetos)
                    novo_projeto = pd.DataFrame(
                        [
                            {
                                "id": novo_id,
                                "projeto": nome_projeto.strip(),
                                "cliente": cliente.strip(),
                                "data_inicial": data_inicial.strftime("%d/%m/%Y"),
                                "status": status,
                            }
                        ]
                    )
                    df_projetos_atualizado = pd.concat(
                        [df_projetos, novo_projeto], ignore_index=True
                    )
                    salvar_csv(df_projetos_atualizado, ARQUIVO_PROJETOS)

                    df_relatorios_atualizado = garantir_relatorio_para_projeto(
                        df_relatorios, novo_id, nome_projeto.strip()
                    )
                    salvar_csv(df_relatorios_atualizado, ARQUIVO_RELATORIOS)
                    st.success("Projeto cadastrado e vinculado ao relatorio.")
                    st.rerun()

        st.divider()
        st.subheader("Atualizar Etapas do Relatorio")
        if df_projetos.empty:
            st.info("Cadastre um projeto antes de atualizar relatorios.")
        else:
            opcoes_projeto = {
                f"{linha.id} - {linha.projeto}": (linha.id, linha.projeto)
                for linha in df_projetos.itertuples()
            }

            colunas_etapas = [
                coluna
                for coluna in df_relatorios.columns
                if coluna not in ["id_projeto", "projeto"]
            ]

            with st.form("form_atualizar_relatorio", clear_on_submit=True):
                projeto_selecionado = st.selectbox("Projeto", list(opcoes_projeto.keys()))
                etapa = st.selectbox("Etapa", colunas_etapas)
                valor_etapa = st.selectbox(
                    "Status da etapa",
                    ["nao iniciado", "em andamento", "concluido"],
                    index=0,
                )
                enviar_relatorio = st.form_submit_button("Atualizar relatorio")

                if enviar_relatorio:
                    id_projeto, nome_projeto = opcoes_projeto[projeto_selecionado]

                    df_relatorios_atualizado = garantir_relatorio_para_projeto(
                        df_relatorios.copy(), int(id_projeto), nome_projeto
                    )

                    mascara_projeto = pd.to_numeric(
                        df_relatorios_atualizado["id_projeto"], errors="coerce"
                    ).eq(int(id_projeto))
                    df_relatorios_atualizado.loc[mascara_projeto, "projeto"] = nome_projeto
                    df_relatorios_atualizado.loc[mascara_projeto, etapa] = valor_etapa

                    df_relatorios_atualizado = df_relatorios_atualizado.drop_duplicates(
                        subset=["id_projeto"], keep="last"
                    )
                    salvar_csv(df_relatorios_atualizado, ARQUIVO_RELATORIOS)
                    st.success("Relatorio atualizado sem duplicar registros.")
                    st.rerun()

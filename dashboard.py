import os
import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px
from bson import ObjectId
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Configuração da página
st.set_page_config(
    page_title="Monitoramento Inteligente - App Acessibilidade",
    layout="wide"
)

# Carrega variáveis do .env, se existir
load_dotenv()

# conexao com o MongoDB
@st.cache_resource
def connect_mongo():
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB")

    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        client.admin.command('ping')
    except Exception:
        client = MongoClient(uri)
        client.admin.command('ping')

    return client[db_name]

db = connect_mongo()

# Funções auxiliares
def to_df(data):
    return pd.DataFrame(data) if data else pd.DataFrame()


st.sidebar.title("📡 Monitoramento Ativo")
page = st.sidebar.radio("Navegação", [
    "Visão Geral",
    "Objetos",
    "History (Eventos)",
    "Scans"
])

refresh = st.sidebar.button("🔄 Atualizar Agora")

# Fluxo principal
if page == "Visão Geral":
    st.title("📊 Monitoramento Geral do Sistema")

    users = list(db.users.find())
    residences = list(db.residences.find())
    objects = list(db.objects.find())
    scans = list(db.scans.find())
    history = list(db.history.find())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Usuários", len(users))
    col2.metric("Residências", len(residences))
    col3.metric("Objetos Detectados", len(objects))
    col4.metric("Total de Scans", len(scans))

    st.subheader("📍 Objetos mais recentes")
    df_objects = to_df(objects)
    if not df_objects.empty:
        df_objects["last_seen"] = pd.to_datetime(df_objects["last_seen"])
        st.dataframe(df_objects.sort_values("last_seen", ascending=False))


# grafico de objetos por tipo
if page == "Objetos":
    st.title("📦 Monitoramento de Objetos com Filtros Inteligentes")

    # filtro usuário
    users = list(db.users.find())
    df_users = to_df(users)

    user_names = df_users["name"].tolist()
    selected_user_name = st.selectbox("👤 Selecionar usuário", [""] + user_names)

    if selected_user_name:
        selected_user = df_users[df_users["name"] == selected_user_name].iloc[0]
        user_id = selected_user["_id"]

        # filtro residência
        residences = list(db.residences.find({"user_id": user_id}))
        df_res = to_df(residences)

        res_names = df_res["name"].tolist()
        selected_res_name = st.selectbox("🏠 Selecionar residência", [""] + res_names)

        if selected_res_name:
            selected_res = df_res[df_res["name"] == selected_res_name].iloc[0]
            residence_id = selected_res["_id"]

            # filtro scan
            scans = list(db.scans.find({"residence_id": residence_id}))
            df_scans = to_df(scans)

            scan_options = [str(x["_id"]) for x in scans]
            selected_scan_id = st.selectbox("📷 Selecionar scan", [""] + scan_options)

            # Se TUDO estiver selecionado → filtra objetos
            if selected_scan_id:
                selected_scan_id = ObjectId(selected_scan_id)

                objects = list(db.objects.find({
                    "residence_id": residence_id,
                    "scan_id": selected_scan_id
                }))

                df = to_df(objects)

                if df.empty:
                    st.info("Nenhum objeto encontrado para este filtro.")
                else:
                    df["first_seen"] = pd.to_datetime(df["first_seen"])
                    df["last_seen"] = pd.to_datetime(df["last_seen"])

                    st.subheader("📦 Objetos filtrados")
                    st.dataframe(df[[
                        "name", "type", "color", "coordinates",
                        "first_seen", "last_seen", "status", "confidence"
                    ]])

                    # Gráfico 3D
                    try:
                        fig = px.scatter_3d(
                            df,
                            x=df["coordinates"].apply(lambda c: c["x"]),
                            y=df["coordinates"].apply(lambda c: c["y"]),
                            z=df["coordinates"].apply(lambda c: c["z"]),
                            color="type",
                            title="Mapa 3D dos Objetos no Scan"
                        )
                        st.plotly_chart(fig)
                    except:
                        st.warning("Alguns objetos não possuem coordenadas completas.")


# grafico de histórico de eventos
if page == "History (Eventos)":
    st.title("🔔 Histórico Inteligente do Ambiente")

    # filtro usuário
    users = list(db.users.find())
    df_users = to_df(users)

    selected_user = st.selectbox("👤 Selecionar usuário", [""] + df_users["name"].tolist())

    if selected_user:
        user_id = df_users[df_users["name"] == selected_user].iloc[0]["_id"]

        # filtro objetos do usuário (via residências)
        residences = list(db.residences.find({"user_id": user_id}))
        residence_ids = [r["_id"] for r in residences]

        objects = list(db.objects.find({"residence_id": {"$in": residence_ids}}))
        df_objects = to_df(objects)

        obj_names = df_objects["name"].tolist()
        selected_obj_name = st.selectbox("📦 Selecionar objeto", [""] + obj_names)

        if selected_obj_name:
            obj_id = df_objects[df_objects["name"] == selected_obj_name].iloc[0]["_id"]

            history = list(db.history.find({"object_id": obj_id}))
            df_history = to_df(history)

            if df_history.empty:
                st.info("Nenhum histórico encontrado.")
            else:
                df_history["timestamp"] = pd.to_datetime(df_history["timestamp"])
                st.dataframe(df_history.sort_values("timestamp", ascending=False))

                fig = px.histogram(
                    df_history,
                    x="action_type",
                    title="Distribuição de eventos deste objeto"
                )
                st.plotly_chart(fig)


# grafico de scans
if page == "Scans":
    st.title("📷 Histórico de Scans com Filtros Inteligentes")

    users = list(db.users.find())
    df_users = to_df(users)

    selected_user = st.selectbox("👤 Selecionar usuário", [""] + df_users["name"].tolist())

    if selected_user:
        user_id = df_users[df_users["name"] == selected_user].iloc[0]["_id"]

        residences = list(db.residences.find({"user_id": user_id}))
        df_res = to_df(residences)

        selected_res = st.selectbox("🏠 Selecionar residência", [""] + df_res["name"].tolist())

        if selected_res:
            residence_id = df_res[df_res["name"] == selected_res].iloc[0]["_id"]

            scans = list(db.scans.find({"residence_id": residence_id}))
            df_scans = to_df(scans)

            if df_scans.empty:
                st.info("Nenhum scan encontrado.")
            else:
                df_scans["timestamp"] = pd.to_datetime(df_scans["timestamp"])
                st.dataframe(df_scans.sort_values("timestamp", ascending=False))

                fig = px.line(
                    df_scans,
                    x="timestamp",
                    y="objects_detected_count",
                    title="Objetos Detectados por Scan"
                )
                st.plotly_chart(fig)

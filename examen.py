import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px

# ==========================
# CONFIGURACIÓN DE PÁGINA
# ==========================
st.set_page_config(
    page_title="Dashboard EcoRuta",
    page_icon="♻️",
    layout="wide"
)

st.title("♻️ Dashboard EcoRuta")
st.markdown("### Análisis de rutas, barrios y recolectores")

# ==========================
# CONEXIÓN A MYSQL
# ==========================
def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",    # <-- Cambia si tu MySQL tiene clave
        database="ecoruta_db"
    )

# ==========================
# CONSULTA PRINCIPAL
# ==========================
@st.cache_data
def load_data():
    conn = get_connection()
    query = """
    SELECT 
        v.id_visita,
        v.fecha_visita,
        v.cantidad_kg,
        v.completada,
        r.nombre_ruta,
        r.tipo_material,
        r.frecuencia,
        b.nombre_barrio,
        rec.nombre_completo AS recolector
    FROM visita v
    JOIN ruta r ON v.ruta_id_ruta = r.id_ruta
    JOIN barrio b ON r.barrio_id_barrio = b.id_barrio
    JOIN recolector rec ON v.recolector_id_recolector = rec.id_recolector;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Cargar los datos
df = load_data()

# ==========================
# NORMALIZAR FECHAS (SOLUCIÓN DEL ERROR)
# ==========================
df["fecha_visita"] = pd.to_datetime(df["fecha_visita"], errors="coerce").dt.normalize()

# ==========================
# FILTROS
# ==========================
st.sidebar.header("🔎 Filtros")

fecha_min = df["fecha_visita"].min().date()
fecha_max = df["fecha_visita"].max().date()

# Rango de fechas desde Streamlit (devuelve datetime.date)
rango_fechas = st.sidebar.date_input("Rango de fechas", (fecha_min, fecha_max))

barrios_filtro = st.sidebar.multiselect("Barrio", df["nombre_barrio"].unique())
recolector_filtro = st.sidebar.multiselect("Recolector", df["recolector"].unique())

# Copia del dataframe
df_filtrado = df.copy()

# ==========================
# FILTRO POR FECHAS — VERSIÓN A PRUEBA DE ERRORES
# ==========================
if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:

    fecha_inicio = pd.to_datetime(rango_fechas[0])
    fecha_fin = pd.to_datetime(rango_fechas[1])

    df_filtrado = df_filtrado[
        (df_filtrado["fecha_visita"] >= fecha_inicio) &
        (df_filtrado["fecha_visita"] <= fecha_fin)
    ]

# Filtro por barrios
if barrios_filtro:
    df_filtrado = df_filtrado[df_filtrado["nombre_barrio"].isin(barrios_filtro)]

# Filtro por recolectores
if recolector_filtro:
    df_filtrado = df_filtrado[df_filtrado["recolector"].isin(recolector_filtro)]

# ==========================
# TABLA DE DATOS
# ==========================
st.subheader("📄 Datos Originales")
st.dataframe(df_filtrado, use_container_width=True)

# ==========================
# KPIs
# ==========================
col1, col2, col3 = st.columns(3)

total_kg = df_filtrado["cantidad_kg"].sum()

ruta_top = (
    df_filtrado["nombre_ruta"].value_counts().idxmax()
    if len(df_filtrado) > 0 else "N/A"
)

recolector_top = (
    df_filtrado["recolector"].value_counts().idxmax()
    if len(df_filtrado) > 0 else "N/A"
)

col1.metric("Total Kg Recolectados", f"{total_kg:.2f} kg")
col2.metric("Ruta con más visitas", ruta_top)
col3.metric("Recolector más activo", recolector_top)

# ==========================
# GRÁFICOS
# ==========================

# 1) Barras – kg por barrio
st.subheader("📊 Kg recolectados por barrio")
kg_barrio = df_filtrado.groupby("nombre_barrio")["cantidad_kg"].sum().reset_index()
fig1 = px.bar(kg_barrio, x="nombre_barrio", y="cantidad_kg", title="Kg por Barrio")
st.plotly_chart(fig1, use_container_width=True)

# 2) Pie – kg por recolector
st.subheader("🥧 Distribución de kg por recolector")
kg_recolector = df_filtrado.groupby("recolector")["cantidad_kg"].sum().reset_index()
fig2 = px.pie(kg_recolector, names="recolector", values="cantidad_kg", title="Kg por Recolector")
st.plotly_chart(fig2, use_container_width=True)

# 3) Línea – kg por fecha
st.subheader("📈 Kg recolectados por fecha")
kg_fecha = df_filtrado.groupby("fecha_visita")["cantidad_kg"].sum().reset_index()
fig3 = px.line(kg_fecha, x="fecha_visita", y="cantidad_kg", title="Kg por Fecha")
st.plotly_chart(fig3, use_container_width=True)

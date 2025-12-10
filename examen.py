import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime, timedelta

# ==========================
# CONFIGURACIÓN DE PÁGINA
# ==========================
st.set_page_config(
    page_title="Dashboard EcoRuta",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("♻️ Dashboard EcoRuta")
st.markdown("### Análisis de rutas, barrios y recolectores")

# ==========================
# CONEXIÓN A MYSQL
# ==========================
def get_connection():
    """Conexión a MySQL"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",    # Cambiar si MySQL tiene clave
            database="ecoruta_db"
        )
        return conn
    except Exception as e:
        st.error(f"❌ Error conectando a la base de datos: {e}")
        return None

# ==========================
# CARGA DE DATOS
# ==========================
@st.cache_data(ttl=600)
def load_data():
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
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
    try:
        df = pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"❌ Error en la consulta: {e}")
        return pd.DataFrame()
    finally:
        conn.close()
    
    # Normalizar fechas
    if 'fecha_visita' in df.columns:
        df['fecha_visita'] = pd.to_datetime(df['fecha_visita'], errors='coerce').dt.normalize()
    
    return df

# Cargar datos
df = load_data()
if df.empty:
    st.warning("⚠️ No se encontraron datos en la base de datos.")
    st.stop()

# ==========================
# SIDEBAR - FILTROS
# ==========================
st.sidebar.header("🔎 Filtros")

# Rango de fechas
fecha_min = df["fecha_visita"].min().date()
fecha_max = df["fecha_visita"].max().date()
rango_fechas = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

# Barrios
barrios_filtro = st.sidebar.multiselect("Barrio", df["nombre_barrio"].unique())

# Recolectores
recolector_filtro = st.sidebar.multiselect("Recolector", df["recolector"].unique())

# ==========================
# FILTRADO DE DATOS
# ==========================
df_filtrado = df.copy()

# Filtro fechas
if isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 2:
    fecha_inicio = pd.to_datetime(rango_fechas[0])
    fecha_fin = pd.to_datetime(rango_fechas[1])
    df_filtrado = df_filtrado[
        (df_filtrado["fecha_visita"] >= fecha_inicio) &
        (df_filtrado["fecha_visita"] <= fecha_fin)
    ]

# Filtro barrios
if barrios_filtro:
    df_filtrado = df_filtrado[df_filtrado["nombre_barrio"].isin(barrios_filtro)]

# Filtro recolectores
if recolector_filtro:
    df_filtrado = df_filtrado[df_filtrado["recolector"].isin(recolector_filtro)]

if df_filtrado.empty:
    st.warning("⚠️ No hay datos que coincidan con los filtros.")
    st.stop()

# ==========================
# KPIs
# ==========================
st.subheader("📊 Indicadores Clave (KPIs)")
col1, col2, col3 = st.columns(3)

total_kg = df_filtrado["cantidad_kg"].sum()
ruta_top = df_filtrado["nombre_ruta"].value_counts().idxmax() if not df_filtrado.empty else "N/A"
recolector_top = df_filtrado["recolector"].value_counts().idxmax() if not df_filtrado.empty else "N/A"

col1.metric("Total Kg Recolectados", f"{total_kg:.2f} kg")
col2.metric("Ruta con más visitas", ruta_top)
col3.metric("Recolector más activo", recolector_top)

st.divider()

# ==========================
# DATOS FILTRADOS
# ==========================
with st.expander("📋 Ver Datos Filtrados", expanded=False):
    st.dataframe(df_filtrado, use_container_width=True, height=300)
    
    # Botón de descarga CSV
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar CSV", csv, "datos_ecoruta.csv", "text/csv")

st.divider()

# ==========================
# VISUALIZACIONES
# ==========================
st.subheader("📈 Visualizaciones")

tab1, tab2, tab3 = st.tabs(["🏘️ Kg por Barrio", "👤 Kg por Recolector", "📅 Kg por Fecha"])

# TAB 1: Kg por Barrio
with tab1:
    kg_barrio = df_filtrado.groupby("nombre_barrio")["cantidad_kg"].sum().reset_index()
    fig1 = px.bar(kg_barrio, x="nombre_barrio", y="cantidad_kg", title="Kg recolectados por Barrio", color="nombre_barrio")
    st.plotly_chart(fig1, use_container_width=True)

# TAB 2: Kg por Recolector
with tab2:
    kg_recolector = df_filtrado.groupby("recolector")["cantidad_kg"].sum().reset_index()
    fig2 = px.pie(kg_recolector, names="recolector", values="cantidad_kg", title="Distribución de Kg por Recolector")
    st.plotly_chart(fig2, use_container_width=True)

# TAB 3: Kg por Fecha
with tab3:
    kg_fecha = df_filtrado.groupby("fecha_visita")["cantidad_kg"].sum().reset_index()
    fig3 = px.line(kg_fecha, x="fecha_visita", y="cantidad_kg", title="Kg recolectados por Fecha")
    st.plotly_chart(fig3, use_container_width=True)

# ==========================
# PIE DE PÁGINA
# ==========================
st.divider()
st.caption("♻️ Sistema EcoRuta - Base de Datos I 2024")

# ==========================
# INFORMACIÓN TÉCNICA (OPCIONAL)
# ==========================
with st.expander("🔧 Información Técnica", expanded=False):
    st.write("### 📋 Columnas disponibles:")
    st.write(list(df.columns))
    
    st.write("### 📊 Resumen estadístico:")
    st.dataframe(df.describe())
    
    st.write("### 🔗 Registros:")
    st.code(f"Total registros: {len(df)}")
    st.code(f"Registros filtrados: {len(df_filtrado)}")

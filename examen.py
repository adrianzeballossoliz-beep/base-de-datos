import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ================================================
# CONFIGURACIÓN
# ================================================
st.set_page_config(
    page_title="🌿 ECORUTA Dashboard",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================
# CONEXIÓN A BASE DE DATOS
# ================================================
@st.cache_resource
def get_connection():
    """Establece conexión con MySQL"""
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='',  # Déjalo vacío si no tienes contraseña
            database='ecoruta_db',
            port=3306,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

def get_data(query, params=None):
    """Ejecuta consulta y retorna DataFrame"""
    try:
        conn = get_connection()
        if params:
            df = pd.read_sql(query, conn, params=params)
        else:
            df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error en consulta: {e}")
        return pd.DataFrame()

def get_single_value(query, params=None):
    """Retorna un valor único"""
    df = get_data(query, params)
    if not df.empty:
        return df.iloc[0, 0]
    return 0

# ================================================
# SIDEBAR CON FILTROS
# ================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3095/3095113.png", width=80)
    st.title("🌿 ECORUTA")
    
    st.markdown("---")
    st.header("🔍 Filtros")
    
    # Obtener rangos de fechas
    fecha_min = get_single_value("SELECT MIN(fecha_visita) FROM visita")
    fecha_max = get_single_value("SELECT MAX(fecha_visita) FROM visita")
    
    if fecha_min and fecha_max:
        fecha_inicio = st.date_input(
            "📅 Fecha inicio",
            value=pd.to_datetime(fecha_min),
            min_value=pd.to_datetime(fecha_min),
            max_value=pd.to_datetime(fecha_max)
        )
        fecha_fin = st.date_input(
            "📅 Fecha fin",
            value=pd.to_datetime(fecha_max),
            min_value=pd.to_datetime(fecha_min),
            max_value=pd.to_datetime(fecha_max)
        )
    else:
        fecha_inicio = st.date_input("📅 Fecha inicio", value=datetime.now() - timedelta(days=30))
        fecha_fin = st.date_input("📅 Fecha fin", value=datetime.now())
    
    # Filtro por barrio
    barrios_df = get_data("SELECT id_barrio, nombre_barrio FROM barrio ORDER BY nombre_barrio")
    barrios_opciones = ["Todos"] + barrios_df['nombre_barrio'].tolist()
    barrio_seleccionado = st.selectbox("🏘️ Barrio", barrios_opciones)
    
    # Filtro por recolector
    recolectores_df = get_data("SELECT id_recolector, nombre_completo FROM recolector ORDER BY nombre_completo")
    recolectores_opciones = ["Todos"] + recolectores_df['nombre_completo'].tolist()
    recolector_seleccionado = st.selectbox("👷 Recolector", recolectores_opciones)
    
    st.markdown("---")
    
    # Estadísticas rápidas
    st.header("📊 Resumen")
    
    total_kg = get_single_value("SELECT COALESCE(SUM(cantidad_kg), 0) FROM visita")
    total_visitas = get_single_value("SELECT COUNT(*) FROM visita")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("KG Total", f"{total_kg:,.0f}")
    with col_s2:
        st.metric("Visitas", total_visitas)

# ================================================
# CONTENIDO PRINCIPAL
# ================================================
st.title("♻️ ECORUTA - Dashboard de Gestión")
st.markdown("---")

# ================================================
# 1. KPIs PRINCIPALES
# ================================================
st.header("📊 Métricas Clave")

# Calcular KPIs
total_barrios = get_single_value("SELECT COUNT(*) FROM barrio")
total_recolectores = get_single_value("SELECT COUNT(*) FROM recolector")
total_rutas = get_single_value("SELECT COUNT(*) FROM ruta")
total_kg = get_single_value("SELECT COALESCE(SUM(cantidad_kg), 0) FROM visita")
eficiencia = get_single_value("""
    SELECT COALESCE(AVG(CASE WHEN completada = 'Si' THEN 1 ELSE 0 END) * 100, 0) 
    FROM visita
""")

# Mostrar KPIs
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("🏘️ Barrios", total_barrios)

with col2:
    st.metric("👷 Recolectores", total_recolectores)

with col3:
    st.metric("🛣️ Rutas", total_rutas)

with col4:
    st.metric("📦 KG Total", f"{total_kg:,.0f}")

with col5:
    st.metric("📈 Eficiencia", f"{eficiencia:.1f}%")

st.markdown("---")

# ================================================
# 2. GRÁFICOS (3 REQUERIDOS)
# ================================================
st.header("📈 Visualizaciones")

# Gráfico 1: KG por barrio (BARRAS)
st.subheader("1. 📊 KG Recolectados por Barrio")
kg_barrio = get_data("""
    SELECT b.nombre_barrio, SUM(v.cantidad_kg) as total_kg
    FROM barrio b
    JOIN ruta r ON b.id_barrio = r.barrio_id_barrio
    JOIN visita v ON r.id_ruta = v.ruta_id_ruta
    GROUP BY b.id_barrio, b.nombre_barrio
    ORDER BY total_kg DESC
""")

if not kg_barrio.empty:
    fig1 = px.bar(
        kg_barrio,
        x='nombre_barrio',
        y='total_kg',
        color='total_kg',
        text='total_kg',
        color_continuous_scale='Viridis',
        height=400
    )
    fig1.update_layout(
        xaxis_title="Barrio",
        yaxis_title="Kilogramos (KG)",
        plot_bgcolor='rgba(0,0,0,0)'
    )
    fig1.update_traces(texttemplate='%{text:,.0f} kg', textposition='outside')
    st.plotly_chart(fig1, use_container_width=True)

# Gráfico 2: KG por recolector (PIE)
st.subheader("2. 👷 Distribución por Recolector")
col_g1, col_g2 = st.columns([2, 1])

with col_g1:
    kg_recolector = get_data("""
        SELECT r.nombre_completo, SUM(v.cantidad_kg) as total_kg
        FROM recolector r
        JOIN visita v ON r.id_recolector = v.recolector_id_recolector
        GROUP BY r.id_recolector, r.nombre_completo
        ORDER BY total_kg DESC
    """)
    
    if not kg_recolector.empty:
        fig2 = px.pie(
            kg_recolector,
            values='total_kg',
            names='nombre_completo',
            hole=0.3,
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)

with col_g2:
    if not kg_recolector.empty:
        st.dataframe(
            kg_recolector[['nombre_completo', 'total_kg']]
            .rename(columns={'nombre_completo': 'Recolector', 'total_kg': 'KG'})
            .sort_values('KG', ascending=False),
            height=400,
            use_container_width=True
        )

# Gráfico 3: KG por fecha (LÍNEA)
st.subheader("3. 📈 Tendencia por Fecha")
kg_fecha = get_data(f"""
    SELECT 
        DATE(fecha_visita) as fecha,
        SUM(cantidad_kg) as total_kg,
        COUNT(*) as total_visitas
    FROM visita
    WHERE fecha_visita BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
    GROUP BY DATE(fecha_visita)
    ORDER BY fecha
""")

if not kg_fecha.empty:
    fig3 = go.Figure()
    
    # Línea para KG
    fig3.add_trace(go.Scatter(
        x=kg_fecha['fecha'],
        y=kg_fecha['total_kg'],
        mode='lines+markers',
        name='KG Recolectados',
        line=dict(color='#4CAF50', width=3)
    ))
    
    # Barras para visitas (eje secundario)
    fig3.add_trace(go.Bar(
        x=kg_fecha['fecha'],
        y=kg_fecha['total_visitas'],
        name='Número de Visitas',
        yaxis='y2',
        marker_color='rgba(76, 175, 80, 0.3)'
    ))
    
    fig3.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Kilogramos (KG)",
        yaxis2=dict(
            title="Visitas",
            overlaying='y',
            side='right'
        ),
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ================================================
# 3. TABLA DE DATOS FILTRADOS
# ================================================
st.header("📋 Datos Detallados")

# Construir consulta con filtros
query = """
    SELECT 
        v.fecha_visita,
        v.cantidad_kg,
        v.completada,
        r.nombre_ruta,
        r.tipo_material,
        b.nombre_barrio,
        rec.nombre_completo as recolector
    FROM visita v
    JOIN ruta r ON v.ruta_id_ruta = r.id_ruta
    JOIN barrio b ON r.barrio_id_barrio = b.id_barrio
    JOIN recolector rec ON v.recolector_id_recolector = rec.id_recolector
    WHERE v.fecha_visita BETWEEN %s AND %s
"""

params = [fecha_inicio, fecha_fin]

if barrio_seleccionado != "Todos":
    query += " AND b.nombre_barrio = %s"
    params.append(barrio_seleccionado)

if recolector_seleccionado != "Todos":
    query += " AND rec.nombre_completo = %s"
    params.append(recolector_seleccionado)

query += " ORDER BY v.fecha_visita DESC"

# Obtener datos filtrados
datos_filtrados = get_data(query, params)

if not datos_filtrados.empty:
    st.dataframe(
        datos_filtrados,
        use_container_width=True,
        height=300
    )
    
    # Exportar a CSV
    csv = datos_filtrados.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name=f"ecoruta_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.info("No hay datos con los filtros seleccionados.")

# ================================================
# 4. RESUMEN POR TABLAS
# ================================================
st.markdown("---")
st.header("🏗️ Estructura de la Base de Datos")

tab1, tab2, tab3, tab4 = st.tabs(["🏘️ Barrios", "👷 Recolectores", "🛣️ Rutas", "📝 Visitas"])

with tab1:
    barrios = get_data("SELECT * FROM barrio ORDER BY nombre_barrio")
    st.dataframe(barrios, use_container_width=True)

with tab2:
    recolectores = get_data("SELECT * FROM recolector ORDER BY nombre_completo")
    st.dataframe(recolectores, use_container_width=True)

with tab3:
    rutas = get_data("""
        SELECT r.*, b.nombre_barrio 
        FROM ruta r 
        JOIN barrio b ON r.barrio_id_barrio = b.id_barrio
        ORDER BY r.nombre_ruta
    """)
    st.dataframe(rutas, use_container_width=True)

with tab4:
    visitas = get_data("SELECT * FROM visita ORDER BY fecha_visita DESC LIMIT 30")
    st.dataframe(visitas, use_container_width=True)

# ================================================
# PIE DE PÁGINA
# ================================================
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray; padding: 20px'>
    <p>🌿 <b>ECORUTA Dashboard</b> | Sistema de Gestión de Reciclaje</p>
    <p>📅 Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    <p>📊 Base de datos: ecoruta_db (4 tablas)</p>
</div>
""", unsafe_allow_html=True)
# ============================================
# ECORUTA DASHBOARD - EXAMEN FINAL BASES DE DATOS
# ============================================
import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ============================================
st.set_page_config(
    page_title="🌿 ECORUTA Dashboard",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    /* Títulos principales */
    .main-title {
        color: #2E7D32;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .sub-title {
        color: #4CAF50;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    
    /* Tarjetas de métricas */
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #4CAF50;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Sidebar */
    .sidebar-title {
        color: #2E7D32;
        font-size: 1.5rem;
        font-weight: bold;
    }
    
    /* Botones */
    .stButton>button {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(76, 175, 80, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# 2. CONEXIÓN A BASE DE DATOS
# ============================================
def conectar_db():
    """Conecta a la base de datos MySQL"""
    try:
        conexion = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='ecoruta_db',
            port=3306,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conexion
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

def ejecutar_consulta(query, params=None):
    """Ejecuta una consulta SQL y retorna DataFrame"""
    conn = None
    try:
        conn = conectar_db()
        if conn:
            df = pd.read_sql(query, conn, params=params)
            conn.close()
            return df
        return pd.DataFrame()
    except Exception as e:
        # st.error(f"❌ Error en consulta: {e}") # Descomentar para debug
        if conn:
            conn.close()
        return pd.DataFrame()

# ============================================
# 3. ENCABEZADO PRINCIPAL
# ============================================
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/3095/3095113.png", width=100)
with col2:
    st.markdown('<p class="main-title">🌿 ECORUTA Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Sistema Municipal de Gestión de Rutas de Reciclaje</p>', unsafe_allow_html=True)
with col3:
    st.markdown(f"**📅 {datetime.now().strftime('%d/%m/%Y')}**")

st.markdown("---")

# ============================================
# 4. BARRA LATERAL CON FILTROS (FECHAS CORREGIDAS)
# ============================================
with st.sidebar:
    st.markdown('<p class="sidebar-title">🌿 ECORUTA</p>', unsafe_allow_html=True)
    
    # Prueba de conexión
    if st.button("🔍 Probar Conexión a BD", use_container_width=True):
        try:
            conn = conectar_db()
            if conn:
                st.success("✅ Conexión exitosa!")
                conn.close()
            else:
                st.error("❌ Error en conexión")
        except:
            st.error("❌ No se pudo conectar")
    
    st.markdown("---")
    
    # FILTROS
    st.markdown("### 🔍 Filtros")
    
    # Fechas
    fecha_min = ejecutar_consulta("SELECT MIN(fecha_visita) as min_fecha FROM visita")
    fecha_max = ejecutar_consulta("SELECT MAX(fecha_visita) as max_fecha FROM visita")
    
    if not fecha_min.empty and not fecha_max.empty:
        # CORRECCIÓN: Acceder al valor por nombre de columna para evitar DateParseError
        min_date = pd.to_datetime(fecha_min['min_fecha'].iloc[0])
        max_date = pd.to_datetime(fecha_max['max_fecha'].iloc[0])
    else:
        min_date = datetime.now() - timedelta(days=60)
        max_date = datetime.now()
    
    col_fecha1, col_fecha2 = st.columns(2)
    with col_fecha1:
        fecha_inicio = st.date_input("Inicio", value=min_date, min_value=min_date, max_value=max_date)
    with col_fecha2:
        fecha_fin = st.date_input("Fin", value=max_date, min_value=min_date, max_value=max_date)
    
    # Barrios
    barrios_data = ejecutar_consulta("SELECT DISTINCT nombre_barrio FROM barrio ORDER BY nombre_barrio")
    if not barrios_data.empty:
        barrios_lista = ["Todos"] + barrios_data['nombre_barrio'].tolist()
        barrio_filtro = st.selectbox("🏘️ Barrio", barrios_lista)
    else:
        barrio_filtro = "Todos"
    
    # Recolectores
    recolectores_data = ejecutar_consulta("SELECT DISTINCT nombre_completo FROM recolector ORDER BY nombre_completo")
    if not recolectores_data.empty:
        recolectores_lista = ["Todos"] + recolectores_data['nombre_completo'].tolist()
        recolector_filtro = st.selectbox("👷 Recolector", recolectores_lista)
    else:
        recolector_filtro = "Todos"
    
    st.markdown("---")
    
    # Estadísticas rápidas (Generales, sin filtro)
    st.markdown("### 📊 Resumen General")
    total_kg = ejecutar_consulta("SELECT COALESCE(SUM(cantidad_kg), 0) as total FROM visita")
    total_visitas = ejecutar_consulta("SELECT COUNT(*) as total FROM visita")
    
    kg_valor = total_kg.iloc[0, 0] if not total_kg.empty else 0
    visitas_valor = total_visitas.iloc[0, 0] if not total_visitas.empty else 0
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("KG Total", f"{kg_valor:,.0f}")
    with col_stat2:
        st.metric("Visitas", visitas_valor)

# ============================================
# 5. CARGA DE DATOS CENTRAL (DINÁMICA Y FILTRADA)
# ============================================

@st.cache_data(ttl=600)
def obtener_datos_filtrados(f_inicio, f_fin, b_filtro, r_filtro):
    """Obtiene datos combinados aplicando todos los filtros dinámicamente en una consulta."""
    
    query = """
    SELECT 
        v.fecha_visita,
        v.cantidad_kg,
        v.completada,
        r.nombre_ruta,
        r.tipo_material,
        b.nombre_barrio,
        rec.nombre_completo as nombre_recolector
    FROM visita v
    JOIN ruta r ON v.ruta_id_ruta = r.id_ruta
    JOIN barrio b ON r.barrio_id_barrio = b.id_barrio
    JOIN recolector rec ON v.recolector_id_recolector = rec.id_recolector
    WHERE v.fecha_visita BETWEEN %s AND %s
    """
    params = [f_inicio, f_fin]
    
    if b_filtro != "Todos":
        query += " AND b.nombre_barrio = %s"
        params.append(b_filtro)
        
    if r_filtro != "Todos":
        query += " AND rec.nombre_completo = %s"
        params.append(r_filtro)
        
    query += " ORDER BY v.fecha_visita DESC"
    
    df_filtrado = ejecutar_consulta(query, params)
    
    if not df_filtrado.empty:
        df_filtrado['fecha_visita'] = pd.to_datetime(df_filtrado['fecha_visita'])
        df_filtrado['cantidad_kg'] = pd.to_numeric(df_filtrado['cantidad_kg'])
    return df_filtrado

# Obtener datos filtrados
df_filtrado = obtener_datos_filtrados(fecha_inicio, fecha_fin, barrio_filtro, recolector_filtro)

if df_filtrado.empty:
    st.warning("⚠️ No se encontraron datos con los filtros seleccionados.")
    st.info("💡 Intenta ampliar el rango de fechas o cambiar los filtros.")
    st.stop()


# ============================================
# 6. MÉTRICAS PRINCIPALES (KPIs Dinámicos)
# ============================================
st.markdown("### 🎯 Métricas Clave del Sistema")

# Cálculo de KPIs directamente desde el DataFrame filtrado (Totalmente reactivos)
total_kg_filtrado = df_filtrado['cantidad_kg'].sum()
total_visitas_filtradas = len(df_filtrado)

# KPI 2: Ruta con mayor número de visitas
ruta_mayor_visitas = df_filtrado['nombre_ruta'].value_counts()
kpi_ruta_nombre = ruta_mayor_visitas.idxmax() if not ruta_mayor_visitas.empty else "N/A"
kpi_ruta_conteo = ruta_mayor_visitas.max() if not ruta_mayor_visitas.empty else 0

# KPI 3: Recolector más activo
recolector_activo = df_filtrado['nombre_recolector'].value_counts()
kpi_recolector_nombre = recolector_activo.idxmax() if not recolector_activo.empty else "N/A"
kpi_recolector_conteo = recolector_activo.max() if not recolector_activo.empty else 0

# KPI adicional: Eficiencia
total_completadas_filtradas = df_filtrado[df_filtrado['completada'] == 'Si'].shape[0]
eficiencia_filtrada = (total_completadas_filtradas / total_visitas_filtradas) * 100 if total_visitas_filtradas > 0 else 0

# KPIs Estáticos (General DB info)
kpi_data = ejecutar_consulta("""
    SELECT 
        (SELECT COUNT(*) FROM barrio) as total_barrios,
        (SELECT COUNT(*) FROM recolector) as total_recolectores,
        (SELECT COUNT(*) FROM ruta) as total_rutas
""")

col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)

with col_k1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("📦 KG Recolectados", f"{total_kg_filtrado:,.0f} kg")
    st.markdown('</div>', unsafe_allow_html=True)

with col_k2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("📈 Eficiencia", f"{eficiencia_filtrada:.1f}%")
    st.markdown('</div>', unsafe_allow_html=True)

with col_k3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("🛣️ Ruta Líder", kpi_ruta_nombre, delta=f"{kpi_ruta_conteo} Visitas")
    st.markdown('</div>', unsafe_allow_html=True)

with col_k4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("👷 Recolector Top", kpi_recolector_nombre, delta=f"{kpi_recolector_conteo} Visitas")
    st.markdown('</div>', unsafe_allow_html=True)

with col_k5:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("🏘️ Barrios (Total)", f"{kpi_data.iloc[0, 0]}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ============================================
# 7. GRÁFICOS (3 REQUERIDOS) - Usando df_filtrado (Dinámicos)
# ============================================
st.markdown("### 📊 Visualizaciones Analíticas")

# GRÁFICO 1: KG POR BARRIO (BARRAS)
st.markdown("##### 1. 📦 KG Recolectados por Barrio")
kg_barrio = df_filtrado.groupby('nombre_barrio')['cantidad_kg'].sum().reset_index()

fig1 = px.bar(
    kg_barrio.sort_values(by='cantidad_kg', ascending=False),
    x='nombre_barrio',
    y='cantidad_kg',
    color='cantidad_kg',
    color_continuous_scale='Viridis',
    text='cantidad_kg',
    height=450
)
fig1.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    xaxis_title="",
    yaxis_title="Kilogramos (KG)",
    showlegend=False
)
fig1.update_traces(
    texttemplate='%{text:,.0f} kg',
    textposition='outside',
    marker_line_color='black',
    marker_line_width=1
)
st.plotly_chart(fig1, use_container_width=True)

# GRÁFICOS 2 Y 3 EN COLUMNAS
col_g1, col_g2 = st.columns(2)

# GRÁFICO 2: KG POR RECOLECTOR (PIE)
with col_g1:
    st.markdown("##### 2. 👷 Distribución por Recolector")
    kg_recolector = df_filtrado.groupby('nombre_recolector').agg(
        KG_Total=('cantidad_kg', 'sum'),
        Visitas=('fecha_visita', 'count')
    ).reset_index().sort_values('KG_Total', ascending=False)
    
    fig2 = px.pie(
        kg_recolector,
        values='KG_Total',
        names='nombre_recolector',
        hole=0.4,
        height=400
    )
    fig2.update_traces(
        textposition='inside',
        textinfo='percent+label',
        pull=[0.1] + [0]*(len(kg_recolector)-1)
    )
    fig2.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Tabla de apoyo
    st.dataframe(
        kg_recolector[['nombre_recolector', 'KG_Total', 'Visitas']]
        .rename(columns={'nombre_recolector': 'Recolector', 'KG_Total': 'KG', 'Visitas': 'N° Visitas'}),
        height=150,
        use_container_width=True
    )

# GRÁFICO 3: KG POR FECHA (LÍNEA)
with col_g2:
    st.markdown("##### 3. 📈 Evolución Temporal")
    
    # Agrupar por fecha
    kg_fecha = df_filtrado.groupby(df_filtrado['fecha_visita'].dt.date).agg(
        KG_Diario=('cantidad_kg', 'sum'),
        Visitas_Diarias=('nombre_ruta', 'count')
    ).reset_index().rename(columns={'fecha_visita': 'Fecha'})
    
    fig3 = go.Figure()
    
    # Línea principal (KG)
    fig3.add_trace(go.Scatter(
        x=kg_fecha['Fecha'],
        y=kg_fecha['KG_Diario'],
        mode='lines+markers',
        name='KG Recolectados',
        line=dict(color='#4CAF50', width=3),
        marker=dict(size=8, color='#2E7D32')
    ))
    
    # Barras (Visitas)
    fig3.add_trace(go.Bar(
        x=kg_fecha['Fecha'],
        y=kg_fecha['Visitas_Diarias'],
        name='Visitas',
        yaxis='y2',
        marker_color='rgba(76, 175, 80, 0.4)'
    ))
    
    fig3.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Fecha",
        yaxis_title="Kilogramos (KG)",
        yaxis2=dict(
            title="Número de Visitas",
            overlaying='y',
            side='right'
        ),
        height=400,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ============================================
# 8. TABLA DE DATOS FILTRADOS
# ============================================
st.markdown("### 📋 Datos Detallados de Visitas (Aplicando Filtros)")

# Cálculos de estadísticas rápidas usando el df_filtrado
total_filtro = len(df_filtrado)
kg_total_filtro = df_filtrado['cantidad_kg'].sum()
completadas_filtro = df_filtrado[df_filtrado['completada'] == 'Si'].shape[0]
porcentaje_filtro = (completadas_filtro / total_filtro * 100) if total_filtro > 0 else 0

col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.info(f"**Registros:** {total_filtro}")
with col_info2:
    st.info(f"**KG Total:** {kg_total_filtro:,.1f}")
with col_info3:
    st.info(f"**Completadas:** {porcentaje_filtro:.1f}%")

# Reordenar y renombrar columnas para la visualización final en la tabla
tabla_final = df_filtrado.rename(columns={
    'fecha_visita': 'Fecha', 
    'cantidad_kg': 'KG', 
    'completada': 'Completada',
    'nombre_ruta': 'Ruta',
    'tipo_material': 'Material',
    'nombre_barrio': 'Barrio',
    'nombre_recolector': 'Recolector'
})[['Fecha', 'KG', 'Completada', 'Ruta', 'Material', 'Barrio', 'Recolector']]

# Mostrar tabla
st.dataframe(
    tabla_final,
    use_container_width=True,
    height=350
)

# Botones de exportación
col_btn1, col_btn2, col_btn3 = st.columns(3)

with col_btn1:
    # Este botón de descarga funciona correctamente
    csv = tabla_final.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name=f"ecoruta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col_btn2:
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.rerun()

with col_btn3:
    # Este botón de "Ver Todos" está mejor como un botón de rerun para refrescar el filtro
    if st.button("📊 Reiniciar Filtros", use_container_width=True):
        st.rerun()


# ============================================
# 9. RESUMEN DE TABLAS
# ============================================
st.markdown("---")
st.markdown("### 🏗️ Estructura de la Base de Datos")

# Pestañas para cada tabla
tab1, tab2, tab3, tab4 = st.tabs(["🏘️ Barrios", "👷 Recolectores", "🛣️ Rutas", "📝 Visitas"])

with tab1:
    barrios_tabla = ejecutar_consulta("SELECT * FROM barrio ORDER BY nombre_barrio")
    if not barrios_tabla.empty:
        st.dataframe(barrios_tabla, use_container_width=True)
    else:
        st.info("No hay datos de barrios")

with tab2:
    recolectores_tabla = ejecutar_consulta("SELECT * FROM recolector ORDER BY nombre_completo")
    if not recolectores_tabla.empty:
        st.dataframe(recolectores_tabla, use_container_width=True)
    else:
        st.info("No hay datos de recolectores")

with tab3:
    rutas_tabla = ejecutar_consulta("""
        SELECT 
            r.id_ruta, 
            r.nombre_ruta, 
            r.tipo_material, 
            r.frecuencia,
            b.nombre_barrio as Barrio
        FROM ruta r
        JOIN barrio b ON r.barrio_id_barrio = b.id_barrio
        ORDER BY r.nombre_ruta
    """)
    if not rutas_tabla.empty:
        st.dataframe(rutas_tabla, use_container_width=True)
    else:
        st.info("No hay datos de rutas")

with tab4:
    visitas_tabla = ejecutar_consulta("""
        SELECT * FROM visita 
        ORDER BY fecha_visita DESC 
        LIMIT 50
    """)
    if not visitas_tabla.empty:
        st.dataframe(visitas_tabla, use_container_width=True)
    else:
        st.info("No hay datos de visitas")

# ============================================
# 10. PIE DE PÁGINA
# ============================================
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; padding: 20px; background-color: #f9f9f9; border-radius: 10px;">
    <p style="font-size: 16px; font-weight: bold; color: #2E7D32;">🌿 ECORUTA Dashboard - Examen Final Bases de Datos</p>
    <p style="font-size: 14px;">Sistema Municipal de Gestión de Rutas de Reciclaje</p>
    <p style="font-size: 12px;">📅 Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}</p>
    <p style="font-size: 12px;">📊 Base de datos: ecoruta_db | Tablas: barrio, recolector, ruta, visita</p>
</div>
""", unsafe_allow_html=True)

with st.expander("📋 Información del Sistema"):
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown("**📁 Tablas en la base de datos:**")
        tablas = ejecutar_consulta("SHOW TABLES")
        if not tablas.empty:
            for tabla in tablas.iloc[:, 0]:
                st.write(f"• {tabla}")
    
    with col_info2:
        st.markdown("**🔧 Dependencias:**")
        st.write("• Python 3.8+")
        st.write("• Streamlit")
        st.write("• PyMySQL")
        st.write("• Plotly")
        st.write("• Pandas")
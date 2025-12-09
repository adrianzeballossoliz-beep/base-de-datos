import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ================================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ================================================
st.set_page_config(
    page_title="🌿 ECORUTA Dashboard",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================
# 2. CONEXIÓN A LA BASE DE DATOS
# ================================================
@st.cache_resource
def crear_conexion():
    """Crea una conexión a la base de datos MySQL"""
    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',           
            database='ecoruta_db', 
            port=3306              
        )
        return conexion
    except Error as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

# ================================================
# 3. FUNCIONES DE CONSULTA
# ================================================
def ejecutar_consulta(query, params=None):
    """Ejecuta una consulta SQL y devuelve resultados"""
    conexion = crear_conexion()
    if conexion:
        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if query.strip().lower().startswith('select'):
                resultados = cursor.fetchall()
            else:
                conexion.commit()
                resultados = None
            
            cursor.close()
            return resultados
        except Error as e:
            st.error(f"Error en la consulta: {e}")
            return None
        finally:
            if conexion and conexion.is_connected():
                conexion.close()

def obtener_dataframe(query, params=None):
    """Ejecuta consulta y devuelve DataFrame de pandas"""
    resultados = ejecutar_consulta(query, params)
    if resultados:
        return pd.DataFrame(resultados)
    return pd.DataFrame()

# ================================================
# 4. INTERFAZ PRINCIPAL
# ================================================
# Logo y título
col1, col2 = st.columns([1, 3])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/3095/3095113.png", width=100)
with col2:
    st.title("♻️ ECORUTA Dashboard")
    st.subheader("Sistema de Gestión de Rutas de Reciclaje")

st.markdown("---")

# ================================================
# 5. BARRA LATERAL - CONFIGURACIÓN
# ================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Prueba de conexión
    if st.button("🔌 Probar Conexión MySQL"):
        conexion = crear_conexion()
        if conexion:
            st.success("✅ Conexión exitosa!")
            conexion.close()
        else:
            st.error("❌ Error en la conexión")
    
    st.markdown("---")
    
    # Filtros
    st.header("📊 Filtros")
    meses = ['Enero 2025', 'Febrero 2025', 'Marzo 2025']
    mes_seleccionado = st.selectbox("Seleccionar Mes", meses)
    
    materiales = ['Todos', 'plástico', 'papel', 'vidrio', 'mixto']
    material_seleccionado = st.selectbox("Tipo de Material", materiales)
    
    st.markdown("---")
    
    # Estadísticas rápidas
    st.header("📈 Stats Rápidas")
    total_visitas = ejecutar_consulta("SELECT COUNT(*) as total FROM visita")
    total_kilos = ejecutar_consulta("SELECT SUM(cantidad_kg) as total FROM visita")
    
    if total_visitas and total_kilos:
        st.metric("Total Visitas", total_visitas[0]['total'])
        st.metric("Total Kilos", f"{total_kilos[0]['total']:,.2f} kg")

# ================================================
# 6. SECCIÓN PRINCIPAL - MÉTRICAS
# ================================================
st.header("📊 Métricas Clave")

# Crear 4 columnas para métricas
col1, col2, col3, col4 = st.columns(4)

with col1:
    # Total de barrios
    df_barrios = obtener_dataframe("SELECT COUNT(*) as total FROM barrio")
    st.metric("🏘️ Barrios", df_barrios['total'][0])

with col2:
    # Total de recolectores
    df_recolectores = obtener_dataframe("SELECT COUNT(*) as total FROM recolector")
    st.metric("👷 Recolectores", df_recolectores['total'][0])

with col3:
    # Total de rutas
    df_rutas = obtener_dataframe("SELECT COUNT(*) as total FROM ruta")
    st.metric("🛣️ Rutas Activas", df_rutas['total'][0])

with col4:
    # Eficiencia promedio
    df_eficiencia = obtener_dataframe(
        "SELECT AVG(CASE WHEN completada = 'Si' THEN 1 ELSE 0 END) * 100 as eficiencia FROM visita"
    )
    st.metric("📈 Eficiencia", f"{df_eficiencia['eficiencia'][0]:.1f}%")

st.markdown("---")

# ================================================
# 7. GRÁFICOS Y VISUALIZACIONES
# ================================================
st.header("📈 Visualizaciones")

# Crear pestañas para diferentes gráficos
tab1, tab2, tab3, tab4 = st.tabs(["📊 Kilos por Ruta", "👥 Recolectores", "🗺️ Distribución", "📅 Evolución Mensual"])

with tab1:
    # Gráfico 1: Kilos recolectados por ruta
    st.subheader("Kilos Recolectados por Ruta")
    query_rutas = """
    SELECT r.nombre_ruta, r.tipo_material, SUM(v.cantidad_kg) as total_kg
    FROM visita v
    JOIN ruta r ON v.ruta_id_ruta = r.id_ruta
    GROUP BY r.nombre_ruta, r.tipo_material
    ORDER BY total_kg DESC
    LIMIT 10
    """
    df_rutas_kg = obtener_dataframe(query_rutas)
    
    if not df_rutas_kg.empty:
        fig = px.bar(df_rutas_kg, x='nombre_ruta', y='total_kg', 
                    color='tipo_material', 
                    title="Top 10 Rutas por Kilos Recolectados",
                    labels={'nombre_ruta': 'Ruta', 'total_kg': 'Kilos Totales'},
                    height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar tabla de datos
        st.dataframe(df_rutas_kg, use_container_width=True)

with tab2:
    # Gráfico 2: Desempeño de recolectores
    st.subheader("Desempeño de Recolectores")
    query_recolectores = """
    SELECT rec.nombre_completo, rec.turno, 
           COUNT(v.id_visita) as total_visitas,
           SUM(v.cantidad_kg) as total_kg,
           AVG(CASE WHEN v.completada = 'Si' THEN 1 ELSE 0 END) * 100 as eficiencia
    FROM visita v
    JOIN recolector rec ON v.recolector_id_recolector = rec.id_recolector
    GROUP BY rec.nombre_completo, rec.turno
    ORDER BY total_kg DESC
    """
    df_recolectores_perf = obtener_dataframe(query_recolectores)
    
    if not df_recolectores_perf.empty:
        # Gráfico de barras
        fig = px.bar(df_recolectores_perf, x='nombre_completo', y='total_kg',
                    color='turno', title="Kilos Recolectados por Empleado",
                    height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla detallada
        st.dataframe(df_recolectores_perf, use_container_width=True)

with tab3:
    # Gráfico 3: Distribución por distrito
    st.subheader("Distribución por Distrito")
    query_distritos = """
    SELECT b.distrito, COUNT(r.id_ruta) as total_rutas,
           SUM(v.cantidad_kg) as total_kg,
           COUNT(DISTINCT b.id_barrio) as barrios
    FROM barrio b
    JOIN ruta r ON b.id_barrio = r.barrio_id_barrio
    JOIN visita v ON r.id_ruta = v.ruta_id_ruta
    GROUP BY b.distrito
    """
    df_distritos = obtener_dataframe(query_distritos)
    
    if not df_distritos.empty:
        fig = px.pie(df_distritos, values='total_kg', names='distrito',
                    title="Distribución de Kilos por Distrito",
                    height=400)
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    # Gráfico 4: Evolución mensual
    st.subheader("Evolución Mensual de Recolección")
    query_mensual = """
    SELECT DATE_FORMAT(fecha_visita, '%Y-%m') as mes,
           SUM(cantidad_kg) as total_kg,
           COUNT(*) as total_visitas,
           AVG(CASE WHEN completada = 'Si' THEN 1 ELSE 0 END) * 100 as eficiencia
    FROM visita
    GROUP BY DATE_FORMAT(fecha_visita, '%Y-%m')
    ORDER BY mes
    """
    df_mensual = obtener_dataframe(query_mensual)
    
    if not df_mensual.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_mensual['mes'], y=df_mensual['total_kg'],
                                mode='lines+markers',
                                name='Kilos Recolectados',
                                line=dict(color='green', width=3)))
        
        fig.update_layout(title='Evolución Mensual de Kilos Recolectados',
                         xaxis_title='Mes',
                         yaxis_title='Kilos Totales',
                         height=400)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ================================================
# 8. TABLA DE VISITAS RECIENTES
# ================================================
st.header("📋 Visitas Recientes")

query_visitas = """
SELECT v.id_visita, v.fecha_visita, v.cantidad_kg, v.completada,
       r.nombre_ruta, r.tipo_material,
       b.nombre_barrio,
       rec.nombre_completo as recolector
FROM visita v
JOIN ruta r ON v.ruta_id_ruta = r.id_ruta
JOIN barrio b ON r.barrio_id_barrio = b.id_barrio
JOIN recolector rec ON v.recolector_id_recolector = rec.id_recolector
ORDER BY v.fecha_visita DESC
LIMIT 20
"""

df_visitas = obtener_dataframe(query_visitas)

if not df_visitas.empty:
    # Formatear la columna de completada con emojis
    df_visitas['Estado'] = df_visitas['completada'].apply(lambda x: '✅ Completada' if x == 'Si' else '❌ Pendiente')
    
    # Mostrar tabla con columnas seleccionadas
    columnas_mostrar = ['fecha_visita', 'nombre_ruta', 'tipo_material', 
                       'nombre_barrio', 'recolector', 'cantidad_kg', 'Estado']
    
    st.dataframe(df_visitas[columnas_mostrar], use_container_width=True)
else:
    st.warning("No hay datos de visitas disponibles")

# ================================================
# 9. SECCIÓN DE CONSULTAS PERSONALIZADAS
# ================================================
st.header("🔍 Consultas SQL Personalizadas")

with st.expander("Ejecutar Consulta SQL", expanded=False):
    consulta_sql = st.text_area("Escribe tu consulta SQL:", 
                               "SELECT * FROM visita LIMIT 10;")
    
    if st.button("Ejecutar Consulta", type="primary"):
        if consulta_sql:
            resultados = ejecutar_consulta(consulta_sql)
            if resultados is not None:
                if resultados:
                    df_resultados = pd.DataFrame(resultados)
                    st.success(f"✅ Consulta ejecutada. {len(resultados)} registros encontrados.")
                    st.dataframe(df_resultados, use_container_width=True)
                else:
                    st.info("ℹ️ La consulta se ejecutó correctamente pero no devolvió resultados.")

# ================================================
# 10. PIE DE PÁGINA
# ================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>🌿 <b>ECORUTA Dashboard</b> | Sistema de Gestión de Reciclaje</p>
    <p>📅 Última actualización: {}</p>
</div>
""".format(datetime.now().strftime("%d/%m/%Y %H:%M")), unsafe_allow_html=True)

# ================================================
# 11. EJECUCIÓN
# ================================================
if __name__ == "__main__":
    # Verificar conexión al inicio
    conexion = crear_conexion()
    if conexion:
        st.sidebar.success("✅ Conectado a MySQL: ecoruta_db")
        conexion.close()
    else:
        st.sidebar.error("⚠️ No se pudo conectar a la base de dato")
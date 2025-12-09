import streamlit as st
import pandas as pd
import pymysql
from pymysql import Error
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
    except Error as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

# ================================================
# 3. FUNCIONES DE CONSULTA CORREGIDAS
# ================================================
def ejecutar_consulta(query, params=None):
    """Ejecuta una consulta SQL y devuelve resultados"""
    conexion = None
    try:
        conexion = crear_conexion()
        if conexion is None:
            return None
        
        with conexion.cursor() as cursor:
            cursor.execute(query, params or ())
            
            if query.strip().lower().startswith(('select', 'show')):
                resultados = cursor.fetchall()
            else:
                conexion.commit()
                resultados = cursor.rowcount
        
        return resultados
    except Error as e:
        st.error(f"Error en la consulta: {e}")
        return None
    except Exception as e:
        st.error(f"Error inesperado: {e}")
        return None
    finally:
        if conexion and conexion.open:
            try:
                conexion.close()
            except:
                pass

def obtener_dataframe(query, params=None):
    """Ejecuta consulta y devuelve DataFrame"""
    resultados = ejecutar_consulta(query, params)
    if resultados and isinstance(resultados, list):
        return pd.DataFrame(resultados)
    return pd.DataFrame()

def obtener_valor_simple(query, default=0):
    """Obtiene un valor simple de una consulta"""
    try:
        resultados = ejecutar_consulta(query)
        if resultados and isinstance(resultados, list) and len(resultados) > 0:
            valor = list(resultados[0].values())[0]
            return valor if valor is not None else default
        return default
    except:
        return default

# ================================================
# 4. INTERFAZ PRINCIPAL
# ================================================
col1, col2 = st.columns([1, 3])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/3095/3095113.png", width=100)
with col2:
    st.title("♻️ ECORUTA Dashboard")
    st.subheader("Sistema de Gestión de Rutas de Reciclaje")

st.markdown("---")

# ================================================
# 5. BARRA LATERAL SIMPLIFICADA
# ================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Prueba de conexión simplificada
    if st.button("🔌 Probar Conexión"):
        try:
            resultados = ejecutar_consulta("SELECT 'OK' as estado")
            if resultados:
                st.success("✅ Conexión exitosa!")
            else:
                st.error("❌ Error en la conexión")
        except:
            st.error("❌ No se pudo conectar")
    
    st.markdown("---")
    st.header("📊 Filtros")
    mes_seleccionado = st.selectbox("Mes", ['Enero 2025', 'Febrero 2025', 'Marzo 2025'])
    material_seleccionado = st.selectbox("Material", ['Todos', 'plástico', 'papel', 'vidrio', 'mixto'])
    
    st.markdown("---")
    st.header("📈 Stats Rápidas")
    
    total_visitas = obtener_valor_simple("SELECT COUNT(*) FROM visita", 0)
    total_kilos = obtener_valor_simple("SELECT COALESCE(SUM(cantidad_kg), 0) FROM visita", 0)
    
    st.metric("Visitas", total_visitas)
    st.metric("Kilos", f"{total_kilos:,.0f} kg")

# ================================================
# 6. MÉTRICAS PRINCIPALES (SIN ERROR)
# ================================================
st.header("📊 Métricas Clave")

col1, col2, col3, col4 = st.columns(4)

with col1:
    barrios = obtener_valor_simple("SELECT COUNT(*) FROM barrio", 0)
    st.metric("🏘️ Barrios", barrios)

with col2:
    recolectores = obtener_valor_simple("SELECT COUNT(*) FROM recolector", 0)
    st.metric("👷 Recolectores", recolectores)

with col3:
    rutas = obtener_valor_simple("SELECT COUNT(*) FROM ruta", 0)
    st.metric("🛣️ Rutas", rutas)

with col4:
    eficiencia = obtener_valor_simple(
        "SELECT COALESCE(AVG(CASE WHEN completada = 'Si' THEN 1 ELSE 0 END) * 100, 0) FROM visita",
        0
    )
    st.metric("📈 Eficiencia", f"{eficiencia:.1f}%")

st.markdown("---")

# ================================================
# 7. GRÁFICOS SIMPLIFICADOS
# ================================================
st.header("📈 Visualizaciones")

# Solo mostrar un gráfico básico para probar
df_visitas = obtener_dataframe("""
SELECT DATE(fecha_visita) as fecha, SUM(cantidad_kg) as total_kg
FROM visita 
GROUP BY DATE(fecha_visita) 
ORDER BY fecha 
LIMIT 10
""")

if not df_visitas.empty:
    fig = px.line(df_visitas, x='fecha', y='total_kg', 
                  title="Kilos Recolectados por Día",
                  height=400)
    st.plotly_chart(fig, use_container_width=True)

# ================================================
# 8. TABLA DE VISITAS
# ================================================
st.header("📋 Últimas Visitas")

df_recientes = obtener_dataframe("""
SELECT fecha_visita, cantidad_kg, completada, 
       (SELECT nombre_ruta FROM ruta WHERE id_ruta = visita.ruta_id_ruta) as ruta
FROM visita 
ORDER BY fecha_visita DESC 
LIMIT 10
""")

if not df_recientes.empty:
    st.dataframe(df_recientes, use_container_width=True)

# ================================================
# 9. VERIFICACIÓN INICIAL SIN CERRAR CONEXIÓN
# ================================================
# Esta verificación se hace una sola vez al inicio
if 'app_inicializada' not in st.session_state:
    # Solo mostrar mensaje, no crear y cerrar conexión
    try:
        test = obtener_valor_simple("SELECT 1", 0)
        if test == 1:
            st.sidebar.success("✅ App inicializada")
    except:
        pass
    
    st.session_state.app_inicializada = True

# ================================================
# 10. PIE DE PÁGINA
# ================================================
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: gray;">
    <p>🌿 <b>ECORUTA Dashboard</b> | Sistema de Gestión de Reciclaje</p>
    <p>📅 {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
</div>
""", unsafe_allow_html=True)
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# ============================================
# CONFIGURACIÓN
# ============================================
st.set_page_config(page_title="Hotel Dashboard", layout="wide")

# OPCIÓN QUE MÁS PROBABLEMENTE FUNCIONE
DB_URI = "mysql+pymysql://root:@127.0.0.1:3306/proyecto"

# ============================================
# PRUEBA DE CONEXIÓN SIMPLE
# ============================================
st.title("🏨 Sistema Hotelero - Conexión")

st.write("### Probando conexión a MySQL...")

try:
    # 1. Crear conexión
    engine = create_engine(DB_URI)
    
    # 2. Probar conexión
    with engine.connect() as conn:
        # Consulta SUPER simple
        result = conn.execute(text("SELECT '✅ CONECTADO' as estado"))
        mensaje = result.fetchone()[0]
        st.success(f"**{mensaje}** a la base de datos")
        
        # Mostrar algunas tablas
        tablas = pd.read_sql("SHOW TABLES", conn)
        st.info(f"📊 **{len(tablas)} tablas** en la base de datos")
        
        # Mostrar primeras 5 tablas
        st.write("**Algunas tablas:**")
        st.write(tablas.head(10))
        
except Exception as e:
    st.error(f"❌ **Error de conexión:** {e}")
    st.stop()

# ============================================
# SI LLEGA AQUÍ, LA CONEXIÓN FUNCIONA
# ============================================
st.success("🎉 **¡CONEXIÓN EXITOSA!**")
st.write("---")

# ============================================
# MOSTRAR ALGUNOS DATOS REALES
# ============================================
st.header("📋 Datos de ejemplo")

# Opción 1: Clientes
try:
    clientes = pd.read_sql("SELECT * FROM cliente LIMIT 5", engine)
    st.subheader("👥 Clientes (primeros 5)")
    st.dataframe(clientes)
except:
    st.warning("No se pudo leer la tabla 'cliente'")

# Opción 2: Habitaciones
try:
    habitaciones = pd.read_sql("SELECT * FROM habitacion LIMIT 5", engine)
    st.subheader("🛏️ Habitaciones (primeros 5)")
    st.dataframe(habitaciones)
except:
    st.warning("No se pudo leer la tabla 'habitacion'")

# Opción 3: Reservas
try:
    reservas = pd.read_sql("""
        SELECT r.id_reserva, r.fecha_reserva, r.estado_reserva,
               c.nombre, c.apellido_paterno
        FROM reserva r
        LEFT JOIN cliente c ON r.id_cliente = c.id_cliente
        LIMIT 5
    """, engine)
    st.subheader("📅 Reservas (primeros 5)")
    st.dataframe(reservas)
except Exception as e:
    st.warning(f"No se pudo leer reservas: {str(e)[:100]}")

# ============================================
# INSTRUCCIONES FINALES
# ============================================
st.write("---")
st.success("**Siguiente paso:** Si esto funciona, podemos arreglar tu dashboard completo.")
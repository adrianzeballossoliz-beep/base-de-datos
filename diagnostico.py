import streamlit as st
import socket

st.title("🔍 Diagnóstico de Conexión MySQL")

# Prueba diferentes configuraciones
configuraciones = [
    "mysql+pymysql://root:@localhost:3307/proyecto",
    "mysql+pymysql://root:@127.0.0.1:3307/proyecto",
    "mysql+pymysql://root:@localhost:3306/proyecto",
    "mysql+pymysql://root:@127.0.0.1:3306/proyecto",
    "mysql+pymysql://root:@localhost/proyecto"
]

st.write("### Probando conexiones...")

for config in configuraciones:
    try:
        from sqlalchemy import create_engine
        engine = create_engine(config)
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        st.success(f"✅ CONEXIÓN EXITOSA: {config}")
        break
    except Exception as e:
        st.error(f"❌ FALLÓ: {config}")
        st.code(f"Error: {str(e)[:100]}...")
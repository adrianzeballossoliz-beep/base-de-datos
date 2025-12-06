import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard Hotelero",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CADENA DE CONEXIÓN CORRECTA
DEFAULT_DB_URI = "mysql+pymysql://root:@127.0.0.1:3306/proyecto"

# ============================================================
# FUNCIÓN DE CONEXIÓN
# ============================================================
def get_engine(db_uri):
    """Crea un engine SQLAlchemy."""
    try:
        engine = create_engine(db_uri)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        st.success("✅ Conectado a la base de datos")
        return engine
    except Exception as e:
        st.error(f"❌ Error conectando a la base de datos:\n{e}")
        return None

# ============================================================
# CARGA DE DATOS - CONSULTA CORREGIDA
# ============================================================
@st.cache_data(ttl=600)
def load_hotel_data(db_uri):
    """Carga datos desde la base de datos hotelera."""
    engine = create_engine(db_uri)
    
    # CONSULTA PRINCIPAL CORREGIDA (solo columnas que EXISTEN)
    query = """
    SELECT 
        -- Información de reserva
        r.id_reserva,
        r.fecha_reserva,
        r.monto_total,
        r.estado_reserva,
        r.numero_personas,
        r.fecha_entrada,
        r.fecha_salida,
        
        -- Información de cliente
        c.id_cliente,
        c.nombre,
        c.apellido_paterno,
        c.apellido_materno,
        c.ci,
        CONCAT(c.nombre, ' ', c.apellido_paterno, ' ', 
               COALESCE(c.apellido_materno, '')) AS nombre_completo,
        
        -- Información de detalle de reserva
        dr.id_detalle_reserva,
        dr.precio_unitario,
        dr.check_in,
        dr.check_out,
        dr.subtotal AS subtotal_detalle,
        
        -- Información de habitación
        h.id_habitacion,
        h.numero_habitacion,
        h.piso,
        h.estado AS estado_habitacion,
        h.precio_noche AS precio_habitacion,
        
        -- Información de tipo de habitación
        th.id_tipo_habitacion,
        th.nombre_tipo AS tipo_habitacion,
        th.numero_camas,
        th.capacidad_personas,
        th.precio_base,
        
        -- Información de pago
        p.id_pago,
        p.monto AS monto_pago,
        p.estado_pago,
        p.fecha_pago,
        p.codigo_pago
        
    FROM reserva r
    LEFT JOIN cliente c ON r.id_cliente = c.id_cliente
    LEFT JOIN detalle_reserva dr ON r.id_reserva = dr.id_reserva
    LEFT JOIN habitacion h ON dr.id_habitacion = h.id_habitacion
    LEFT JOIN tipo_habitacion th ON h.id_tipo_habitacion = th.id_tipo_habitacion
    LEFT JOIN pago p ON r.id_reserva = p.id_reserva
    ORDER BY r.fecha_reserva DESC
    LIMIT 1000
    """
    
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Error en la consulta: {e}")
        # Mostrar tablas disponibles para diagnóstico
        try:
            tablas = pd.read_sql("SHOW TABLES", engine)
            st.write("Tablas disponibles:", tablas)
        except:
            pass
        return pd.DataFrame()
    
    # CONVERSIÓN DE FECHAS
    date_columns = ['fecha_reserva', 'check_in', 'check_out', 'fecha_pago', 
                   'fecha_entrada', 'fecha_salida']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # CALCULAR DURACIÓN DE ESTADÍA (con fecha_entrada y fecha_salida)
    if 'fecha_entrada' in df.columns and 'fecha_salida' in df.columns:
        df['duracion_estadia'] = (df['fecha_salida'] - df['fecha_entrada']).dt.days
        df['duracion_estadia'] = df['duracion_estadia'].fillna(0).astype(int)
    
    # COLUMNAS DERIVADAS DE FECHA
    if 'fecha_reserva' in df.columns:
        df['anio'] = df['fecha_reserva'].dt.year
        df['mes'] = df['fecha_reserva'].dt.month
        df['dia'] = df['fecha_reserva'].dt.day
        df['mes_anio'] = df['fecha_reserva'].dt.to_period('M').astype(str)
        df['dia_semana'] = df['fecha_reserva'].dt.day_name()
    
    # CALCULAR MONTO NETO (usar monto_total de reserva)
    if 'monto_total' in df.columns:
        df['monto_neto'] = df['monto_total'].fillna(0)
    else:
        df['monto_neto'] = 0
    
    # LIMPIEZA DE VALORES NULOS
    text_columns = ['estado_reserva', 'nombre', 'tipo_habitacion', 
                   'estado_pago', 'estado_habitacion', 'codigo_pago']
    
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].fillna('Sin especificar')
    
    # VALORES NUMÉRICOS
    numeric_columns = ['monto_total', 'monto_neto', 'precio_unitario', 
                      'precio_habitacion', 'numero_personas', 'capacidad_personas']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(float)
    
    return df

# ============================================================
# FUNCIÓN DE FILTRADO
# ============================================================
def filtrar_hotel(df, fechas, estados_reserva, tipos_habitacion, estados_pago):
    """Filtra reservas hoteleras según criterios."""
    
    df_filtrado = df.copy()
    
    # FILTRAR POR FECHAS (usar fecha_reserva)
    if isinstance(fechas, (list, tuple)) and len(fechas) == 2:
        fi, ff = fechas[0], fechas[1]
    else:
        if 'fecha_reserva' in df_filtrado.columns:
            fi = df_filtrado['fecha_reserva'].min().date()
            ff = df_filtrado['fecha_reserva'].max().date()
        else:
            fi = datetime.now().date() - timedelta(days=30)
            ff = datetime.now().date()
    
    if 'fecha_reserva' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['fecha_reserva'].dt.date.between(fi, ff)]
    
    # FILTRAR POR ESTADO DE RESERVA
    if estados_reserva and 'estado_reserva' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['estado_reserva'].isin(estados_reserva)]
    
    # FILTRAR POR TIPO DE HABITACIÓN
    if tipos_habitacion and 'tipo_habitacion' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['tipo_habitacion'].isin(tipos_habitacion)]
    
    # FILTRAR POR ESTADO DE PAGO
    if estados_pago and 'estado_pago' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['estado_pago'].isin(estados_pago)]
    
    return df_filtrado

# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================
st.title("🏨 Dashboard de Gestión Hotelera")

# CONEXIÓN
engine = get_engine(DEFAULT_DB_URI)
if engine is None:
    st.stop()

# CARGA DE DATOS
with st.spinner("🔄 Cargando datos del hotel..."):
    df = load_hotel_data(DEFAULT_DB_URI)

if df.empty:
    st.warning("⚠️ No se encontraron datos en la base de datos.")
    
    # Botón para crear datos de prueba
    if st.button("🔄 Crear datos de prueba"):
        try:
            with engine.connect() as conn:
                # Insertar cliente de prueba
                conn.execute(text("""
                    INSERT INTO cliente (nombre, ci, apellido_paterno, apellido_materno)
                    VALUES ('Juan', '1234567', 'Pérez', 'García')
                    ON DUPLICATE KEY UPDATE nombre=nombre
                """))
                
                # Insertar tipo habitación
                conn.execute(text("""
                    INSERT INTO tipo_habitacion (nombre_tipo, numero_camas, capacidad_personas, precio_base)
                    VALUES ('ESTANDAR', 1, 2, 100.00)
                    ON DUPLICATE KEY UPDATE nombre_tipo=nombre_tipo
                """))
                
                conn.commit()
                st.success("Datos de prueba creados. Recarga la página.")
        except Exception as e:
            st.error(f"Error creando datos: {e}")
    
    st.stop()

# ============================================================
# SIDEBAR - FILTROS
# ============================================================
st.sidebar.header("🔍 Filtros")

# FECHAS
if 'fecha_reserva' in df.columns and not df['fecha_reserva'].isnull().all():
    fecha_min = df['fecha_reserva'].min().date()
    fecha_max = df['fecha_reserva'].max().date()
    fechas = st.sidebar.date_input(
        "📅 Rango de fechas de reserva",
        [fecha_min, fecha_max],
        min_value=fecha_min,
        max_value=fecha_max
    )
else:
    fechas = st.sidebar.date_input(
        "📅 Rango de fechas",
        [datetime.now().date() - timedelta(days=30), datetime.now().date()]
    )

# ESTADOS DE RESERVA
if 'estado_reserva' in df.columns:
    estados_opciones = sorted(df['estado_reserva'].unique().tolist())
    estados_reserva = st.sidebar.multiselect(
        "📋 Estado de reserva",
        estados_opciones,
        default=estados_opciones if len(estados_opciones) <= 3 else []
    )
else:
    estados_reserva = []

# TIPOS DE HABITACIÓN
if 'tipo_habitacion' in df.columns:
    tipos_habitacion = st.sidebar.multiselect(
        "🛏️ Tipo de habitación",
        sorted(df['tipo_habitacion'].unique().tolist())
    )
else:
    tipos_habitacion = []

# ESTADOS DE PAGO
if 'estado_pago' in df.columns:
    estados_pago = st.sidebar.multiselect(
        "💰 Estado de pago",
        sorted(df['estado_pago'].unique().tolist())
    )
else:
    estados_pago = []

# APLICAR FILTROS
df_filtrado = filtrar_hotel(df, fechas, estados_reserva, tipos_habitacion, estados_pago)

if df_filtrado.empty:
    st.warning("⚠️ No hay reservas que coincidan con los filtros seleccionados.")
    st.stop()

# ============================================================
# KPI PRINCIPALES
# ============================================================
st.subheader("📊 Indicadores Clave (KPIs)")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_ventas = df_filtrado['monto_neto'].sum()
    st.metric("💰 Ingresos Totales", f"${total_ventas:,.2f}")

with col2:
    num_reservas = df_filtrado['id_reserva'].nunique()
    st.metric("📋 Reservas Totales", num_reservas)

with col3:
    if num_reservas > 0:
        promedio_reserva = total_ventas / num_reservas
    else:
        promedio_reserva = 0
    st.metric("📈 Reserva Promedio", f"${promedio_reserva:,.2f}")

with col4:
    if 'duracion_estadia' in df_filtrado.columns and len(df_filtrado) > 0:
        estancia_promedio = df_filtrado['duracion_estadia'].mean()
    else:
        estancia_promedio = 0
    st.metric("🏨 Estancia Promedio", f"{estancia_promedio:.1f} noches")

st.divider()

# ============================================================
# DATOS FILTRADOS
# ============================================================
with st.expander("📋 Ver Datos de Reservas", expanded=False):
    columnas_mostrar = []
    for col in ['id_reserva', 'fecha_reserva', 'nombre_completo', 'tipo_habitacion', 
                'fecha_entrada', 'fecha_salida', 'duracion_estadia', 'monto_neto', 
                'estado_reserva', 'estado_pago']:
        if col in df_filtrado.columns:
            columnas_mostrar.append(col)
    
    if columnas_mostrar:
        st.dataframe(df_filtrado[columnas_mostrar], use_container_width=True, height=300)
        
        # Botón descarga
        csv = df_filtrado[columnas_mostrar].to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Descargar CSV",
            csv,
            "reservas_hotel.csv",
            "text/csv"
        )
    else:
        st.warning("No hay columnas disponibles para mostrar")

st.divider()

# ============================================================
# VISUALIZACIONES
# ============================================================
st.subheader("📈 Análisis Visual")

tab1, tab2, tab3, tab4 = st.tabs(["📅 Tiempo", "🛏️ Habitaciones", "👥 Clientes", "💰 Pagos"])

# TAB 1: ANÁLISIS TEMPORAL
with tab1:
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        if 'fecha_reserva' in df_filtrado.columns and 'monto_neto' in df_filtrado.columns:
            st.markdown("### 📈 Ingresos por Fecha")
            ingresos_diarios = df_filtrado.groupby(
                df_filtrado['fecha_reserva'].dt.date
            )['monto_neto'].sum().reset_index()
            
            if not ingresos_diarios.empty:
                fig = px.line(
                    ingresos_diarios, 
                    x='fecha_reserva', 
                    y='monto_neto',
                    title='Evolución de Ingresos',
                    labels={'monto_neto': 'Ingresos ($)', 'fecha_reserva': 'Fecha'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col_t2:
        if 'mes_anio' in df_filtrado.columns and 'monto_neto' in df_filtrado.columns:
            st.markdown("### 📊 Ingresos Mensuales")
            ingresos_mensuales = df_filtrado.groupby('mes_anio')['monto_neto'].sum().reset_index()
            
            if not ingresos_mensuales.empty:
                fig = px.bar(
                    ingresos_mensuales, 
                    x='mes_anio', 
                    y='monto_neto',
                    title='Ingresos por Mes',
                    labels={'monto_neto': 'Ingresos ($)', 'mes_anio': 'Mes'}
                )
                st.plotly_chart(fig, use_container_width=True)

# TAB 2: ANÁLISIS DE HABITACIONES
with tab2:
    col_h1, col_h2 = st.columns(2)
    
    with col_h1:
        if 'tipo_habitacion' in df_filtrado.columns:
            st.markdown("### 🛏️ Reservas por Tipo")
            reservas_por_tipo = df_filtrado['tipo_habitacion'].value_counts().reset_index()
            reservas_por_tipo.columns = ['Tipo', 'Cantidad']
            
            if not reservas_por_tipo.empty:
                fig = px.bar(
                    reservas_por_tipo,
                    x='Tipo',
                    y='Cantidad',
                    title='Reservas por Tipo de Habitación'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col_h2:
        if 'tipo_habitacion' in df_filtrado.columns and 'monto_neto' in df_filtrado.columns:
            st.markdown("### 💰 Ingresos por Tipo")
            ingresos_por_tipo = df_filtrado.groupby('tipo_habitacion')['monto_neto'].sum().reset_index()
            
            if not ingresos_por_tipo.empty:
                fig = px.pie(
                    ingresos_por_tipo,
                    values='monto_neto',
                    names='tipo_habitacion',
                    title='Ingresos por Tipo de Habitación'
                )
                st.plotly_chart(fig, use_container_width=True)

# TAB 3: ANÁLISIS DE CLIENTES
with tab3:
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        if 'nombre_completo' in df_filtrado.columns and 'monto_neto' in df_filtrado.columns:
            st.markdown("### 👑 Clientes Top")
            top_clientes = df_filtrado.groupby('nombre_completo')['monto_neto'].sum().reset_index()
            top_clientes = top_clientes.sort_values('monto_neto', ascending=False).head(10)
            
            if not top_clientes.empty:
                fig = px.bar(
                    top_clientes,
                    x='nombre_completo',
                    y='monto_neto',
                    title='Clientes con Mayor Consumo'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col_c2:
        if 'duracion_estadia' in df_filtrado.columns:
            st.markdown("### 📅 Duración de Estadía")
            fig = px.histogram(
                df_filtrado,
                x='duracion_estadia',
                nbins=10,
                title='Distribución de Noches'
            )
            st.plotly_chart(fig, use_container_width=True)

# TAB 4: ANÁLISIS DE PAGOS
with tab4:
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        if 'estado_pago' in df_filtrado.columns:
            st.markdown("### 💳 Estados de Pago")
            estado_pagos = df_filtrado['estado_pago'].value_counts().reset_index()
            estado_pagos.columns = ['Estado', 'Cantidad']
            
            if not estado_pagos.empty:
                fig = px.pie(
                    estado_pagos,
                    values='Cantidad',
                    names='Estado',
                    title='Distribución por Estado de Pago'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col_p2:
        if 'estado_reserva' in df_filtrado.columns:
            st.markdown("### 📋 Estados de Reserva")
            estado_reservas = df_filtrado['estado_reserva'].value_counts().reset_index()
            estado_reservas.columns = ['Estado', 'Cantidad']
            
            if not estado_reservas.empty:
                fig = px.bar(
                    estado_reservas,
                    x='Estado',
                    y='Cantidad',
                    title='Estados de Reserva'
                )
                st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PIE DE PÁGINA
# ============================================================
st.divider()
st.caption("🏨 Sistema de Gestión Hotelera - Base de Datos I 2024")

# ============================================================
# INFORMACIÓN DE DIAGNÓSTICO
# ============================================================
with st.expander("🔧 Información Técnica", expanded=False):
    st.write("### 📋 Columnas disponibles:")
    st.write(list(df.columns))
    
    st.write("### 📊 Primeras filas:")
    st.dataframe(df.head())
    
    st.write("### 🔗 Conexión:")
    st.code(f"URI: {DEFAULT_DB_URI}")
    st.code(f"Registros: {len(df)} | Filtrados: {len(df_filtrado)}")
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
    page_title="Dashboard Hoteero",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CADENA DE CONEXIÓN CORRECTA PARA TU MYSQL LOCAL
DEFAULT_DB_URI = "mysql+pymysql://root:@localhost:3306/proyecto"

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
# CARGA DE DATOS - ADAPTADA A TABLAS HOTELERAS
# ============================================================
@st.cache_data(ttl=600)
def load_hotel_data(db_uri):
    """Carga datos desde la base de datos hotelera."""
    engine = create_engine(db_uri)
    
    # CONSULTA PRINCIPAL PARA EL HOTEL
    query = """
    SELECT 
        -- Información de reserva
        r.id_reserva,
        r.fecha_reserva,
        r.monto_total,
        r.estado_reserva,
        r.localizacion_reserva,
        r.fecha_vencimiento,
        
        -- Información de cliente
        c.id_cliente,
        c.nombre,
        c.apellido_paterno,
        c.apellido_materno,
        c.ci,
        CONCAT(c.nombre, ' ', c.apellido_paterno, ' ', c.apellido_materno) AS nombre_completo,
        
        -- Información de detalle de reserva
        dr.id_detalle_reserva,
        dr.precio_unitario,
        dr.cantidad_personas,
        dr.check_in,
        dr.check_out,
        
        -- Información de habitación
        h.id_habitacion,
        h.numero_habitacion,
        h.piso,
        h.precio AS precio_habitacion,
        
        -- Información de tipo de habitación
        th.id_tipo_habitacion,
        th.descripcion AS tipo_habitacion,
        th.numero_camas,
        th.capacidad,
        th.tamano_m2,
        
        -- Información de servicios especiales
        COALESCE(se.nombre, 'Sin servicio') AS servicio_especial,
        COALESCE(se.precio, 0) AS precio_servicio,
        
        -- Información de pago
        p.id_pago,
        p.monto AS monto_pago,
        p.estado_pago,
        p.fecha_pago,
        
        -- Tipo de método de pago
        CASE 
            WHEN tar.id_tarjeta IS NOT NULL THEN 'TARJETA'
            WHEN tr.id_transferencia IS NOT NULL THEN 'TRANSFERENCIA'
            WHEN ef.id_efectivo IS NOT NULL THEN 'EFECTIVO'
            WHEN q.id_qr IS NOT NULL THEN 'QR'
            ELSE 'SIN_REGISTRO'
        END AS metodo_pago,
        
        -- Información de promociones
        pr.codigo_promocional,
        pr.porcentaje_descuento
        
    FROM reserva r
    LEFT JOIN cliente c ON r.id_cliente = c.id_cliente
    LEFT JOIN detalle_reserva dr ON r.id_reserva = dr.id_reserva
    LEFT JOIN habitacion h ON dr.id_habitacion = h.id_habitacion
    LEFT JOIN tipo_habitacion th ON h.id_tipo_habitacion = th.id_tipo_habitacion
    LEFT JOIN detalle_reserva_servicios_especiales drse ON dr.id_detalle_reserva = drse.id_detalle_reserva
    LEFT JOIN servicios_especiales se ON drse.id_servicios_especiales = se.id_servicios_especiales
    LEFT JOIN pago p ON r.id_reserva = p.id_reserva
    LEFT JOIN tarjeta tar ON p.id_pago = tar.id_detalle_pago
    LEFT JOIN transferencia tr ON p.id_pago = tr.id_detalle_pago
    LEFT JOIN efectivo ef ON p.id_pago = ef.id_detalle_pago
    LEFT JOIN qr q ON p.id_pago = q.id_detalle_pago
    LEFT JOIN promocion pr ON p.id_pago = pr.id_promocion
    ORDER BY r.fecha_reserva DESC
    LIMIT 1000
    """
    
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Error en la consulta: {e}")
        return pd.DataFrame()
    
    # CONVERSIÓN DE FECHAS
    date_columns = ['fecha_reserva', 'check_in', 'check_out', 'fecha_pago', 'fecha_vencimiento']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # CALCULAR DURACIÓN DE ESTADÍA
    if 'check_in' in df.columns and 'check_out' in df.columns:
        df['duracion_estadia'] = (df['check_out'] - df['check_in']).dt.days
        df['duracion_estadia'] = df['duracion_estadia'].fillna(0).astype(int)
    
    # COLUMNAS DERIVADAS DE FECHA
    if 'fecha_reserva' in df.columns:
        df['anio'] = df['fecha_reserva'].dt.year
        df['mes'] = df['fecha_reserva'].dt.month
        df['dia'] = df['fecha_reserva'].dt.day
        df['mes_anio'] = df['fecha_reserva'].dt.to_period('M').astype(str)
        df['dia_semana'] = df['fecha_reserva'].dt.day_name()
    
    # CALCULAR MONTO NETO (considerando descuentos)
    if 'monto_total' in df.columns and 'porcentaje_descuento' in df.columns:
        df['porcentaje_descuento'] = df['porcentaje_descuento'].fillna(0)
        df['descuento'] = df['monto_total'] * (df['porcentaje_descuento'] / 100)
        df['monto_neto'] = df['monto_total'] - df['descuento']
    elif 'monto_total' in df.columns:
        df['monto_neto'] = df['monto_total']
    else:
        df['monto_neto'] = 0
    
    # AGREGAR PRECIO SERVICIO SI EXISTE
    if 'precio_servicio' in df.columns:
        df['monto_neto'] = df['monto_neto'] + df['precio_servicio'].fillna(0)
    
    # LIMPIEZA DE VALORES NULOS
    text_columns = ['estado_reserva', 'localizacion_reserva', 'nombre', 
                   'tipo_habitacion', 'servicio_especial', 'estado_pago', 
                   'metodo_pago', 'codigo_promocional']
    
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].fillna('Sin especificar')
    
    # VALORES NUMÉRICOS
    numeric_columns = ['monto_total', 'monto_neto', 'precio_unitario', 
                      'precio_habitacion', 'precio_servicio', 'cantidad_personas']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(float)
    
    return df

# ============================================================
# FUNCIÓN DE FILTRADO PARA HOTEL
# ============================================================
def filtrar_hotel(df, fechas, estados_reserva, tipos_habitacion, servicios, metodos_pago):
    """Filtra reservas hoteleras según criterios."""
    
    # Copiar DataFrame
    df_filtrado = df.copy()
    
    # FILTRAR POR FECHAS
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
    
    # FILTRAR POR SERVICIOS ESPECIALES
    if servicios and 'servicio_especial' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['servicio_especial'].isin(servicios)]
    
    # FILTRAR POR MÉTODO DE PAGO
    if metodos_pago and 'metodo_pago' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['metodo_pago'].isin(metodos_pago)]
    
    return df_filtrado

# ============================================================
# INTERFAZ PRINCIPAL - HOTEL
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
    st.info("""
    **Posibles soluciones:**
    1. Asegúrate de haber ejecutado el script SQL para crear las tablas
    2. Verifica que haya datos en las tablas
    3. Revisa la conexión a la base de datos
    """)
    st.stop()

# ============================================================
# SIDEBAR - FILTROS HOTELEROS
# ============================================================
st.sidebar.header("🔍 Filtros Hotelero")

# FECHAS
if 'fecha_reserva' in df.columns:
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
    estados_opciones = df['estado_reserva'].unique().tolist()
    estados_reserva = st.sidebar.multiselect(
        "📋 Estado de reserva",
        estados_opciones,
        default=['confirmada'] if 'confirmada' in estados_opciones else []
    )
else:
    estados_reserva = []

# TIPOS DE HABITACIÓN
if 'tipo_habitacion' in df.columns:
    tipos_habitacion = st.sidebar.multiselect(
        "🛏️ Tipo de habitación",
        df['tipo_habitacion'].unique().tolist()
    )
else:
    tipos_habitacion = []

# SERVICIOS ESPECIALES
if 'servicio_especial' in df.columns:
    servicios_opciones = df['servicio_especial'].unique().tolist()
    servicios = st.sidebar.multiselect(
        "⭐ Servicios especiales",
        servicios_opciones
    )
else:
    servicios = []

# MÉTODOS DE PAGO
if 'metodo_pago' in df.columns:
    metodos_pago = st.sidebar.multiselect(
        "💳 Método de pago",
        df['metodo_pago'].unique().tolist()
    )
else:
    metodos_pago = []

# APLICAR FILTROS
df_filtrado = filtrar_hotel(df, fechas, estados_reserva, tipos_habitacion, servicios, metodos_pago)

if df_filtrado.empty:
    st.warning("⚠️ No hay reservas que coincidan con los filtros seleccionados.")
    st.stop()

# ============================================================
# KPI PRINCIPALES - HOTEL
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
                'check_in', 'check_out', 'duracion_estadia', 'monto_neto', 
                'estado_reserva', 'metodo_pago']:
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
# VISUALIZACIONES - HOTEL
# ============================================================
st.subheader("📈 Análisis Visual")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📅 Tiempo", 
    "🛏️ Habitaciones", 
    "👥 Clientes", 
    "💳 Pagos", 
    "📊 General"
])

# TAB 1: ANÁLISIS TEMPORAL
with tab1:
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        if 'fecha_reserva' in df_filtrado.columns and 'monto_neto' in df_filtrado.columns:
            st.markdown("### 📈 Ingresos Diarios")
            ingresos_diarios = df_filtrado.groupby(
                df_filtrado['fecha_reserva'].dt.date
            )['monto_neto'].sum().reset_index()
            
            fig = px.line(
                ingresos_diarios, 
                x='fecha_reserva', 
                y='monto_neto',
                title='Evolución de Ingresos Diarios',
                labels={'monto_neto': 'Ingresos ($)', 'fecha_reserva': 'Fecha'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col_t2:
        if 'mes_anio' in df_filtrado.columns and 'monto_neto' in df_filtrado.columns:
            st.markdown("### 📊 Ingresos Mensuales")
            ingresos_mensuales = df_filtrado.groupby('mes_anio')['monto_neto'].sum().reset_index()
            
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
            st.markdown("### 🛏️ Reservas por Tipo de Habitación")
            reservas_por_tipo = df_filtrado['tipo_habitacion'].value_counts().reset_index()
            reservas_por_tipo.columns = ['Tipo', 'Cantidad']
            
            fig = px.bar(
                reservas_por_tipo,
                x='Tipo',
                y='Cantidad',
                title='Distribución de Reservas por Tipo de Habitación',
                color='Tipo'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col_h2:
        if 'tipo_habitacion' in df_filtrado.columns and 'monto_neto' in df_filtrado.columns:
            st.markdown("### 💰 Ingresos por Tipo de Habitación")
            ingresos_por_tipo = df_filtrado.groupby('tipo_habitacion')['monto_neto'].sum().reset_index()
            
            fig = px.pie(
                ingresos_por_tipo,
                values='monto_neto',
                names='tipo_habitacion',
                title='Distribución de Ingresos por Tipo de Habitación'
            )
            st.plotly_chart(fig, use_container_width=True)

# TAB 3: ANÁLISIS DE CLIENTES
with tab3:
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        if 'nombre_completo' in df_filtrado.columns and 'monto_neto' in df_filtrado.columns:
            st.markdown("### 👑 Top 10 Clientes por Consumo")
            top_clientes = df_filtrado.groupby('nombre_completo')['monto_neto'].sum().reset_index()
            top_clientes = top_clientes.sort_values('monto_neto', ascending=False).head(10)
            
            fig = px.bar(
                top_clientes,
                x='nombre_completo',
                y='monto_neto',
                title='Clientes con Mayor Consumo',
                labels={'monto_neto': 'Consumo Total ($)', 'nombre_completo': 'Cliente'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col_c2:
        if 'duracion_estadia' in df_filtrado.columns:
            st.markdown("### 📅 Distribución de Duración de Estadía")
            fig = px.histogram(
                df_filtrado,
                x='duracion_estadia',
                nbins=20,
                title='Distribución de Noches por Reserva',
                labels={'duracion_estadia': 'Noches de Estadía'}
            )
            st.plotly_chart(fig, use_container_width=True)

# TAB 4: ANÁLISIS DE PAGOS
with tab4:
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        if 'metodo_pago' in df_filtrado.columns:
            st.markdown("### 💳 Métodos de Pago Más Usados")
            metodos_count = df_filtrado['metodo_pago'].value_counts().reset_index()
            metodos_count.columns = ['Método', 'Cantidad']
            
            fig = px.bar(
                metodos_count,
                x='Método',
                y='Cantidad',
                title='Frecuencia de Métodos de Pago',
                color='Método'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col_p2:
        if 'metodo_pago' in df_filtrado.columns and 'monto_neto' in df_filtrado.columns:
            st.markdown("### 📊 Ingresos por Método de Pago")
            ingresos_metodo = df_filtrado.groupby('metodo_pago')['monto_neto'].sum().reset_index()
            
            fig = px.pie(
                ingresos_metodo,
                values='monto_neto',
                names='metodo_pago',
                title='Distribución de Ingresos por Método de Pago'
            )
            st.plotly_chart(fig, use_container_width=True)

# TAB 5: ANÁLISIS GENERAL
with tab5:
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        if 'estado_reserva' in df_filtrado.columns:
            st.markdown("### 📋 Estado de las Reservas")
            estado_reservas = df_filtrado['estado_reserva'].value_counts().reset_index()
            estado_reservas.columns = ['Estado', 'Cantidad']
            
            fig = px.pie(
                estado_reservas,
                values='Cantidad',
                names='Estado',
                title='Distribución por Estado de Reserva'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        if 'servicio_especial' in df_filtrado.columns:
            st.markdown("### ⭐ Servicios Especiales Más Solicitados")
            servicios_count = df_filtrado['servicio_especial'].value_counts().reset_index()
            servicios_count.columns = ['Servicio', 'Cantidad']
            servicios_count = servicios_count[servicios_count['Servicio'] != 'Sin servicio'].head(10)
            
            if not servicios_count.empty:
                fig = px.bar(
                    servicios_count,
                    x='Servicio',
                    y='Cantidad',
                    title='Servicios Especiales Más Populares',
                    color='Servicio'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay servicios especiales registrados")

# ============================================================
# PIE DE PÁGINA
# ============================================================
st.divider()
st.caption("🏨 Sistema de Gestión Hotelera - Base de Datos I 2024")

# ============================================================
# INFORMACIÓN DE DIAGNÓSTICO (SOLO DESARROLLO)
# ============================================================
with st.expander("🔧 Información Técnica (Desarrollo)", expanded=False):
    st.write("### 📋 Columnas disponibles:")
    st.write(list(df.columns))
    
    st.write("### 📊 Resumen estadístico:")
    st.dataframe(df.describe())
    
    st.write("### 🔗 Conexión activa:")
    st.code(f"URI: {DEFAULT_DB_URI}")
    st.code(f"Registros totales: {len(df)}")
    st.code(f"Registros filtrados: {len(df_filtrado)}")
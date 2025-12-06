import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
st.set_page_config(
    page_title="🏨 Dashboard Hotelero - Proyecto",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CADENA DE CONEXIÓN - PUERTO 3307 como en tu MySQL Workbench
DEFAULT_DB_URI = "mysql+pymysql://root:@localhost:3306/proyecto"

# ============================================================================
# FUNCIONES DE CONEXIÓN Y CARGA
# ============================================================================
@st.cache_resource
def get_connection():
    """Establece conexión con la base de datos."""
    try:
        engine = create_engine(DEFAULT_DB_URI)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None

@st.cache_data(ttl=300)
def load_hotel_data():
    """Carga los datos principales del hotel."""
    engine = get_connection()
    if engine is None:
        return pd.DataFrame()
    
    # CONSULTA PRINCIPAL - ESPECÍFICA PARA TUS DATOS
    query = """
    SELECT 
        -- Reserva
        r.id_reserva,
        r.fecha_reserva,
        r.monto_total,
        r.estado_reserva,
        r.localizacion_reserva,
        r.fecha_vencimiento,
        
        -- Cliente
        c.id_cliente,
        c.nombre,
        c.apellido_paterno,
        c.apellido_materno,
        c.ci,
        CONCAT(c.nombre, ' ', c.apellido_paterno, ' ', c.apellido_materno) AS nombre_cliente,
        
        -- Detalle Reserva
        dr.id_detalle_reserva,
        dr.precio_unitario,
        dr.cantidad_personas,
        dr.check_in,
        dr.check_out,
        
        -- Habitación
        h.id_habitacion,
        h.numero_habitacion,
        h.piso,
        h.precio AS precio_habitacion,
        
        -- Tipo Habitación
        th.id_tipo_habitacion,
        th.descripcion AS tipo_habitacion,
        th.numero_camas,
        th.capacidad,
        th.tamano_m2,
        
        -- Servicios Especiales
        COALESCE(se.nombre, 'Sin servicio') AS servicio_especial,
        COALESCE(se.precio, 0) AS precio_servicio,
        
        -- Pago
        p.id_pago,
        p.monto AS monto_pago,
        p.estado_pago,
        p.fecha_pago,
        
        -- Método de Pago (derivado de tablas de pago)
        CASE 
            WHEN mp.nombre = 'Tarjeta crédito' THEN 'TARJETA'
            WHEN mp.nombre = 'Tarjeta débito' THEN 'TARJETA'
            WHEN mp.nombre = 'Efectivo' THEN 'EFECTIVO'
            WHEN mp.nombre = 'Transferencia' THEN 'TRANSFERENCIA'
            WHEN mp.nombre = 'Paypal' THEN 'DIGITAL'
            WHEN mp.nombre = 'QR' THEN 'QR'
            ELSE mp.nombre
        END AS metodo_pago,
        
        -- Información adicional
        f.descuento AS descuento_factura,
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
    LEFT JOIN detalle_pago dp ON p.id_detalle_pago = dp.id_detalle_pago
    LEFT JOIN metodo_pago mp ON dp.id_metodo_pago = mp.id_metodo_pago
    LEFT JOIN factura f ON p.id_factura = f.id_factura
    LEFT JOIN promocion pr ON f.id_factura = pr.id_promocion
    ORDER BY r.fecha_reserva DESC
    """
    
    try:
        df = pd.read_sql(query, engine)
        
        # PROCESAMIENTO DE DATOS
        if not df.empty:
            # Conversión de fechas
            date_cols = ['fecha_reserva', 'check_in', 'check_out', 'fecha_pago', 'fecha_vencimiento']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Calcular duración de estadía
            if 'check_in' in df.columns and 'check_out' in df.columns:
                df['duracion_estadia'] = (df['check_out'] - df['check_in']).dt.days
                df['duracion_estadia'] = df['duracion_estadia'].fillna(0).astype(int)
            
            # Columnas derivadas de fecha
            if 'fecha_reserva' in df.columns:
                df['anio'] = df['fecha_reserva'].dt.year
                df['mes'] = df['fecha_reserva'].dt.month
                df['dia'] = df['fecha_reserva'].dt.day
                df['mes_anio'] = df['fecha_reserva'].dt.to_period('M').astype(str)
                df['dia_semana'] = df['fecha_reserva'].dt.day_name()
                df['semana'] = df['fecha_reserva'].dt.isocalendar().week
            
            # Calcular monto neto (considerando descuentos)
            df['descuento_factura'] = df['descuento_factura'].fillna(0)
            df['porcentaje_descuento'] = df['porcentaje_descuento'].fillna(0)
            
            if 'monto_total' in df.columns:
                df['monto_neto'] = df['monto_total']
                # Aplicar descuentos
                df['descuento_total'] = df['descuento_factura'] + (df['monto_total'] * df['porcentaje_descuento'] / 100)
                df['monto_neto'] = df['monto_total'] - df['descuento_total']
                
                # Agregar precio de servicios
                if 'precio_servicio' in df.columns:
                    df['monto_neto'] = df['monto_neto'] + df['precio_servicio'].fillna(0)
            
            # Calcular ingresos por noche
            df['ingreso_por_noche'] = df['monto_neto'] / df['duracion_estadia'].replace(0, 1)
            
            # Categorías
            df['categoria_cliente'] = pd.cut(
                df['monto_neto'],
                bins=[0, 200, 350, 500, float('inf')],
                labels=['Económico', 'Estándar', 'Premium', 'Lujo']
            )
            
            # Limpieza de valores nulos
            text_cols = ['estado_reserva', 'localizacion_reserva', 'nombre_cliente', 
                        'tipo_habitacion', 'servicio_especial', 'estado_pago', 
                        'metodo_pago', 'codigo_promocional']
            for col in text_cols:
                if col in df.columns:
                    df[col] = df[col].fillna('No especificado')
            
            # Valores numéricos
            num_cols = ['monto_total', 'monto_neto', 'precio_unitario', 'precio_habitacion', 
                       'precio_servicio', 'cantidad_personas', 'duracion_estadia', 'ingreso_por_noche']
            for col in num_cols:
                if col in df.columns:
                    df[col] = df[col].fillna(0).astype(float)
        
        return df
    
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def create_kpi_card(title, value, delta=None, delta_color="normal"):
    """Crea una tarjeta KPI visualmente atractiva."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric(label=title, value=value, delta=delta, delta_color=delta_color)
    return col1

def format_currency(value):
    """Formatea un valor como moneda."""
    return f"${value:,.2f}"

def format_number(value):
    """Formatea un número con separadores."""
    return f"{value:,.0f}"

# ============================================================================
# FUNCIÓN DE FILTRADO
# ============================================================================
def aplicar_filtros(df, filtros):
    """Aplica todos los filtros seleccionados."""
    df_filtrado = df.copy()
    
    # Filtro por fechas
    if filtros['fecha_inicio'] and filtros['fecha_fin']:
        mask = (df_filtrado['fecha_reserva'].dt.date >= filtros['fecha_inicio']) & \
               (df_filtrado['fecha_reserva'].dt.date <= filtros['fecha_fin'])
        df_filtrado = df_filtrado[mask]
    
    # Filtro por estado de reserva
    if filtros['estados_reserva']:
        df_filtrado = df_filtrado[df_filtrado['estado_reserva'].isin(filtros['estados_reserva'])]
    
    # Filtro por tipo de habitación
    if filtros['tipos_habitacion']:
        df_filtrado = df_filtrado[df_filtrado['tipo_habitacion'].isin(filtros['tipos_habitacion'])]
    
    # Filtro por ubicación
    if filtros['ubicaciones']:
        df_filtrado = df_filtrado[df_filtrado['localizacion_reserva'].isin(filtros['ubicaciones'])]
    
    # Filtro por servicios
    if filtros['servicios']:
        df_filtrado = df_filtrado[df_filtrado['servicio_especial'].isin(filtros['servicios'])]
    
    # Filtro por método de pago
    if filtros['metodos_pago']:
        df_filtrado = df_filtrado[df_filtrado['metodo_pago'].isin(filtros['metodos_pago'])]
    
    return df_filtrado

# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================
def main():
    # TÍTULO PRINCIPAL
    st.title("🏨 Dashboard Hotelero - Sistema de Gestión")
    st.markdown("---")
    
    # CONEXIÓN Y CARGA DE DATOS
    with st.spinner("🔄 Conectando con la base de datos..."):
        engine = get_connection()
    
    if engine is None:
        st.stop()
    
    with st.spinner("📊 Cargando datos del hotel..."):
        df = load_hotel_data()
    
    if df.empty:
        st.warning("⚠️ No se encontraron datos en la base de datos.")
        st.info("""
        **Verifica que:**
        1. MySQL esté corriendo en puerto 3307
        2. La base de datos 'proyecto' exista
        3. Hayas ejecutado el script SQL completo
        4. Hayas insertado los datos de población
        """)
        st.stop()
    
    # ============================================================================
    # SIDEBAR - FILTROS
    # ============================================================================
    with st.sidebar:
        st.header("🔍 Filtros de Análisis")
        st.markdown("---")
        
        # FECHAS
        st.subheader("📅 Rango de Fechas")
        if 'fecha_reserva' in df.columns:
            fecha_min = df['fecha_reserva'].min().date()
            fecha_max = df['fecha_reserva'].max().date()
            fechas = st.date_input(
                "Seleccione el rango:",
                [fecha_min, fecha_max],
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_filtro"
            )
            
            if len(fechas) == 2:
                fecha_inicio, fecha_fin = fechas
            else:
                fecha_inicio, fecha_fin = fecha_min, fecha_max
        else:
            fecha_inicio = datetime.now().date() - timedelta(days=30)
            fecha_fin = datetime.now().date()
            st.date_input("Seleccione el rango:", [fecha_inicio, fecha_fin])
        
        # ESTADOS DE RESERVA
        st.subheader("📋 Estado de Reserva")
        estados_opciones = df['estado_reserva'].unique().tolist() if 'estado_reserva' in df.columns else []
        estados_reserva = st.multiselect(
            "Seleccione estados:",
            options=estados_opciones,
            default=['confirmada'] if 'confirmada' in estados_opciones else []
        )
        
        # TIPOS DE HABITACIÓN
        st.subheader("🛏️ Tipo de Habitación")
        tipos_hab_opciones = df['tipo_habitacion'].unique().tolist() if 'tipo_habitacion' in df.columns else []
        tipos_habitacion = st.multiselect(
            "Seleccione tipos:",
            options=tipos_hab_opciones
        )
        
        # UBICACIONES
        st.subheader("📍 Ubicación")
        ubicaciones_opciones = df['localizacion_reserva'].unique().tolist() if 'localizacion_reserva' in df.columns else []
        ubicaciones = st.multiselect(
            "Seleccione ubicaciones:",
            options=ubicaciones_opciones
        )
        
        # SERVICIOS ESPECIALES
        st.subheader("⭐ Servicios Especiales")
        servicios_opciones = df['servicio_especial'].unique().tolist() if 'servicio_especial' in df.columns else []
        servicios = st.multiselect(
            "Seleccione servicios:",
            options=[s for s in servicios_opciones if s != 'No especificado']
        )
        
        # MÉTODOS DE PAGO
        st.subheader("💳 Método de Pago")
        metodos_opciones = df['metodo_pago'].unique().tolist() if 'metodo_pago' in df.columns else []
        metodos_pago = st.multiselect(
            "Seleccione métodos:",
            options=metodos_opciones
        )
        
        # BOTÓN DE APLICAR FILTROS
        st.markdown("---")
        aplicar_filtros_btn = st.button("✅ Aplicar Filtros", type="primary", use_container_width=True)
        limpiar_filtros_btn = st.button("🧹 Limpiar Filtros", use_container_width=True)
    
    # ============================================================================
    # APLICAR FILTROS
    # ============================================================================
    filtros = {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estados_reserva': estados_reserva,
        'tipos_habitacion': tipos_habitacion,
        'ubicaciones': ubicaciones,
        'servicios': servicios,
        'metodos_pago': metodos_pago
    }
    
    df_filtrado = aplicar_filtros(df, filtros)
    
    if df_filtrado.empty:
        st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")
        st.info("Intenta ajustar los filtros o verifica los datos en la base de datos.")
        st.stop()
    
    # ============================================================================
    # SECCIÓN 1: KPI PRINCIPALES
    # ============================================================================
    st.header("📊 Indicadores Clave de Desempeño (KPI)")
    
    # Calcular métricas
    total_reservas = df_filtrado['id_reserva'].nunique()
    total_ingresos = df_filtrado['monto_neto'].sum()
    ingreso_promedio = df_filtrado['monto_neto'].mean() if total_reservas > 0 else 0
    ocupacion_promedio = df_filtrado['duracion_estadia'].mean() if 'duracion_estadia' in df_filtrado.columns else 0
    clientes_unicos = df_filtrado['id_cliente'].nunique()
    tasa_confirmacion = (df_filtrado['estado_reserva'] == 'confirmada').sum() / total_reservas * 100 if total_reservas > 0 else 0
    
    # Mostrar KPIs en columnas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        create_kpi_card("💰 Ingresos Totales", format_currency(total_ingresos))
    
    with col2:
        create_kpi_card("📋 Reservas Totales", format_number(total_reservas))
    
    with col3:
        create_kpi_card("📈 Reserva Promedio", format_currency(ingreso_promedio))
    
    with col4:
        create_kpi_card("🏨 Estancia Promedio", f"{ocupacion_promedio:.1f} noches")
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        create_kpi_card("👥 Clientes Únicos", format_number(clientes_unicos))
    
    with col6:
        create_kpi_card("✅ Tasa de Confirmación", f"{tasa_confirmacion:.1f}%")
    
    with col7:
        servicios_utilizados = df_filtrado[df_filtrado['servicio_especial'] != 'No especificado']['servicio_especial'].nunique()
        create_kpi_card("⭐ Servicios Utilizados", format_number(servicios_utilizados))
    
    with col8:
        habitaciones_utilizadas = df_filtrado['id_habitacion'].nunique()
        create_kpi_card("🛏️ Habitaciones Ocupadas", format_number(habitaciones_utilizadas))
    
    st.markdown("---")
    
    # ============================================================================
    # SECCIÓN 2: VISUALIZACIONES
    # ============================================================================
    st.header("📈 Análisis Visual")
    
    # PESTAÑAS PARA DIFERENTES ANÁLISIS
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 Análisis Temporal", 
        "🛏️ Habitaciones y Servicios", 
        "👥 Clientes y Pagos", 
        "📊 Distribuciones", 
        "📋 Datos Detallados"
    ])
    
    with tab1:
        # GRÁFICO 1: INGRESOS POR MES
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.subheader("💰 Ingresos Mensuales")
            if 'mes_anio' in df_filtrado.columns:
                ingresos_mensuales = df_filtrado.groupby('mes_anio')['monto_neto'].sum().reset_index()
                fig1 = px.bar(
                    ingresos_mensuales,
                    x='mes_anio',
                    y='monto_neto',
                    title='Evolución de Ingresos por Mes',
                    labels={'monto_neto': 'Ingresos ($)', 'mes_anio': 'Mes'},
                    color='monto_neto',
                    color_continuous_scale='Viridis'
                )
                fig1.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig1, use_container_width=True)
        
        with col_t2:
            # GRÁFICO 2: RESERVAS POR DÍA DE LA SEMANA
            st.subheader("📅 Reservas por Día de la Semana")
            if 'dia_semana' in df_filtrado.columns:
                reservas_dia = df_filtrado['dia_semana'].value_counts().reset_index()
                reservas_dia.columns = ['Día', 'Cantidad']
                # Ordenar días
                dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                reservas_dia['Día'] = pd.Categorical(reservas_dia['Día'], categories=dias_orden, ordered=True)
                reservas_dia = reservas_dia.sort_values('Día')
                
                fig2 = px.line(
                    reservas_dia,
                    x='Día',
                    y='Cantidad',
                    title='Distribución de Reservas por Día',
                    markers=True
                )
                st.plotly_chart(fig2, use_container_width=True)
    
    with tab2:
        col_h1, col_h2 = st.columns(2)
        
        with col_h1:
            # GRÁFICO 3: DISTRIBUCIÓN POR TIPO DE HABITACIÓN
            st.subheader("🛏️ Distribución por Tipo de Habitación")
            if 'tipo_habitacion' in df_filtrado.columns:
                distribucion_habitacion = df_filtrado['tipo_habitacion'].value_counts().reset_index()
                distribucion_habitacion.columns = ['Tipo', 'Cantidad']
                
                fig3 = px.pie(
                    distribucion_habitacion,
                    values='Cantidad',
                    names='Tipo',
                    title='Distribución de Reservas por Tipo de Habitación',
                    hole=0.4
                )
                st.plotly_chart(fig3, use_container_width=True)
        
        with col_h2:
            # GRÁFICO 4: SERVICIOS MÁS POPULARES
            st.subheader("⭐ Servicios Especiales Más Utilizados")
            if 'servicio_especial' in df_filtrado.columns:
                servicios_populares = df_filtrado[df_filtrado['servicio_especial'] != 'No especificado']
                servicios_populares = servicios_populares['servicio_especial'].value_counts().head(10).reset_index()
                servicios_populares.columns = ['Servicio', 'Cantidad']
                
                fig4 = px.bar(
                    servicios_populares,
                    x='Servicio',
                    y='Cantidad',
                    title='Top 10 Servicios Especiales',
                    color='Cantidad',
                    color_continuous_scale='thermal'
                )
                fig4.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig4, use_container_width=True)
    
    with tab3:
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            # GRÁFICO 5: TOP CLIENTES POR CONSUMO
            st.subheader("👑 Top 10 Clientes por Consumo")
            if 'nombre_cliente' in df_filtrado.columns:
                top_clientes = df_filtrado.groupby('nombre_cliente')['monto_neto'].sum().reset_index()
                top_clientes = top_clientes.sort_values('monto_neto', ascending=False).head(10)
                
                fig5 = px.bar(
                    top_clientes,
                    x='nombre_cliente',
                    y='monto_neto',
                    title='Clientes con Mayor Consumo',
                    labels={'monto_neto': 'Consumo Total ($)', 'nombre_cliente': 'Cliente'},
                    color='monto_neto',
                    color_continuous_scale='sunset'
                )
                fig5.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig5, use_container_width=True)
        
        with col_c2:
            # GRÁFICO 6: DISTRIBUCIÓN DE MÉTODOS DE PAGO
            st.subheader("💳 Métodos de Pago Más Utilizados")
            if 'metodo_pago' in df_filtrado.columns:
                metodos_pago_dist = df_filtrado['metodo_pago'].value_counts().reset_index()
                metodos_pago_dist.columns = ['Método', 'Cantidad']
                
                fig6 = px.pie(
                    metodos_pago_dist,
                    values='Cantidad',
                    names='Método',
                    title='Distribución de Métodos de Pago',
                    hole=0.3
                )
                st.plotly_chart(fig6, use_container_width=True)
    
    with tab4:
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            # GRÁFICO 7: DISTRIBUCIÓN DE ESTADÍA
            st.subheader("📅 Distribución de Duración de Estadía")
            if 'duracion_estadia' in df_filtrado.columns:
                fig7 = px.histogram(
                    df_filtrado,
                    x='duracion_estadia',
                    nbins=20,
                    title='Distribución de Noches por Reserva',
                    labels={'duracion_estadia': 'Noches de Estadía'},
                    color_discrete_sequence=['#636efa']
                )
                fig7.update_layout(bargap=0.1)
                st.plotly_chart(fig7, use_container_width=True)
        
        with col_d2:
            # GRÁFICO 8: INGRESOS POR CATEGORÍA DE CLIENTE
            st.subheader("🏷️ Ingresos por Categoría de Cliente")
            if 'categoria_cliente' in df_filtrado.columns:
                ingresos_categoria = df_filtrado.groupby('categoria_cliente')['monto_neto'].sum().reset_index()
                
                fig8 = px.bar(
                    ingresos_categoria,
                    x='categoria_cliente',
                    y='monto_neto',
                    title='Ingresos por Categoría de Cliente',
                    labels={'monto_neto': 'Ingresos ($)', 'categoria_cliente': 'Categoría'},
                    color='categoria_cliente',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig8, use_container_width=True)
    
    with tab5:
        # TABLA DE DATOS DETALLADOS
        st.subheader("📋 Datos Detallados de Reservas")
        
        # Seleccionar columnas para mostrar
        columnas_disponibles = [
            'id_reserva', 'fecha_reserva', 'nombre_cliente', 'tipo_habitacion',
            'check_in', 'check_out', 'duracion_estadia', 'monto_neto',
            'estado_reserva', 'metodo_pago', 'servicio_especial', 'localizacion_reserva'
        ]
        
        columnas_seleccionadas = st.multiselect(
            "Seleccione columnas para mostrar:",
            options=columnas_disponibles,
            default=columnas_disponibles[:8]
        )
        
        if columnas_seleccionadas:
            # Filtrar columnas disponibles
            columnas_validas = [col for col in columnas_seleccionadas if col in df_filtrado.columns]
            
            if columnas_validas:
                # Mostrar tabla
                st.dataframe(
                    df_filtrado[columnas_validas],
                    use_container_width=True,
                    height=400
                )
                
                # Estadísticas resumen
                with st.expander("📊 Estadísticas Resumen"):
                    st.write(f"**Total de registros:** {len(df_filtrado)}")
                    st.write(f"**Período:** {fecha_inicio} al {fecha_fin}")
                    st.write(f"**Ingreso total:** {format_currency(total_ingresos)}")
                    st.write(f"**Reservas promedio por día:** {(len(df_filtrado) / max((fecha_fin - fecha_inicio).days, 1)):.1f}")
                
                # Botón de descarga
                csv = df_filtrado[columnas_validas].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Datos (CSV)",
                    data=csv,
                    file_name=f"reservas_hotel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No hay columnas válidas para mostrar.")
    
    # ============================================================================
    # SECCIÓN 3: RESUMEN Y RECOMENDACIONES
    # ============================================================================
    st.markdown("---")
    st.header("💡 Análisis y Recomendaciones")
    
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        with st.container(border=True):
            st.subheader("📈 Tendencias Positivas")
            
            # Análisis de tendencias
            if 'mes_anio' in df_filtrado.columns and len(df_filtrado) > 1:
                ingresos_mensuales = df_filtrado.groupby('mes_anio')['monto_neto'].sum()
                if len(ingresos_mensuales) > 1:
                    crecimiento = ((ingresos_mensuales.iloc[-1] - ingresos_mensuales.iloc[0]) / ingresos_mensuales.iloc[0] * 100)
                    if crecimiento > 0:
                        st.success(f"📈 **Crecimiento del {crecimiento:.1f}%** en ingresos mensuales")
                    else:
                        st.warning(f"📉 **Decrecimiento del {abs(crecimiento):.1f}%** en ingresos mensuales")
            
            # Servicios más rentables
            if 'servicio_especial' in df_filtrado.columns:
                servicios_rentables = df_filtrado.groupby('servicio_especial')['monto_neto'].sum().nlargest(3)
                st.write("**Servicios más rentables:**")
                for servicio, monto in servicios_rentables.items():
                    if servicio != 'No especificado':
                        st.write(f"- {servicio}: {format_currency(monto)}")
    
    with col_r2:
        with st.container(border=True):
            st.subheader("🎯 Oportunidades de Mejora")
            
            # Reservas canceladas
            if 'estado_reserva' in df_filtrado.columns:
                canceladas = (df_filtrado['estado_reserva'] == 'cancelada').sum()
                total = len(df_filtrado)
                if total > 0:
                    tasa_cancelacion = (canceladas / total) * 100
                    if tasa_cancelacion > 10:
                        st.error(f"⚠️ **Alta tasa de cancelación:** {tasa_cancelacion:.1f}%")
                    elif tasa_cancelacion > 5:
                        st.warning(f"⚠️ **Tasa de cancelación moderada:** {tasa_cancelacion:.1f}%")
            
            # Métodos de pago poco utilizados
            if 'metodo_pago' in df_filtrado.columns:
                metodos_bajos = df_filtrado['metodo_pago'].value_counts().nsmallest(2)
                if len(metodos_bajos) > 0:
                    st.write("**Métodos de pago menos utilizados:**")
                    for metodo, cantidad in metodos_bajos.items():
                        st.write(f"- {metodo}: {cantidad} veces")
    
    # ============================================================================
    # PIE DE PÁGINA
    # ============================================================================
    st.markdown("---")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        st.caption(f"📅 **Período analizado:** {fecha_inicio} - {fecha_fin}")
    
    with col_f2:
        st.caption(f"📊 **Total de registros:** {len(df_filtrado)}")
    
    with col_f3:
        st.caption("🏨 **Sistema Hotelero - Base de Datos I 2024**")
    
    # ============================================================================
    # SECCIÓN DIAGNÓSTICO (SOLO EN MODO DESARROLLO)
    # ============================================================================
    with st.expander("🔧 Información Técnica (Solo Desarrollo)", expanded=False):
        st.write("### 📋 Información de la Base de Datos")
        st.write(f"**URI de conexión:** `{DEFAULT_DB_URI}`")
        st.write(f"**Total de registros cargados:** {len(df)}")
        st.write(f"**Registros después de filtros:** {len(df_filtrado)}")
        
        st.write("### 📊 Columnas Disponibles")
        st.write(list(df.columns))
        
        st.write("### 🔍 Muestra de Datos")
        st.dataframe(df.head(5), use_container_width=True)

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================
if __name__ == "__main__":
    main()
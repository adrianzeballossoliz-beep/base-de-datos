import pandas as pd
import mysql.connector
from mysql.connector import Error

# -----------------------------------------------------------
# 1. CONFIGURACIÓN DE LA BASE DE DATOS (AJUSTA ESTOS VALORES)
# -----------------------------------------------------------
DB_CONFIG = {
    'host': 'localhost',
    'database': 'Practica_Normalizacion_4_Restaurante',
    'user': 'tu_usuario_mysql',   # EJ: root
    'password': 'tu_password_mysql' # EJ: 1234
}

ARCHIVO_CSV = 'Practica Normalizacion(4).csv'

# -----------------------------------------------------------
# 2. FUNCIÓN DE CONEXIÓN
# -----------------------------------------------------------
def crear_conexion():
    """Crea y devuelve un objeto de conexión a MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

# -----------------------------------------------------------
# 3. PROCESAMIENTO Y POBLAMIENTO DE DATOS
# -----------------------------------------------------------
def poblar_tablas():
    conn = crear_conexion()
    if conn is None:
        return

    cursor = conn.cursor()

    try:
        # A. LEER Y LIMPIAR EL CSV (Asumiendo que la primera fila es un encabezado extra)
        df = pd.read_csv(ARCHIVO_CSV, skiprows=1)
        
        # Eliminar las filas de restricciones al final
        df = df.iloc[:4] 
        
        # Formatear la columna de fechas a AAAA-MM-DD
        df['Fecha_Reservación'] = pd.to_datetime(df['Fecha_Reservación'], format='%m/%d/%Y').dt.strftime('%Y-%m-%d')
        
        # Mapeos para Claves Foráneas
        cliente_map = {}
        mesa_map = {}

        # ----------------------------------------------------
        # B. POBLAR TABLA MESAS
        # ----------------------------------------------------
        print("Poblando Mesas...")
        
        # Extraer datos únicos de mesas
        mesas_unicas = df[['Mesa', 'Capacidad_Mesa']].drop_duplicates().sort_values(by='Mesa')
        
        # TRUNCATE para limpiar antes de insertar y reiniciar AUTO_INCREMENT
        cursor.execute("TRUNCATE TABLE Mesas")
        conn.commit()

        for index, row in mesas_unicas.iterrows():
            nro_mesa = row['Mesa']
            capacidad = row['Capacidad_Mesa']

            sql = "INSERT INTO Mesas (nro_mesa, capacidad_maxima) VALUES (%s, %s)"
            cursor.execute(sql, (nro_mesa, capacidad))
            
            # Obtener el ID generado (AUTO_INCREMENT)
            id_mesa = cursor.lastrowid
            mesa_map[nro_mesa] = id_mesa
        
        conn.commit()
        print(f"Mesas insertadas: {len(mesa_map)}")

        # ----------------------------------------------------
        # C. POBLAR TABLA CLIENTES
        # ----------------------------------------------------
        print("Poblando Clientes...")
        
        # Extraer datos únicos de clientes
        clientes_unicos = df[['Codigo_cliente', 'Nombre_Cliente', 'Teléfono', 'Correo', 'Dirección_Cliente']].drop_duplicates(subset=['Codigo_cliente'])
        
        cursor.execute("TRUNCATE TABLE Clientes")
        conn.commit()
        
        for index, row in clientes_unicos.iterrows():
            codigo = row['Codigo_cliente']
            nombre = row['Nombre_Cliente']
            telefono = row['Teléfono']
            correo = row['Correo']
            direccion = row['Dirección_Cliente']

            sql = "INSERT INTO Clientes (codigo_cliente, nombre_cliente, telefono_cliente, correo_cliente, direccion_cliente) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (codigo, nombre, telefono, correo, direccion))
            
            # Obtener el ID generado (AUTO_INCREMENT)
            id_cliente = cursor.lastrowid
            cliente_map[codigo] = id_cliente
        
        conn.commit()
        print(f"Clientes insertados: {len(cliente_map)}")

        # ----------------------------------------------------
        # D. POBLAR TABLA RESERVACIONES (USANDO FKs)
        # ----------------------------------------------------
        print("Poblando Reservaciones...")
        
        cursor.execute("TRUNCATE TABLE Reservaciones")
        conn.commit()
        
        for index, row in df.iterrows():
            # Obtener Claves Foráneas (FK) a través de los mapas
            fk_cliente = cliente_map.get(row['Codigo_cliente'])
            fk_mesa = mesa_map.get(row['Mesa'])
            
            # Datos de Reservaciones
            fecha = row['Fecha_Reservación']
            hora = row['Hora']
            personas = row['Cantidad_Personas']
            estado = row['Estado_Reservación']
            pago = row['Método_Pago']
            total = row['Total_Pagado']

            sql = """
            INSERT INTO Reservaciones (fecha_reservacion, hora_reservacion, cantidad_personas, estado_reservacion, metodo_pago, total_pagado, id_cliente, id_mesa)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (fecha, hora, personas, estado, pago, total, fk_cliente, fk_mesa))

        conn.commit()
        print(f"Reservaciones insertadas: {len(df)}")
        print("\n¡Poblamiento del Ejercicio 4 completado con éxito!")


    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo '{ARCHIVO_CSV}'.")
    except Error as e:
        print(f"ERROR de SQL: {e}")
        conn.rollback() # Deshacer cambios si hay un error
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if _name_ == "_main_":
    poblar_tablas()
pip install -r requirements.txt
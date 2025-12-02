# -*- coding: utf-8 -*-
"""
Script para cargar datos de dengue del CSV a la base de datos
Adaptado a la estructura de tablas del proyecto
"""

import pandas as pd
import mysql.connector
from datetime import datetime
import os

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin',
    'database': 'proyecto_integrador'
}

# Mapeo de códigos de entidad a nombres de estados (INEGI)
ENTIDADES = {
    1: 'Aguascalientes',
    2: 'Baja California',
    3: 'Baja California Sur',
    4: 'Campeche',
    5: 'Coahuila',
    6: 'Colima',
    7: 'Chiapas',
    8: 'Chihuahua',
    9: 'Ciudad de México',
    10: 'Durango',
    11: 'Guanajuato',
    12: 'Guerrero',
    13: 'Hidalgo',
    14: 'Jalisco',
    15: 'Estado de México',
    16: 'Michoacán',
    17: 'Morelos',
    18: 'Nayarit',
    19: 'Nuevo León',
    20: 'Oaxaca',
    21: 'Puebla',
    22: 'Querétaro',
    23: 'Quintana Roo',
    24: 'San Luis Potosí',
    25: 'Sinaloa',
    26: 'Sonora',
    27: 'Tabasco',
    28: 'Tamaulipas',
    29: 'Tlaxcala',
    30: 'Veracruz',
    31: 'Yucatán',
    32: 'Zacatecas'
}

# Población por estado (Censo 2020)
POBLACION = {
    1: 1425607,
    2: 3769020,
    3: 798447,
    4: 928363,
    5: 3146771,
    6: 731391,
    7: 5543828,
    8: 3741869,
    9: 9209944,
    10: 1832650,
    11: 6166934,
    12: 3540685,
    13: 3082841,
    14: 8348151,
    15: 16992418,
    16: 4748846,
    17: 1971520,
    18: 1235456,
    19: 5784442,
    20: 4132148,
    21: 6583278,
    22: 2368467,
    23: 1857985,
    24: 2822255,
    25: 3026943,
    26: 2944840,
    27: 2402598,
    28: 3527735,
    29: 1342977,
    30: 8062579,
    31: 2320898,
    32: 1622138
}

def conectar_db():
    """Conecta a la base de datos MySQL"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("✅ Conexión a la base de datos exitosa")
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Error de conexión: {err}")
        return None

def insertar_enfermedad_dengue(cursor):
    """Inserta la enfermedad Dengue si no existe"""
    cursor.execute("SELECT id_enfermedad FROM enfermedad WHERE nombre = 'Dengue'")
    result = cursor.fetchone()
    if result:
        print(f"✅ Enfermedad 'Dengue' ya existe con ID: {result[0]}")
        return result[0]
    
    try:
        cursor.execute("""
            INSERT INTO enfermedad (nombre, descripcion, sintomas, via_transmision)
            VALUES ('Dengue', 'Enfermedad viral transmitida por mosquitos Aedes', 
                    'Fiebre alta, dolor de cabeza, dolor muscular, sarpullido', 
                    'Picadura de mosquito Aedes aegypti')
        """)
        id_enfermedad = cursor.lastrowid
        print(f"✅ Enfermedad 'Dengue' insertada con ID: {id_enfermedad}")
        return id_enfermedad
    except mysql.connector.Error as e:
        print(f"⚠️ Error insertando enfermedad: {e}")
        # Intentar obtener el ID de nuevo
        cursor.execute("SELECT id_enfermedad FROM enfermedad WHERE nombre = 'Dengue'")
        result = cursor.fetchone()
        return result[0] if result else 1

def insertar_regiones(cursor):
    """Inserta las 32 entidades federativas"""
    print("\n📍 Insertando/actualizando regiones...")
    
    regiones_db = {}
    for codigo, nombre in ENTIDADES.items():
        poblacion = POBLACION.get(codigo, 0)
        try:
            cursor.execute("""
                INSERT INTO region (id_region, nombre, codigo_postal, poblacion)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    nombre = VALUES(nombre),
                    poblacion = VALUES(poblacion)
            """, (codigo, nombre, str(codigo * 1000).zfill(5), poblacion))
            regiones_db[codigo] = nombre
        except mysql.connector.Error as e:
            print(f"   ⚠️ Error con {nombre}: {e}")
    
    print(f"✅ {len(regiones_db)} regiones configuradas")
    return regiones_db

def cargar_csv(ruta_csv):
    """Carga y procesa el CSV de datos de dengue"""
    print(f"\n📂 Cargando CSV: {ruta_csv}")
    
    df = pd.read_csv(ruta_csv, encoding='latin-1', low_memory=False)
    print(f"   Total de registros en CSV: {len(df):,}")
    
    # Convertir fecha
    df['fecha'] = pd.to_datetime(df['FECHA_SIGN_SINTOMAS'], errors='coerce')
    
    # Filtrar registros válidos
    df = df.dropna(subset=['fecha', 'ENTIDAD_RES'])
    df['ENTIDAD_RES'] = df['ENTIDAD_RES'].astype(int)
    print(f"   Registros válidos: {len(df):,}")
    
    # ESTATUS_CASO: 1=Probable, 2=No es caso, 3=Confirmado
    df['es_confirmado'] = (df['ESTATUS_CASO'] == 3).astype(int)
    df['es_defuncion'] = (df['DEFUNCION'] == 1).astype(int) if 'DEFUNCION' in df.columns else 0
    
    # Agregar columna de semana (para agrupar por semana)
    df['fecha_semana'] = df['fecha'].dt.to_period('W').dt.start_time
    
    return df

def procesar_y_agregar(df):
    """Agrega datos por semana y entidad"""
    print("\n🔄 Agregando datos por semana y estado...")
    
    agregado = df.groupby(['ENTIDAD_RES', 'fecha_semana']).agg({
        'es_confirmado': 'sum',
        'es_defuncion': 'sum'
    }).reset_index()
    
    agregado.columns = ['id_region', 'fecha', 'casos_confirmados', 'defunciones']
    
    print(f"   Registros agregados: {len(agregado):,}")
    print(f"   Rango de fechas: {agregado['fecha'].min().date()} a {agregado['fecha'].max().date()}")
    print(f"   Total casos confirmados: {agregado['casos_confirmados'].sum():,}")
    
    return agregado

def insertar_datos(cursor, datos, id_enfermedad):
    """Inserta los datos en la tabla dato_epidemiologico"""
    print("\n💾 Insertando datos epidemiológicos...")
    
    # NO borramos datos anteriores, agregamos usando INSERT ... ON DUPLICATE KEY UPDATE
    
    sql = """
        INSERT INTO dato_epidemiologico 
        (id_enfermedad, id_region, fecha, fecha_carga, casos_confirmados, defunciones)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            casos_confirmados = casos_confirmados + VALUES(casos_confirmados),
            defunciones = defunciones + VALUES(defunciones)
    """
    
    insertados = 0
    errores = 0
    fecha_carga = datetime.now().date()
    
    for _, row in datos.iterrows():
        try:
            valores = (
                id_enfermedad,
                int(row['id_region']),
                row['fecha'].strftime('%Y-%m-%d'),
                fecha_carga,
                int(row['casos_confirmados']),
                int(row['defunciones'])
            )
            cursor.execute(sql, valores)
            insertados += 1
            
            if insertados % 500 == 0:
                print(f"   Progreso: {insertados:,} registros...")
                
        except mysql.connector.Error as e:
            errores += 1
            if errores <= 3:
                print(f"   ⚠️ Error: {e}")
    
    print(f"\n✅ Insertados: {insertados:,} registros")
    if errores > 0:
        print(f"⚠️ Errores: {errores}")
    
    return insertados

def mostrar_resumen(cursor):
    """Muestra un resumen de los datos cargados"""
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE DATOS CARGADOS")
    print("=" * 60)
    
    cursor.execute("SELECT COUNT(*) FROM dato_epidemiologico")
    print(f"Total registros: {cursor.fetchone()[0]:,}")
    
    cursor.execute("SELECT MIN(fecha), MAX(fecha) FROM dato_epidemiologico")
    fechas = cursor.fetchone()
    print(f"Período: {fechas[0]} a {fechas[1]}")
    
    cursor.execute("SELECT SUM(casos_confirmados), SUM(defunciones) FROM dato_epidemiologico")
    totales = cursor.fetchone()
    print(f"Total casos confirmados: {totales[0]:,}")
    print(f"Total defunciones: {totales[1] or 0:,}")
    
    print("\n🏆 Top 10 estados con más casos:")
    cursor.execute("""
        SELECT r.nombre, SUM(d.casos_confirmados) as total
        FROM dato_epidemiologico d
        JOIN region r ON d.id_region = r.id_region
        GROUP BY r.id_region, r.nombre
        ORDER BY total DESC
        LIMIT 10
    """)
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"   {i:2}. {row[0]}: {row[1]:,} casos")

def main():
    print("=" * 60)
    print("🦟 CARGADOR DE DATOS DE DENGUE - CSV A MySQL")
    print("=" * 60)
    
    # Ruta al CSV - CAMBIAR AQUÍ PARA OTROS ARCHIVOS
    ruta_csv = r'c:\GDPS-PROEVIRA\ProeVira\data\Datos abiertos dengue_2021.csv'
    
    if not os.path.exists(ruta_csv):
        print(f"❌ No se encontró: {ruta_csv}")
        return
    
    conn = conectar_db()
    if conn is None:
        return
    
    cursor = conn.cursor()
    
    try:
        # 1. Insertar enfermedad
        id_enfermedad = insertar_enfermedad_dengue(cursor)
        conn.commit()
        
        # 2. Insertar regiones
        insertar_regiones(cursor)
        conn.commit()
        
        # 3. Cargar CSV
        df = cargar_csv(ruta_csv)
        
        # 4. Procesar datos
        datos = procesar_y_agregar(df)
        
        # 5. Insertar datos
        insertar_datos(cursor, datos, id_enfermedad)
        conn.commit()
        
        # 6. Mostrar resumen
        mostrar_resumen(cursor)
        
        print("\n✅ ¡PROCESO COMPLETADO EXITOSAMENTE!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        print("\n🔌 Conexión cerrada")

if __name__ == '__main__':
    main()

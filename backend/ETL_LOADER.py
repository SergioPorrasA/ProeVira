# ----------------------------------------------------------------------
# ETL_LOADER.PY: Proceso de Extracción, Transformación y Carga a MySQL
# ----------------------------------------------------------------------

import pandas as pd
import numpy as np
import mysql.connector
from datetime import date
import os

# --- 1. CONFIGURACIÓN Y DATOS ---

# Obtener el directorio base del proyecto (un nivel arriba del script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)  # C:\GDPS-PROEVIRA\ProeVira
DATA_DIR = os.path.join(PROJECT_DIR, 'data')

# ⚠️ ADAPTAR ESTAS VARIABLES DE CONEXIÓN A TU ENTORNO MySQL
DB_CONFIG = {
    'user': 'root', 
    'password': 'admin', 
    'host': '127.0.0.1',
    'database': 'proyecto_integrador'
}

# Lista de archivos CSV con rutas absolutas (6 años de datos)
ARCHIVO_NOMBRES = [
    os.path.join(DATA_DIR, 'dengue_2020.csv'), 
    os.path.join(DATA_DIR, 'dengue_2021.csv'),
    os.path.join(DATA_DIR, 'dengue_2022.csv'),
    os.path.join(DATA_DIR, 'dengue_2023.csv'),
    os.path.join(DATA_DIR, 'dengue_2024.csv'),
    os.path.join(DATA_DIR, 'dengue_2025.csv')
]

print(f"📂 Directorio de datos: {DATA_DIR}")

# Proyección de Población (CONAPO 2025) - Se usa para el mapeo de regiones y cálculo de TI
POBLACION_2025_PROYECCION = {
    1: ('Aguascalientes', 1512400), 2: ('Baja California', 3968300), 3: ('Baja California Sur', 850700),
    4: ('Campeche', 1011800), 5: ('Coahuila de Zaragoza', 3328500), 6: ('Colima', 775100),
    7: ('Chiapas', 6000100), 8: ('Chihuahua', 3998500), 9: ('Ciudad de México', 9386700),
    10: ('Durango', 1913400), 11: ('Guanajuato', 6555200), 12: ('Guerrero', 3724300),
    13: ('Hidalgo', 3327600), 14: ('Jalisco', 8847600), 15: ('México', 18016500),
    16: ('Michoacán de Ocampo', 4975800), 17: ('Morelos', 2056000), 18: ('Nayarit', 1294800),
    19: ('Nuevo León', 6231200), 20: ('Oaxaca', 4432900), 21: ('Puebla', 6886400),
    22: ('Querétaro', 2603300), 23: ('Quintana Roo', 1989500), 24: ('San Luis Potosí', 2931400),
    25: ('Sinaloa', 3274600), 26: ('Sonora', 3154100), 27: ('Tabasco', 2601900),
    28: ('Tamaulipas', 3682900), 29: ('Tlaxcala', 1421000), 30: ('Veracruz de Ignacio de la Llave', 8871300),
    31: ('Yucatán', 2561900), 32: ('Zacatecas', 1698200)
}

# --- 2. FUNCIÓN DE TRANSFORMACIÓN (Lógica ML) ---

def process_data(archivo_nombres):
    """Consolida, limpia, calcula TI y crea el target de riesgo."""
    
    # 1. Consolidación y Limpieza Inicial
    df_list = []
    for file_name in archivo_nombres:
        if os.path.exists(file_name):
            try:
                df_anual = pd.read_csv(file_name)
                df_list.append(df_anual)
                print(f"✅ Cargado: {os.path.basename(file_name)} ({len(df_anual)} registros)")
            except Exception as e:
                print(f"❌ Error al leer {file_name}: {e}")
        else:
            print(f"⚠️ Archivo no encontrado: {file_name}")
            
    if not df_list: raise ValueError("No se pudo cargar ningún archivo CSV.")

    df_consolidado = pd.concat(df_list, ignore_index=True)
    df = df_consolidado.copy()
    df['FECHA_SIGN_SINTOMAS'] = pd.to_datetime(df['FECHA_SIGN_SINTOMAS'], errors='coerce')
    df.dropna(subset=['FECHA_SIGN_SINTOMAS'], inplace=True)
    df_confirmados = df[df['ESTATUS_CASO'] == 1].copy()

    # 2. Mapeo de Población (necesario para TI)
    df_poblacion = pd.DataFrame(POBLACION_2025_PROYECCION).T
    df_poblacion.columns = ['NOMBRE_ESTADO', 'POBLACION']
    df_poblacion.index.name = 'ENTIDAD_RES'
    df_confirmados = df_confirmados.merge(df_poblacion, on='ENTIDAD_RES', how='left')
    df_confirmados.dropna(subset=['POBLACION'], inplace=True)
    
    # 3. Agregación a Series de Tiempo (df_ts)
    df_ts = (
        df_confirmados.groupby(['ENTIDAD_RES', 'NOMBRE_ESTADO', 'POBLACION'])
        .resample('W', on='FECHA_SIGN_SINTOMAS')
        .size()
        .reset_index(name='CASOS_CONFIRMADOS')
    )
    df_ts.rename(columns={'FECHA_SIGN_SINTOMAS': 'fecha_fin_semana'}, inplace=True)
    
    # 4. Cálculo de Tasa de Incidencia (TI) y Target (Y)
    df_ts['tasa_incidencia'] = (df_ts['CASOS_CONFIRMADOS'] / df_ts['POBLACION']) * 100000
    
    # El Umbral de Riesgo (Percentil 75) se calcula sobre TODA la historia
    umbral_riesgo = df_ts['tasa_incidencia'].quantile(0.75)
    df_ts['riesgo_brote_target'] = np.where(df_ts['tasa_incidencia'] > umbral_riesgo, 1, 0).astype(int)

    # 5. Preparar para la carga a DB
    # ⚠️ ASUMIMOS que el ID de la enfermedad (Dengue) es 1
    df_ts['id_enfermedad'] = 1 
    df_ts['defunciones'] = 0 
    df_ts['fecha_carga'] = date.today()
    
    # Mapeo de columnas a la tabla SQL (Usamos ENTIDAD_RES como id_region)
    df_ts.rename(columns={'ENTIDAD_RES': 'id_region', 'CASOS_CONFIRMADOS': 'casos_confirmados'}, inplace=True)

    # DataFrame de Regiones (para cargar el catálogo primero)
    df_regiones = df_ts[['id_region', 'NOMBRE_ESTADO']].drop_duplicates()
    df_regiones = df_regiones.rename(columns={'NOMBRE_ESTADO': 'nombre'})

    # Columnas que coinciden con la tabla dato_epidemiologico
    df_final = df_ts[['id_enfermedad', 'id_region', 'fecha_fin_semana', 
                      'casos_confirmados', 'defunciones', 'tasa_incidencia', 
                      'riesgo_brote_target', 'fecha_carga']].copy()
    
    return df_final, df_regiones


# --- 3. FUNCIÓN DE CARGA A BASE DE DATOS (MySQL) ---

def load_to_db(df_final, df_regiones):
    """Conecta a MySQL e inserta los datos procesados."""
    cnx = None
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        print("\nConexión a la base de datos MySQL exitosa.")

        # A. Carga de Regiones (Catálogo de Estados)
        print("Cargando catálogo de regiones (Estados)...")
        for index, row in df_regiones.iterrows():
            insert_region = """
            INSERT IGNORE INTO region (id_region, nombre, codigo_entidad_inegi) 
            VALUES (%s, %s, %s)
            """
            # Usamos el id_region (código INEGI) para los 3 campos
            cursor.execute(insert_region, (row['id_region'], row['nombre'], row['id_region']))
        cnx.commit()
        print(f"Catálogo de regiones cargado/actualizado.")
        
        # B. Carga de Datos Epidemiológicos (Serie de Tiempo)
        print("Cargando 6 años de series de tiempo en dato_epidemiologico...")
        # ON DUPLICATE KEY UPDATE es CRÍTICO para actualizar registros si se corre el ETL de nuevo
        insert_dato = """
        INSERT INTO dato_epidemiologico (id_enfermedad, id_region, fecha_fin_semana, 
                                          casos_confirmados, defunciones, tasa_incidencia, 
                                          riesgo_brote_target, fecha_carga)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            casos_confirmados = VALUES(casos_confirmados), 
            tasa_incidencia = VALUES(tasa_incidencia),
            riesgo_brote_target = VALUES(riesgo_brote_target),
            fecha_carga = VALUES(fecha_carga)
        """
        
        datos_para_sql = [
            (row['id_enfermedad'], row['id_region'], row['fecha_fin_semana'].date(), 
             row['casos_confirmados'], row['defunciones'], round(row['tasa_incidencia'], 4), 
             row['riesgo_brote_target'], row['fecha_carga']) 
            for index, row in df_final.iterrows()
        ]

        cursor.executemany(insert_dato, datos_para_sql)
        cnx.commit()
        print(f"Carga de {len(df_final)} registros completada en dato_epidemiologico.")

    except mysql.connector.Error as err:
        print(f"ERROR DE BASE DE DATOS: {err}")
    finally:
        if cnx and cnx.is_connected():
            cursor.close()
            cnx.close()


# --- 4. EJECUCIÓN DEL PROCESO ETL ---

if __name__ == "__main__":
    try:
        df_final, df_regiones = process_data(ARCHIVO_NOMBRES)
        load_to_db(df_final, df_regiones)
        print("\n✅ Proceso ETL completado. La base de datos está lista para las consultas ML.")

    except Exception as e:
        print(f"\n❌ FALLO EL PROCESO ETL GLOBAL: {e}")
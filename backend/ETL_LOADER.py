# ----------------------------------------------------------------------
# ETL_LOADER.PY: Proceso de Extracción, Transformación y Carga a MySQL
# ----------------------------------------------------------------------

import pandas as pd
import numpy as np
import mysql.connector
from datetime import date
import os
from db_config import get_db_connection, DB_CONFIG

# --- 1. CONFIGURACIÓN Y DATOS ---

# Obtener el directorio base del proyecto (un nivel arriba del script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)  # C:\GDPS-PROEVIRA\ProeVira
DATA_DIR = os.path.join(PROJECT_DIR, 'data')

# Configuración de conexión importada de db_config
# DB_CONFIG ya está disponible


# Lista de archivos CSV con rutas absolutas (26 años de datos: 2000-2025)
# dengue_historico_2000_2020.csv: generado por scripts/transform_clean_csv.py (CSVs limpios manuales)
# dengue_2021-2025.csv: datos detallados caso por caso del sistema oficial
ARCHIVO_NOMBRES = [
    # Datos históricos limpios manualmente (2000-2020) - formato agregado mensual
    os.path.join(DATA_DIR, 'dengue_historico_2000_2020.csv'),
    # Datos detallados originales (2021-2025) - formato caso por caso
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

def process_historical_csv(df):
    """Procesa CSV histórico ya transformado (formato pre-procesado)."""
    # El archivo histórico ya tiene el formato correcto
    df['fecha_fin_semana'] = pd.to_datetime(df['fecha_fin_semana'], errors='coerce')
    df.dropna(subset=['fecha_fin_semana'], inplace=True)
    
    # Asegurar tipos correctos
    df['id_enfermedad'] = df['id_enfermedad'].astype(int)
    df['id_region'] = df['id_region'].astype(int)
    df['casos_confirmados'] = df['casos_confirmados'].astype(int)
    df['defunciones'] = df.get('defunciones', 0).fillna(0).astype(int)
    df['tasa_incidencia'] = df['tasa_incidencia'].astype(float)
    df['riesgo_brote_target'] = df['riesgo_brote_target'].astype(int)
    
    return df

def process_detailed_csv(df_list):
    """Procesa CSVs detallados con casos individuales (formato original 2020-2025)."""
    df_consolidado = pd.concat(df_list, ignore_index=True)
    df = df_consolidado.copy()
    df['FECHA_SIGN_SINTOMAS'] = pd.to_datetime(df['FECHA_SIGN_SINTOMAS'], errors='coerce')
    df.dropna(subset=['FECHA_SIGN_SINTOMAS'], inplace=True)
    df_confirmados = df[df['ESTATUS_CASO'] == 1].copy()

    # Mapeo de Población (necesario para TI)
    df_poblacion = pd.DataFrame(POBLACION_2025_PROYECCION).T
    df_poblacion.columns = ['NOMBRE_ESTADO', 'POBLACION']
    df_poblacion.index.name = 'ENTIDAD_RES'
    df_confirmados = df_confirmados.merge(df_poblacion, on='ENTIDAD_RES', how='left')
    df_confirmados.dropna(subset=['POBLACION'], inplace=True)

    # Agregación a Series de Tiempo (df_ts)
    df_ts = (
        df_confirmados.groupby(['ENTIDAD_RES', 'NOMBRE_ESTADO', 'POBLACION'])
        .resample('W', on='FECHA_SIGN_SINTOMAS')
        .size()
        .reset_index(name='CASOS_CONFIRMADOS')
    )
    df_ts.rename(columns={'FECHA_SIGN_SINTOMAS': 'fecha_fin_semana'}, inplace=True)

    # Cálculo de Tasa de Incidencia (TI)
    df_ts['tasa_incidencia'] = (df_ts['CASOS_CONFIRMADOS'] / df_ts['POBLACION']) * 100000

    # Preparar para la carga a DB
    df_ts['id_enfermedad'] = 1
    df_ts['defunciones'] = 0

    # Mapeo de columnas
    df_ts.rename(columns={'ENTIDAD_RES': 'id_region', 'CASOS_CONFIRMADOS': 'casos_confirmados'}, inplace=True)
    
    return df_ts

def process_data(archivo_nombres):
    """Consolida, limpia, calcula TI y crea el target de riesgo.
    Maneja tanto CSVs históricos (pre-procesados) como detallados (casos individuales)."""

    # Separar archivos por tipo de formato
    historical_dfs = []
    detailed_dfs = []
    
    for file_name in archivo_nombres:
        if not os.path.exists(file_name):
            print(f"⚠️ Archivo no encontrado: {file_name}")
            continue
            
        try:
            df_anual = pd.read_csv(file_name)
            
            # Detectar formato por columnas
            if 'id_enfermedad' in df_anual.columns and 'fecha_fin_semana' in df_anual.columns:
                # Formato histórico pre-procesado
                historical_dfs.append(df_anual)
                print(f"✅ Cargado (histórico): {os.path.basename(file_name)} ({len(df_anual)} registros)")
            elif 'FECHA_SIGN_SINTOMAS' in df_anual.columns:
                # Formato detallado (casos individuales)
                detailed_dfs.append(df_anual)
                print(f"✅ Cargado (detallado): {os.path.basename(file_name)} ({len(df_anual)} registros)")
            else:
                print(f"⚠️ Formato no reconocido: {file_name}")
                
        except Exception as e:
            print(f"❌ Error al leer {file_name}: {e}")

    if not historical_dfs and not detailed_dfs:
        raise ValueError("No se pudo cargar ningún archivo CSV.")

    # Procesar cada tipo de datos
    all_data = []
    
    # Procesar datos históricos
    if historical_dfs:
        df_historical = pd.concat(historical_dfs, ignore_index=True)
        df_historical = process_historical_csv(df_historical)
        all_data.append(df_historical)
        print(f"\n📊 Datos históricos procesados: {len(df_historical)} registros")
    
    # Procesar datos detallados
    if detailed_dfs:
        df_detailed = process_detailed_csv(detailed_dfs)
        all_data.append(df_detailed)
        print(f"📊 Datos detallados procesados: {len(df_detailed)} registros")
    
    # Consolidar todos los datos
    df_ts = pd.concat(all_data, ignore_index=True)
    
    # Recalcular umbral de riesgo sobre TODA la historia (2000-2025)
    umbral_riesgo = df_ts['tasa_incidencia'].quantile(0.75)
    df_ts['riesgo_brote_target'] = np.where(df_ts['tasa_incidencia'] > umbral_riesgo, 1, 0).astype(int)
    print(f"\n🎯 Umbral de riesgo (P75): {umbral_riesgo:.4f} por 100,000 hab.")
    
    # Limitar tasa_incidencia a valores que quepan en DECIMAL(10,4) de MySQL
    # Máximo permitido: 999999.9999
    max_tasa = df_ts['tasa_incidencia'].max()
    if max_tasa > 999999:
        print(f"⚠️ Valores de tasa_incidencia muy altos detectados (max: {max_tasa:.2f}), limitando a 999999.9999")
        df_ts['tasa_incidencia'] = df_ts['tasa_incidencia'].clip(upper=999999.9999)
    
    # Agregar fecha de carga
    df_ts['fecha_carga'] = date.today()

    # DataFrame de Regiones (para cargar el catálogo)
    # Mapear id_region a nombres de estado
    df_ts['NOMBRE_ESTADO'] = df_ts['id_region'].map(
        {k: v[0] for k, v in POBLACION_2025_PROYECCION.items()}
    )
    df_regiones = df_ts[['id_region', 'NOMBRE_ESTADO']].drop_duplicates()
    df_regiones = df_regiones.rename(columns={'NOMBRE_ESTADO': 'nombre'})

    # Columnas finales para la tabla dato_epidemiologico
    df_final = df_ts[['id_enfermedad', 'id_region', 'fecha_fin_semana',
                      'casos_confirmados', 'defunciones', 'tasa_incidencia',
                      'riesgo_brote_target', 'fecha_carga']].copy()
    
    print(f"\n📈 Total consolidado: {len(df_final)} registros ({df_final['fecha_fin_semana'].min()} a {df_final['fecha_fin_semana'].max()})")

    return df_final, df_regiones


# --- 3. FUNCIÓN DE CARGA A BASE DE DATOS (MySQL) ---

def load_to_db(df_final, df_regiones):
    """Conecta a MySQL e inserta los datos procesados."""
    cnx = None
    try:
        cnx = get_db_connection()
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

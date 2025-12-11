# ----------------------------------------------------------------------
# TRANSFORM_CLEAN_CSV.PY: Transforma CSVs limpios (2000-2020) manualmente
# creados al formato compatible con ETL_LOADER.py
# ----------------------------------------------------------------------

import pandas as pd
import numpy as np
import os
from datetime import datetime
from calendar import monthrange

# Directorios
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)  # ProeVira/
SOURCE_DIR = os.path.join(PROJECT_DIR, 'csv')  # CSVs limpios en ProeVira/csv/
OUTPUT_DIR = os.path.join(PROJECT_DIR, 'data')

print(f"📂 Directorio fuente (CSVs limpios): {SOURCE_DIR}")
print(f"📂 Directorio destino: {OUTPUT_DIR}")

# Mapeo de nombres de estado a códigos INEGI (1-32)
ESTADO_A_INEGI = {
    'aguascalientes': 1, 'baja california': 2, 'baja california sur': 3,
    'campeche': 4, 'coahuila': 5, 'coahuila de zaragoza': 5, 'colima': 6,
    'chiapas': 7, 'chihuahua': 8, 'ciudad de mexico': 9, 'ciudad de méxico': 9,
    'distrito federal': 9, 'cdmx': 9, 'durango': 10, 'guanajuato': 11,
    'guerrero': 12, 'hidalgo': 13, 'jalisco': 14, 'mexico': 15, 'méxico': 15,
    'estado de mexico': 15, 'estado de méxico': 15, 'michoacan': 16,
    'michoacán': 16, 'michoacán de ocampo': 16, 'morelos': 17, 'nayarit': 18,
    'nuevo leon': 19, 'nuevo león': 19, 'oaxaca': 20, 'puebla': 21,
    'queretaro': 22, 'querétaro': 22, 'quintana roo': 23, 'san luis potosi': 24,
    'san luis potosí': 24, 'sinaloa': 25, 'sonora': 26, 'tabasco': 27,
    'tamaulipas': 28, 'tlaxcala': 29, 'veracruz': 30,
    'veracruz de ignacio de la llave': 30, 'yucatan': 31, 'yucatán': 31,
    'zacatecas': 32
}

# Población 2025 para cálculo de TI (promedio aproximado)
POBLACION = {
    1: 1512400, 2: 3968300, 3: 850700, 4: 1011800, 5: 3328500, 6: 775100,
    7: 6000100, 8: 3998500, 9: 9386700, 10: 1913400, 11: 6555200, 12: 3724300,
    13: 3327600, 14: 8847600, 15: 18016500, 16: 4975800, 17: 2056000, 18: 1294800,
    19: 6231200, 20: 4432900, 21: 6886400, 22: 2603300, 23: 1989500, 24: 2931400,
    25: 3274600, 26: 3154100, 27: 2601900, 28: 3682900, 29: 1421000, 30: 8871300,
    31: 2561900, 32: 1698200
}

# Meses en español
MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
MESES_NUM = {mes: i+1 for i, mes in enumerate(MESES)}


def get_last_day_of_month(year, month):
    """Obtiene el último día del mes."""
    _, last_day = monthrange(year, month)
    return datetime(year, month, last_day)


def clean_numeric(value):
    """Limpia y convierte un valor numérico."""
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    # Limpiar string
    s = str(value).strip()
    s = s.replace(' ', '').replace(',', '')
    try:
        return float(s)
    except:
        return 0


def get_estado_id(estado_name):
    """Obtiene el código INEGI de un estado."""
    if not estado_name or pd.isna(estado_name):
        return None
    
    # Limpiar nombre
    nombre = str(estado_name).strip().lower()
    # Quitar números y caracteres especiales al final
    nombre = ''.join(c for c in nombre if not c.isdigit()).strip()
    
    # Buscar en el mapeo
    if nombre in ESTADO_A_INEGI:
        return ESTADO_A_INEGI[nombre]
    
    # Buscar coincidencia parcial
    for key, value in ESTADO_A_INEGI.items():
        if key in nombre or nombre in key:
            return value
    
    return None


def process_csv(file_path, year):
    """Procesa un archivo CSV y retorna registros normalizados."""
    print(f"📄 Procesando: {os.path.basename(file_path)} (año {year})")
    
    try:
        # Intentar diferentes encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            print(f"   ❌ Error de encoding")
            return []
    except Exception as e:
        print(f"   ❌ Error leyendo archivo: {e}")
        return []
    
    # Normalizar columnas
    df.columns = [str(c).strip() for c in df.columns]
    
    # Detectar columnas de meses
    mes_cols = {}
    for col in df.columns:
        col_lower = col.lower()
        for mes, num in MESES_NUM.items():
            if mes.lower() in col_lower:
                mes_cols[num] = col
                break
    
    # Detectar columna Estado
    estado_col = None
    for col in df.columns:
        if 'estado' in col.lower():
            estado_col = col
            break
    
    if not estado_col:
        estado_col = df.columns[0]
    
    records = []
    
    for _, row in df.iterrows():
        estado = row[estado_col]
        id_region = get_estado_id(estado)
        
        if not id_region:
            continue
        
        # Ignorar filas de totales
        if str(estado).lower().startswith('total'):
            continue
        
        poblacion = POBLACION.get(id_region, 1000000)
        
        # Procesar cada mes - GENERAR 4 SEMANAS POR MES
        for mes_num, col_name in mes_cols.items():
            casos_mes = clean_numeric(row.get(col_name, 0))
            
            if casos_mes <= 0:
                continue
            
            # Validar: máximo 50,000 casos por mes
            if casos_mes > 50000:
                print(f"   ⚠️  Valor alto ignorado: {estado} {year}-{mes_num:02d} = {casos_mes:,.0f}")
                continue
            
            # Dividir casos mensuales en 4 semanas (distribución uniforme)
            casos_por_semana = casos_mes / 4.0
            
            # Generar 4 registros semanales por mes
            for semana in range(4):
                # Calcular fecha de fin de semana (aproximado)
                # Semana 1: día 7, Semana 2: día 14, Semana 3: día 21, Semana 4: último día del mes
                if semana < 3:
                    dia = 7 * (semana + 1)
                    fecha = datetime(year, mes_num, dia)
                else:
                    fecha = get_last_day_of_month(year, mes_num)
                
                # Redondear casos (puede variar ligeramente por semana)
                if semana < 3:
                    casos_semana = int(round(casos_por_semana))
                else:
                    # Última semana toma el resto para que sumen el total mensual
                    casos_semana = int(casos_mes - (int(round(casos_por_semana)) * 3))
                
                tasa_incidencia = min((casos_semana / poblacion) * 100000, 1000.0)
                riesgo = 1 if tasa_incidencia > 5 else 0
                
                records.append({
                    'id_enfermedad': 1,
                    'id_region': id_region,
                    'fecha_fin_semana': fecha,
                    'casos_confirmados': casos_semana,
                    'defunciones': 0,
                    'tasa_incidencia': round(tasa_incidencia, 4),
                    'riesgo_brote_target': riesgo
                })
    
    print(f"   ✅ {len(records)} registros extraídos")
    return records


def transform_all(start_year=2000, end_year=2020):
    """Transforma todos los CSVs limpios."""
    print("\n" + "="*70)
    print("🔄 TRANSFORMACIÓN DE CSVs LIMPIOS (2000-2020)")
    print("="*70 + "\n")
    
    all_records = []
    years_processed = []
    
    for year in range(start_year, end_year + 1):
        file_path = os.path.join(SOURCE_DIR, f'dengue_{year}.csv')
        
        if not os.path.exists(file_path):
            print(f"⚠️  Archivo no encontrado: dengue_{year}.csv")
            continue
        
        records = process_csv(file_path, year)
        if records:
            all_records.extend(records)
            years_processed.append(year)
    
    if not all_records:
        print("\n❌ No se procesaron registros.")
        return None
    
    # Crear DataFrame
    df = pd.DataFrame(all_records)
    df = df.sort_values(['fecha_fin_semana', 'id_region'])
    df['fecha_carga'] = datetime.now().strftime('%Y-%m-%d')
    
    # Guardar
    output_file = os.path.join(OUTPUT_DIR, 'dengue_historico_2000_2020.csv')
    df.to_csv(output_file, index=False)
    
    print("\n" + "="*70)
    print("📊 RESUMEN")
    print("="*70)
    print(f"Años procesados: {len(years_processed)} ({min(years_processed)}-{max(years_processed)})")
    print(f"Total de registros: {len(df)}")
    print(f"Casos totales: {df['casos_confirmados'].sum():,.0f}")
    print(f"Archivo generado: {output_file}")
    print("="*70)
    
    return df


if __name__ == "__main__":
    df = transform_all(start_year=2000, end_year=2020)
    
    if df is not None:
        print("\n✅ TRANSFORMACIÓN COMPLETADA")
        print("\n📋 Próximos pasos:")
        print("   1. Actualizar ETL_LOADER.py para usar el nuevo archivo")
        print("   2. Ejecutar: python backend/ETL_LOADER.py")
        print("   3. Re-entrenar el modelo")

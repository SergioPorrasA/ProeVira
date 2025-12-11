# ----------------------------------------------------------------------
# TRANSFORM_HISTORICAL_CSV.PY: Transforma CSVs históricos (2000-2019) 
# al formato compatible con ETL_LOADER.py
# ----------------------------------------------------------------------
# Los CSVs históricos tienen formato agregado por mes:
#   Estado,Tasa,Total,Ene,Feb,Mar,Abr,May,Jun,Jul,Ago,Sep,Oct,Nov,Dic
# 
# Este script los convierte al formato de serie de tiempo que usa el modelo:
#   id_enfermedad,id_region,fecha_fin_semana,casos_confirmados,...
# ----------------------------------------------------------------------

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from calendar import monthrange

# Obtener directorios
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)  # ProeVira/
SOURCE_DIR = os.path.join(os.path.dirname(PROJECT_DIR), 'Conversor_PDF_CSV', 'csv')
OUTPUT_DIR = os.path.join(PROJECT_DIR, 'data')

print(f"📂 Directorio fuente (CSVs históricos): {SOURCE_DIR}")
print(f"📂 Directorio destino (datos modelo): {OUTPUT_DIR}")

# Mapeo de nombres de estado a códigos INEGI (1-32)
ESTADO_A_INEGI = {
    'Aguascalientes': 1,
    'Baja California': 2,
    'Baja California Sur': 3,
    'Campeche': 4,
    'Coahuila': 5,
    'Coahuila de Zaragoza': 5,
    'Colima': 6,
    'Chiapas': 7,
    'Chihuahua': 8,
    'Distrito Federal': 9,
    'Ciudad de México': 9,
    'Durango': 10,
    'Guanajuato': 11,
    'Guerrero': 12,
    'Guerrero 1': 12,  # Variante encontrada en algunos años
    'Hidalgo': 13,
    'Jalisco': 14,
    'México': 15,
    'Michoacán': 16,
    'Michoacán de Ocampo': 16,
    'Morelos': 17,
    'Nayarit': 18,
    'Nuevo León': 19,
    'Oaxaca': 20,
    'Puebla': 21,
    'Queretaro': 22,
    'Querétaro': 22,
    'Quintana Roo': 23,
    'San Luis Potosi': 24,
    'San Luis Potosí': 24,
    'Sinaloa': 25,
    'Sonora': 26,
    'Tabasco': 27,
    'Tamaulipas': 28,
    'Tlaxcala': 29,
    'Veracruz': 30,
    'Veracruz de Ignacio de la Llave': 30,
    'Yucatán': 31,
    'Zacatecas': 32
}

# Población histórica aproximada por estado (promedio para cálculo de TI)
# Usamos datos aproximados de INEGI/CONAPO para el período 2000-2019
POBLACION_HISTORICA = {
    1: 1100000, 2: 2800000, 3: 550000, 4: 750000, 5: 2600000, 6: 600000,
    7: 4500000, 8: 3300000, 9: 8800000, 10: 1500000, 11: 5000000, 12: 3200000,
    13: 2500000, 14: 6800000, 15: 14000000, 16: 4200000, 17: 1700000, 18: 950000,
    19: 4300000, 20: 3500000, 21: 5400000, 22: 1700000, 23: 1200000, 24: 2400000,
    25: 2700000, 26: 2500000, 27: 2000000, 28: 3000000, 29: 1050000, 30: 7200000,
    31: 1900000, 32: 1400000
}

# Nombres de meses en español (como aparecen en los CSVs)
MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def get_last_day_of_month(year, month):
    """Obtiene el último día del mes para usar como fecha_fin_semana."""
    _, last_day = monthrange(year, month)
    return datetime(year, month, last_day)


def clean_numeric_value(value):
    """Limpia y convierte valores numéricos, manejando casos especiales."""
    if pd.isna(value):
        return 0
    if isinstance(value, str):
        # Remover caracteres no numéricos excepto punto y coma
        value = value.replace(',', '.').strip()
        try:
            return float(value)
        except ValueError:
            return 0
    return float(value) if value else 0


def transform_year(year, source_dir):
    """Transforma un archivo CSV de un año específico."""
    file_path = os.path.join(source_dir, f'dengue_{year}.csv')
    
    if not os.path.exists(file_path):
        print(f"⚠️  Archivo no encontrado: dengue_{year}.csv")
        return None
    
    try:
        df = pd.read_csv(file_path)
        print(f"📄 Procesando dengue_{year}.csv ({len(df)} filas)")
    except Exception as e:
        print(f"❌ Error leyendo dengue_{year}.csv: {e}")
        return None
    
    records = []
    
    for _, row in df.iterrows():
        estado = str(row.get('Estado', '')).strip()
        
        # Ignorar filas de totales, notas o vacías
        if not estado or estado.upper().startswith('TOTAL') or estado.upper().startswith('FUENTE'):
            continue
        if 'Tasa*' in estado or 'habitantes' in estado.lower():
            continue
        
        # Buscar código INEGI
        id_region = None
        for nombre, codigo in ESTADO_A_INEGI.items():
            if nombre.lower() in estado.lower() or estado.lower() in nombre.lower():
                id_region = codigo
                break
        
        if id_region is None:
            # Intentar match exacto
            id_region = ESTADO_A_INEGI.get(estado)
        
        if id_region is None:
            print(f"   ⚠️  Estado no reconocido: '{estado}' (año {year})")
            continue
        
        # Obtener población para el estado
        poblacion = POBLACION_HISTORICA.get(id_region, 1000000)
        
        # Procesar cada mes
        for mes_idx, mes_nombre in enumerate(MESES, 1):
            casos = clean_numeric_value(row.get(mes_nombre, 0))
            
            if casos <= 0:
                continue
            
            # VALIDACIÓN: Rechazar valores absurdamente altos (errores de parsing del PDF)
            # El máximo histórico razonable es ~50,000 casos por mes por estado
            if casos > 50000:
                print(f"   ⚠️  Valor sospechoso ignorado: {estado} {year}-{mes_idx:02d} = {casos:,.0f} casos")
                continue
            
            # Calcular fecha del último día del mes
            fecha = get_last_day_of_month(year, mes_idx)
            
            # Calcular tasa de incidencia (por 100,000 habitantes)
            tasa_incidencia = (casos / poblacion) * 100000
            
            # Limitar tasa máxima a un valor razonable (1000 por 100,000 = 1% de población)
            if tasa_incidencia > 1000:
                tasa_incidencia = 1000.0
            
            # Determinar riesgo de brote (umbral: tasa > 5 por 100,000)
            # Este umbral es conservador para datos históricos
            riesgo_brote = 1 if tasa_incidencia > 5 else 0
            
            records.append({
                'id_enfermedad': 1,  # Dengue
                'id_region': id_region,
                'fecha_fin_semana': fecha,
                'casos_confirmados': int(casos),
                'defunciones': 0,
                'tasa_incidencia': round(tasa_incidencia, 4),
                'riesgo_brote_target': riesgo_brote
            })
    
    if records:
        return pd.DataFrame(records)
    return None


def transform_all_historical(start_year=2000, end_year=2019):
    """
    Transforma todos los CSVs históricos de un rango de años.
    Por defecto procesa 2000-2019 (los años que no están en data/).
    """
    print("\n" + "="*70)
    print("🔄 TRANSFORMACIÓN DE DATOS HISTÓRICOS DE DENGUE")
    print("="*70)
    print(f"Rango de años: {start_year} - {end_year}")
    print(f"Fuente: {SOURCE_DIR}")
    print(f"Destino: {OUTPUT_DIR}")
    print("="*70 + "\n")
    
    all_dataframes = []
    years_processed = []
    
    for year in range(start_year, end_year + 1):
        df_year = transform_year(year, SOURCE_DIR)
        if df_year is not None and len(df_year) > 0:
            all_dataframes.append(df_year)
            years_processed.append(year)
            print(f"   ✅ {year}: {len(df_year)} registros transformados")
    
    if not all_dataframes:
        print("\n❌ No se pudo procesar ningún archivo histórico.")
        return None
    
    # Consolidar todos los años
    df_consolidated = pd.concat(all_dataframes, ignore_index=True)
    
    # Ordenar por fecha y región
    df_consolidated = df_consolidated.sort_values(['fecha_fin_semana', 'id_region'])
    
    # Agregar columna de fecha de carga
    df_consolidated['fecha_carga'] = datetime.now().strftime('%Y-%m-%d')
    
    # Guardar archivo consolidado
    output_file = os.path.join(OUTPUT_DIR, 'dengue_historico_2000_2019.csv')
    df_consolidated.to_csv(output_file, index=False)
    
    print("\n" + "="*70)
    print("📊 RESUMEN DE TRANSFORMACIÓN")
    print("="*70)
    print(f"Años procesados: {len(years_processed)} ({min(years_processed)}-{max(years_processed)})")
    print(f"Total de registros: {len(df_consolidated)}")
    print(f"Casos confirmados totales: {df_consolidated['casos_confirmados'].sum():,.0f}")
    print(f"Archivo generado: {output_file}")
    print("="*70)
    
    # Estadísticas por año
    print("\n📈 Estadísticas por año:")
    for year in years_processed:
        df_year = df_consolidated[df_consolidated['fecha_fin_semana'].dt.year == year]
        casos = df_year['casos_confirmados'].sum()
        print(f"   {year}: {casos:>8,.0f} casos")
    
    return df_consolidated


def validate_output():
    """Valida que el archivo de salida sea compatible con ETL_LOADER."""
    output_file = os.path.join(OUTPUT_DIR, 'dengue_historico_2000_2019.csv')
    
    if not os.path.exists(output_file):
        print("❌ Archivo de salida no encontrado.")
        return False
    
    df = pd.read_csv(output_file)
    
    required_columns = [
        'id_enfermedad', 'id_region', 'fecha_fin_semana',
        'casos_confirmados', 'defunciones', 'tasa_incidencia',
        'riesgo_brote_target'
    ]
    
    missing = [col for col in required_columns if col not in df.columns]
    
    if missing:
        print(f"❌ Columnas faltantes: {missing}")
        return False
    
    print("\n✅ Validación exitosa: El archivo es compatible con ETL_LOADER.py")
    print(f"   - Columnas: {list(df.columns)}")
    print(f"   - Registros: {len(df)}")
    print(f"   - Rango de fechas: {df['fecha_fin_semana'].min()} a {df['fecha_fin_semana'].max()}")
    
    return True


if __name__ == "__main__":
    # Ejecutar transformación
    df_result = transform_all_historical(start_year=2000, end_year=2019)
    
    if df_result is not None:
        # Validar resultado
        validate_output()
        
        print("\n" + "="*70)
        print("✅ TRANSFORMACIÓN COMPLETADA")
        print("="*70)
        print("\n📋 Próximos pasos:")
        print("   1. El archivo 'dengue_historico_2000_2019.csv' está en ProeVira/data/")
        print("   2. Ya está registrado en ETL_LOADER.py para cargarse automáticamente")
        print("   3. Ejecuta: python backend/ETL_LOADER.py")
        print("   4. Re-entrena el modelo con los nuevos datos")
        print("="*70)

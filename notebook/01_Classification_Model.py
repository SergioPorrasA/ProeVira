# ============================================
# Modelo de Clasificación para Predicción de Riesgo de Brote de Dengue
# Random Forest Classifier - Lee datos de MySQL
# ============================================

import pandas as pd
import numpy as np
import mysql.connector
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import sys
import os

# Agregar directorio backend al path para importar db_config
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, '..', 'backend')
sys.path.append(backend_dir)

from db_config import get_db_connection


print("=" * 60)
print("🔬 ENTRENAMIENTO DE MODELO DE CLASIFICACIÓN")
print("   Predicción de Riesgo de Brote de Dengue")
print("   Datos: 2000-2025 (26 años de historia)")
print("=" * 60)

# ============================================
# 1. CONEXIÓN A BASE DE DATOS
# ============================================
print("\n📊 Conectando a la base de datos MySQL...")

try:
    conn = get_db_connection()
    print("✅ Conexión exitosa")
except mysql.connector.Error as err:
    print(f"❌ Error de conexión: {err}")
    exit(1)

# Obtener datos epidemiológicos SOLO de 2021 en adelante (datos semanales reales)
query = """
SELECT 
    d.id_region,
    r.nombre as estado,
    r.poblacion,
    d.fecha_fin_semana,
    d.casos_confirmados,
    d.tasa_incidencia,
    d.riesgo_brote_target,
    WEEK(d.fecha_fin_semana) as semana_anio,
    MONTH(d.fecha_fin_semana) as mes,
    YEAR(d.fecha_fin_semana) as anio
FROM dato_epidemiologico d
JOIN region r ON d.id_region = r.id_region
WHERE YEAR(d.fecha_fin_semana) >= 2021
ORDER BY d.id_region, d.fecha_fin_semana
"""

df = pd.read_sql(query, conn)
conn.close()

print(f"✅ Datos cargados: {len(df)} registros")
print(f"   Estados: {df['estado'].nunique()}")
print(f"   Período: {df['fecha_fin_semana'].min()} a {df['fecha_fin_semana'].max()}")
print(f"   Años de datos: {df['anio'].nunique()}")

# Verificar distribución del target
print(f"\n📊 Distribución del Target (Riesgo de Brote):")
print(f"   Sin riesgo (0): {(df['riesgo_brote_target'] == 0).sum()} ({(df['riesgo_brote_target'] == 0).mean()*100:.1f}%)")
print(f"   Con riesgo (1): {(df['riesgo_brote_target'] == 1).sum()} ({(df['riesgo_brote_target'] == 1).mean()*100:.1f}%)")

# ============================================
# 2. INGENIERÍA DE FEATURES
# ============================================
print("\n🔧 Creando features para clasificación...")

# Ordenar por estado y fecha
df = df.sort_values(['id_region', 'fecha_fin_semana']).reset_index(drop=True)

# Crear features de lag (semanas anteriores)
for lag in [1, 2, 3, 4]:
    df[f'casos_lag_{lag}w'] = df.groupby('id_region')['casos_confirmados'].shift(lag)
    df[f'ti_lag_{lag}w'] = df.groupby('id_region')['tasa_incidencia'].shift(lag)

# Promedio móvil de 4 semanas
df['casos_promedio_4w'] = df.groupby('id_region')['casos_confirmados'].transform(
    lambda x: x.rolling(window=4, min_periods=1).mean().shift(1)
)

# Tendencia (diferencia entre semana actual y hace 4 semanas)
df['tendencia_4w'] = df['casos_lag_1w'] - df['casos_lag_4w']

# Variación porcentual
df['variacion_pct'] = df.groupby('id_region')['casos_confirmados'].pct_change().shift(1)
df['variacion_pct'] = df['variacion_pct'].replace([np.inf, -np.inf], 0).fillna(0)

# Codificar estado
le = LabelEncoder()
df['estado_coded'] = le.fit_transform(df['estado'])

# Guardar encoder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
encoder_path = os.path.join(SCRIPT_DIR, '..', 'backend', 'label_encoder.pkl')
joblib.dump(le, encoder_path)
print(f"✅ Label encoder guardado")

# Eliminar filas con NaN (primeras semanas sin lag)
df_clean = df.dropna()
print(f"✅ Registros para entrenamiento: {len(df_clean)}")

# ============================================
# 3. PREPARAR DATOS PARA ENTRENAMIENTO
# ============================================
print("\n📐 Preparando datos de entrenamiento...")

# Features para el modelo
feature_cols = [
    'casos_lag_1w', 'casos_lag_2w', 'casos_lag_3w', 'casos_lag_4w',
    'ti_lag_1w', 'ti_lag_2w', 'ti_lag_3w', 'ti_lag_4w',
    'casos_promedio_4w', 'tendencia_4w', 'variacion_pct',
    'semana_anio', 'mes',
    'estado_coded'
]

X = df_clean[feature_cols]
y = df_clean['riesgo_brote_target']  # Target: 0 o 1

print(f"   Features: {len(feature_cols)}")
print(f"   Samples: {len(X)}")

# Split train/test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"   Train: {len(X_train)}, Test: {len(X_test)}")
print(f"   Balance Train - Sin riesgo: {(y_train == 0).sum()}, Con riesgo: {(y_train == 1).sum()}")

# ============================================
# 4. ENTRENAR MODELO RANDOM FOREST CLASSIFIER
# ============================================
print("\n🚀 Entrenando Random Forest Classifier...")

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    class_weight='balanced',  # Importante para datos desbalanceados
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)
print("✅ Modelo entrenado")

# ============================================
# 5. EVALUAR MODELO
# ============================================
print("\n📊 Evaluando modelo...")

# Predicciones en test
y_pred = model.predict(X_test)

# Métricas
accuracy = accuracy_score(y_test, y_pred)

print("\n" + "=" * 50)
print("📈 MÉTRICAS DEL MODELO DE CLASIFICACIÓN")
print("=" * 50)
print(f"   Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
print("\n   Reporte de Clasificación:")
print(classification_report(y_test, y_pred, target_names=['Sin Riesgo (0)', 'Con Riesgo (1)']))

# Matriz de confusión
cm = confusion_matrix(y_test, y_pred)
print("   Matriz de Confusión:")
print(f"                 Predicho")
print(f"               0      1")
print(f"   Real 0   {cm[0,0]:5d}  {cm[0,1]:5d}")
print(f"   Real 1   {cm[1,0]:5d}  {cm[1,1]:5d}")
print("=" * 50)

# Cross-validation
cv_scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
print(f"\n   Cross-Validation Accuracy (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# Feature importance
print("\n📊 Importancia de Features:")
importances = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for _, row in importances.iterrows():
    bar = '█' * int(row['importance'] * 50)
    print(f"   {row['feature']:20s} {row['importance']:.3f} {bar}")

# ============================================
# 6. GUARDAR MODELO
# ============================================
print("\n💾 Guardando modelo...")

model_path = os.path.join(SCRIPT_DIR, '..', 'backend', 'model.pkl')
joblib.dump(model, model_path)

# Guardar también las columnas de features
features_path = os.path.join(SCRIPT_DIR, '..', 'backend', 'classifier_features.pkl')
joblib.dump(feature_cols, features_path)

print(f"✅ Modelo guardado en: {model_path}")
print(f"✅ Features guardadas en: {features_path}")

# ============================================
# 7. PRUEBA RÁPIDA
# ============================================
print("\n🧪 Prueba rápida con datos recientes...")

# Tomar últimos registros de diferentes estados para prueba
estados_prueba = ['Guerrero', 'Veracruz de Ignacio de la Llave', 'Jalisco']

for estado in estados_prueba:
    test_samples = df_clean[df_clean['estado'] == estado].tail(3)
    
    if len(test_samples) == 0:
        continue
        
    print(f"\n   {estado}:")
    for idx, row in test_samples.iterrows():
        X_sample = row[feature_cols].values.reshape(1, -1)
        pred = model.predict(X_sample)[0]
        pred_proba = model.predict_proba(X_sample)[0]
        real = row['riesgo_brote_target']
        
        estado_pred = "✅ CORRECTO" if pred == real else "❌ ERROR"
        riesgo_texto = "RIESGO" if pred == 1 else "Sin riesgo"
        
        print(f"      {row['fecha_fin_semana']}: Pred={riesgo_texto} (prob={pred_proba[1]:.2f}), Real={real} {estado_pred}")

print("\n" + "=" * 60)
print("✅ MODELO DE CLASIFICACIÓN ENTRENADO EXITOSAMENTE")
print("   Ahora el sistema puede predecir riesgo de brote")
print("   usando 26 años de datos históricos (2000-2025)")
print("=" * 60)

# ============================================
# Modelo de Regresión para Predicción de Casos de Dengue
# Random Forest Regressor
# ============================================

import pandas as pd
import numpy as np
import mysql.connector
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os

print("=" * 60)
print("🔬 ENTRENAMIENTO DE MODELO DE REGRESIÓN")
print("   Predicción de Cantidad de Casos de Dengue")
print("=" * 60)

# ============================================
# 1. CONEXIÓN A BASE DE DATOS
# ============================================
print("\n📊 Conectando a la base de datos...")

conn = mysql.connector.connect(
    host='127.0.0.1',
    user='root',
    password='admin',
    database='proyecto_integrador'
)

# Obtener todos los datos epidemiológicos
query = """
SELECT 
    d.id_region,
    r.nombre as estado,
    r.poblacion,
    d.fecha_fin_semana,
    d.casos_confirmados,
    d.tasa_incidencia,
    WEEK(d.fecha_fin_semana) as semana_anio,
    MONTH(d.fecha_fin_semana) as mes,
    YEAR(d.fecha_fin_semana) as anio
FROM dato_epidemiologico d
JOIN region r ON d.id_region = r.id_region
ORDER BY d.id_region, d.fecha_fin_semana
"""

df = pd.read_sql(query, conn)
conn.close()

print(f"✅ Datos cargados: {len(df)} registros")
print(f"   Estados: {df['estado'].nunique()}")
print(f"   Período: {df['fecha_fin_semana'].min()} a {df['fecha_fin_semana'].max()}")

# ============================================
# 2. INGENIERÍA DE FEATURES
# ============================================
print("\n🔧 Creando features para regresión...")

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
encoder_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'label_encoder_regressor.pkl')
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
    'ti_lag_1w', 'ti_lag_2w',
    'casos_promedio_4w', 'tendencia_4w',
    'semana_anio', 'mes',
    'estado_coded'
]

X = df_clean[feature_cols]
y = df_clean['casos_confirmados']  # Target: casos reales de esa semana

print(f"   Features: {len(feature_cols)}")
print(f"   Samples: {len(X)}")

# Split train/test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"   Train: {len(X_train)}, Test: {len(X_test)}")

# ============================================
# 4. ENTRENAR MODELO RANDOM FOREST REGRESSOR
# ============================================
print("\n🚀 Entrenando Random Forest Regressor...")

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
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
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

# MAPE (evitando división por cero)
mask = y_test > 0
mape = np.mean(np.abs((y_test[mask] - y_pred[mask]) / y_test[mask])) * 100

print("\n" + "=" * 50)
print("📈 MÉTRICAS DEL MODELO DE REGRESIÓN")
print("=" * 50)
print(f"   MAE  (Error Absoluto Medio): {mae:.2f} casos")
print(f"   RMSE (Raíz Error Cuadrático): {rmse:.2f} casos")
print(f"   MAPE (Error Porcentual Medio): {mape:.1f}%")
print(f"   R²   (Coeficiente Determinación): {r2:.4f} ({r2*100:.1f}%)")
print(f"   Precisión estimada: {100 - mape:.1f}%")
print("=" * 50)

# Cross-validation
cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
print(f"\n   Cross-Validation R² (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

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

model_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'model_regressor.pkl')
joblib.dump(model, model_path)

# Guardar también las columnas de features
features_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'regressor_features.pkl')
joblib.dump(feature_cols, features_path)

print(f"✅ Modelo guardado en: {model_path}")
print(f"✅ Features guardadas en: {features_path}")

# ============================================
# 7. PRUEBA RÁPIDA
# ============================================
print("\n🧪 Prueba rápida con datos recientes...")

# Tomar últimos registros de Guerrero para prueba
test_samples = df_clean[df_clean['estado'] == 'Guerrero'].tail(5)

for idx, row in test_samples.iterrows():
    X_sample = row[feature_cols].values.reshape(1, -1)
    pred = model.predict(X_sample)[0]
    real = row['casos_confirmados']
    error = abs(pred - real)
    error_pct = (error / real * 100) if real > 0 else 0
    
    print(f"   {row['fecha_fin_semana']}: Predicho={pred:.0f}, Real={real}, Error={error_pct:.1f}%")

print("\n" + "=" * 60)
print("✅ MODELO DE REGRESIÓN ENTRENADO EXITOSAMENTE")
print("   Ahora el sistema puede predecir cantidad de casos")
print("=" * 60)

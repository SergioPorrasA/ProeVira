import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# ============================================
# Configuracion de rutas
# ============================================
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "Conversor_PDF_CSV" / "dengue_master_dataset.csv"
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"


def temporal_split(df, feature_cols, target_col, region_col="id_region", date_col="fecha", test_size=0.2):
    """Split temporal por estado (evita usar semanas futuras en train)."""
    train_parts, test_parts = [], []
    for _, g in df.groupby(region_col):
        g_sorted = g.sort_values(date_col)
        if len(g_sorted) < 5:
            continue
        split_idx = int(len(g_sorted) * (1 - test_size))
        split_idx = max(1, min(split_idx, len(g_sorted) - 1))
        train_parts.append(g_sorted.iloc[:split_idx])
        test_parts.append(g_sorted.iloc[split_idx:])

    if not train_parts or not test_parts:
        raise ValueError("No hay suficientes datos para dividir train/test de manera temporal.")

    train_df = pd.concat(train_parts)
    test_df = pd.concat(test_parts)
    return (
        train_df[feature_cols],
        test_df[feature_cols],
        train_df[target_col],
        test_df[target_col],
    )


def main():
    print("=" * 60)
    print("ENTRENAMIENTO MODELO DE REGRESION (CSV consolidado)")
    print("Fuentes: dengue_master_dataset.csv (semanal por estado)")
    print("=" * 60)

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"No se encontro el CSV consolidado en {DATA_PATH}")

    # --------------------------------------------
    # 1. Cargar datos
    # --------------------------------------------
    df = pd.read_csv(DATA_PATH, parse_dates=["fecha"])
    df = df.rename(columns={"casos": "casos_confirmados", "id_estado": "id_region"})
    extras = sorted(set(df["id_region"].unique()) - set(range(1, 33)))
    if extras:
        print(f"[WARN] Se encontraron codigos de estado fuera de 1-32: {extras}. Se excluiran.")
        df = df[df["id_region"].between(1, 32)]
    df = df.sort_values(["id_region", "fecha"]).reset_index(drop=True)

    print(f"Registros: {len(df)}, Estados: {df['id_region'].nunique()}")
    print(f"Periodo: {df['fecha'].min().date()} -> {df['fecha'].max().date()}")

    # --------------------------------------------
    # 2. Ingenieria de features
    # --------------------------------------------
    for lag in [1, 2, 3, 4]:
        df[f"casos_lag_{lag}w"] = df.groupby("id_region")["casos_confirmados"].shift(lag)

    df["casos_promedio_4w"] = (
        df.groupby("id_region")["casos_confirmados"]
        .transform(lambda x: x.rolling(window=4, min_periods=1).mean().shift(1))
    )
    df["tendencia_4w"] = df["casos_lag_1w"] - df["casos_lag_4w"]
    df["semana_anio"] = df["fecha"].dt.isocalendar().week.astype(int)
    df["mes"] = df["fecha"].dt.month

    # Dummy de tasas para mantener compatibilidad de features con el backend
    df["ti_lag_1w"] = 0.0
    df["ti_lag_2w"] = 0.0

    # Codificar estado
    le = LabelEncoder()
    df["estado_coded"] = le.fit_transform(df["id_region"])
    encoder_path = BACKEND_DIR / "label_encoder_regressor.pkl"
    joblib.dump(le, encoder_path)
    print(f"LabelEncoder guardado en {encoder_path}")

    feature_cols = [
        "casos_lag_1w",
        "casos_lag_2w",
        "casos_lag_3w",
        "casos_lag_4w",
        "ti_lag_1w",
        "ti_lag_2w",
        "casos_promedio_4w",
        "tendencia_4w",
        "semana_anio",
        "mes",
        "estado_coded",
    ]

    df_clean = df.dropna(subset=feature_cols + ["casos_confirmados"])
    print(f"Registros despues de limpiar NaN: {len(df_clean)}")

    if df_clean["casos_confirmados"].sum() == 0:
        raise ValueError("No hay casos distintos de cero en el dataset consolidado; revisar dengue_master_dataset.csv antes de entrenar el regressor.")

    # --------------------------------------------
    # 3. Split temporal
    # --------------------------------------------
    X_train, X_test, y_train, y_test = temporal_split(
        df_clean, feature_cols, "casos_confirmados", region_col="id_region", date_col="fecha"
    )
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # --------------------------------------------
    # 4. Entrenar
    # --------------------------------------------
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    print("Modelo entrenado.")

    # --------------------------------------------
    # 5. Evaluar
    # --------------------------------------------
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print("\n" + "=" * 50)
    print("METRICAS (split temporal)")
    print("=" * 50)
    print(f"MAE : {mae:.2f}")
    print(f"RMSE: {rmse:.2f}")
    print(f"R2  : {r2:.4f} ({r2*100:.1f}%)")

    # --------------------------------------------
    # 6. Guardar modelo y features
    # --------------------------------------------
    model_path = BACKEND_DIR / "model_regressor.pkl"
    features_path = BACKEND_DIR / "regressor_features.pkl"
    joblib.dump(model, model_path)
    joblib.dump(feature_cols, features_path)
    print(f"Modelo guardado en {model_path}")
    print(f"Features guardadas en {features_path}")

    # --------------------------------------------
    # 7. Prueba rapida
    # --------------------------------------------
    print("\nPrueba rapida (ultimas filas por estado):")
    for estado, grupo in df_clean.groupby("id_region"):
        muestra = grupo.tail(1)
        X_sample = muestra[feature_cols]
        pred = model.predict(X_sample)[0]
        real = float(muestra["casos_confirmados"].iloc[0])
        print(f"Estado {estado}: pred={pred:.1f} real={real:.1f}")

    print("\n" + "=" * 60)
    print("Entrenamiento de regresion completado.")
    print("=" * 60)


if __name__ == "__main__":
    main()

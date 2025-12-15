import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# ============================================
# Configuracion de rutas
# ============================================
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "Conversor_PDF_CSV" / "dengue_master_dataset.csv"
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"


def temporal_split(df, feature_cols, target_col, region_col="id_region", date_col="fecha", test_size=0.2):
    """Divide en train/test respetando la serie temporal por estado para evitar fuga de futuro."""
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
    print("ENTRENAMIENTO MODELO DE CLASIFICACION (CSV consolidado)")
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
    df["variacion_pct"] = df.groupby("id_region")["casos_confirmados"].pct_change().shift(1)
    df["variacion_pct"] = df["variacion_pct"].replace([np.inf, -np.inf], 0).fillna(0)

    # Dummy de tasas (no estan en el CSV, pero se incluyen para compatibilidad de features)
    df["ti_lag_1w"] = 0.0
    df["ti_lag_2w"] = 0.0
    df["ti_lag_3w"] = 0.0
    df["ti_lag_4w"] = 0.0

    df["semana_anio"] = df["fecha"].dt.isocalendar().week.astype(int)
    df["mes"] = df["fecha"].dt.month

    # Target binario robusto por estado: requiere casos > 0 y evita estados monoclase
    def build_target(grp):
        series = grp["casos_confirmados"]
        if series.max() == 0:
            return pd.Series(0, index=grp.index)

        for q in [0.85, 0.70, 0.50]:
            thr = series.quantile(q)
            thr = max(thr, 1)
            y = ((series >= thr) & (series > 0)).astype(int)
            rate = y.mean()
            if y.nunique() == 2 and 0.05 <= rate <= 0.50:
                return y

        # Fallback: top 25% de semanas con casos > 0
        y = pd.Series(0, index=grp.index, dtype=int)
        positivos = series > 0
        if positivos.any():
            ranks = series[positivos].rank(pct=True)
            y.loc[positivos.index] = (ranks >= 0.75).astype(int)
        if y.nunique() < 2:
            # Si aun es monoclase, fuerza al menos un 0/1 usando el max
            idx_max = series.idxmax()
            y.loc[idx_max] = 1
            y.loc[series.idxmin()] = 0
        return y

    df["riesgo_brote_target"] = df.groupby("id_region", group_keys=False).apply(build_target)

    # Codificar estado
    le = LabelEncoder()
    df["estado_coded"] = le.fit_transform(df["id_region"])

    encoder_path = BACKEND_DIR / "label_encoder.pkl"
    joblib.dump(le, encoder_path)
    print(f"LabelEncoder guardado en {encoder_path}")

    feature_cols = [
        "casos_lag_1w",
        "casos_lag_2w",
        "casos_lag_3w",
        "casos_lag_4w",
        "ti_lag_1w",
        "ti_lag_2w",
        "ti_lag_3w",
        "ti_lag_4w",
        "casos_promedio_4w",
        "tendencia_4w",
        "variacion_pct",
        "semana_anio",
        "mes",
        "estado_coded",
    ]

    df_clean = df.dropna(subset=feature_cols + ["riesgo_brote_target"])
    print(f"Registros despues de limpiar NaN: {len(df_clean)}")

    # Validacion: evitar entrenar un modelo monoclase
    distrib = df_clean["riesgo_brote_target"].value_counts(normalize=True).sort_index()
    print("Distribucion de la clase objetivo:", distrib.to_dict())
    if df_clean["riesgo_brote_target"].nunique() < 2:
        raise ValueError("La clase objetivo quedo con un solo valor. Verifica que dengue_master_dataset.csv tenga casos distintos de cero.")

    # --------------------------------------------
    # 3. Split temporal
    # --------------------------------------------
    X_train, X_test, y_train, y_test = temporal_split(
        df_clean, feature_cols, "riesgo_brote_target", region_col="id_region", date_col="fecha"
    )
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # --------------------------------------------
    # 4. Entrenar
    # --------------------------------------------
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    print("Modelo entrenado.")

    # --------------------------------------------
    # 5. Evaluar
    # --------------------------------------------
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    labels_all = np.array([0, 1])
    labels_present = np.sort(df_clean["riesgo_brote_target"].unique())
    target_name_map = {0: "Sin riesgo", 1: "Con riesgo"}
    target_names = [target_name_map.get(lbl, str(lbl)) for lbl in labels_all]

    print("\n" + "=" * 50)
    print("METRICAS (split temporal)")
    print("=" * 50)
    print(f"Accuracy: {acc:.4f} ({acc*100:.1f}%)")
    print("\nDistribucion en test:")
    print(y_test.value_counts().sort_index())

    print("\nReporte de clasificacion:")
    print(classification_report(
        y_test,
        y_pred,
        labels=labels_all,
        target_names=target_names,
        zero_division=0,
    ))

    cm = confusion_matrix(y_test, y_pred, labels=labels_all)
    print("Matriz de confusion:")
    print(cm)

    # --------------------------------------------
    # 6. Guardar modelo y features
    # --------------------------------------------
    model_path = BACKEND_DIR / "model.pkl"
    features_path = BACKEND_DIR / "classifier_features.pkl"
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
        if len(model.classes_) == 1:
            prob = 1.0 if model.classes_[0] == 1 else 0.0
        else:
            prob = model.predict_proba(X_sample)[0][1]
        print(f"Estado {estado}: pred={pred} prob_riesgo={prob:.2f}")

    print("\n" + "=" * 60)
    print("Entrenamiento de clasificador completado.")
    print("=" * 60)


if __name__ == "__main__":
    main()

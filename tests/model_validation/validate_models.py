#!/usr/bin/env python3
"""
4.6 Validación de modelos predictivos.
Valida el desempeño de los modelos Random Forest (clasificador y regresor) usando un dataset de referencia.
"""

import argparse
import json
import os
from pathlib import Path

from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    mean_squared_error,
    r2_score
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / 'backend'
DEFAULT_DATASET = REPO_ROOT / 'modelo' / 'datos_dengue.csv'


def population_stability_index(expected, actual, buckets=10):
    """Calcula el PSI para detectar deriva en una distribución."""
    def _distribution(values):
        quantiles = np.linspace(0, 1, buckets + 1)
        bins = np.unique(np.quantile(values, quantiles))
        bins[-1] += 1e-6
        hist, _ = np.histogram(values, bins=bins)
        dist = hist / hist.sum()
        return dist

    exp = _distribution(expected)
    act = _distribution(actual)
    psi = np.sum((act - exp) * np.log((act + 1e-8) / (exp + 1e-8)))
    return float(psi)


def load_dataset(path: Path, target_clf: str, target_reg: str):
    df = pd.read_csv(path)
    if target_clf not in df.columns:
        raise ValueError(f'Columna objetivo para clasificador "{target_clf}" no encontrada en {path}')
    if target_reg not in df.columns:
        raise ValueError(f'Columna objetivo para regresor "{target_reg}" no encontrada en {path}')
    return df


def evaluate_classifier(model, df, target_col):
    feature_names = getattr(model, 'feature_names_in_', None)
    if feature_names is None:
        raise ValueError('El modelo clasificador no expone feature_names_in_. Actualiza el entrenamiento con sklearn >=1.0')

    X = df[feature_names]
    y_true = df[target_col]
    y_pred = model.predict(X)
    metrics = {
        'accuracy': float(accuracy_score(y_true, y_pred)),
        'precision': float(precision_score(y_true, y_pred, zero_division=0)),
        'recall': float(recall_score(y_true, y_pred, zero_division=0)),
        'f1': float(f1_score(y_true, y_pred, zero_division=0))
    }

    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(X)[:, 1]
        metrics['roc_auc'] = float(roc_auc_score(y_true, proba))

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    metrics['confusion_matrix'] = {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)}

    return metrics


def evaluate_regressor(model, df, target_col, feature_path: Optional[Path] = None):
    if feature_path and feature_path.exists():
        features = joblib.load(feature_path)
    else:
        features = getattr(model, 'feature_names_in_', None)
    if features is None:
        raise ValueError('No hay lista de features para el regresor')

    X = df[features]
    y_true = df[target_col]
    y_pred = model.predict(X)

    rmse = mean_squared_error(y_true, y_pred, squared=False)
    metrics = {
        'rmse': float(rmse),
        'r2': float(r2_score(y_true, y_pred)),
        'mae': float(np.mean(np.abs(y_true - y_pred)))
    }
    return metrics


def main():
    parser = argparse.ArgumentParser(description='Validación de modelos predictivos ProeVira')
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET, help='Ruta al dataset CSV de validación')
    parser.add_argument('--target-clf', default='riesgo_brote', help='Columna objetivo para el clasificador')
    parser.add_argument('--target-reg', default='casos_semana_siguiente', help='Columna objetivo para el regresor')
    parser.add_argument('--baseline', type=Path, help='CSV de referencia para calcular PSI')
    args = parser.parse_args()

    dataset = load_dataset(args.dataset, args.target_clf, args.target_reg)

    clf_path = BACKEND_DIR / 'model.pkl'
    reg_path = BACKEND_DIR / 'model_regressor.pkl'
    reg_feat_path = BACKEND_DIR / 'regressor_features.pkl'

    if not clf_path.exists():
        raise FileNotFoundError(f'No se encontró el clasificador en {clf_path}')
    if not reg_path.exists():
        raise FileNotFoundError(f'No se encontró el regresor en {reg_path}')

    classifier = joblib.load(clf_path)
    regressor = joblib.load(reg_path)

    clf_metrics = evaluate_classifier(classifier, dataset, args.target_clf)
    reg_metrics = evaluate_regressor(regressor, dataset, args.target_reg, reg_feat_path)

    results = {
        'dataset': str(args.dataset),
        'classifier': clf_metrics,
        'regressor': reg_metrics
    };

    if args.baseline and args.baseline.exists():
        baseline_df = pd.read_csv(args.baseline)
        feature_names = classifier.feature_names_in_
        psi_scores = {}
        for feature in feature_names:
            if feature in baseline_df.columns:
                psi_scores[feature] = population_stability_index(
                    baseline_df[feature].values,
                    dataset[feature].values
                )
        results['psi'] = psi_scores

    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

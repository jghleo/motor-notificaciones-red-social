"""
train_model.py — Script de entrenamiento independiente del notebook
====================================================================
Alternativa al notebook para entrenar el modelo desde la terminal.
Útil para CI/CD o re-entrenamiento automatizado.

Uso:
    python train_model.py
    python train_model.py --data ../data/Dataset_Historico_Notificaciones_PowerBI.xlsx
    python train_model.py --synthetic --n 10000
"""

import argparse
import datetime
import os
import pathlib
import warnings

warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score,
    recall_score, roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

MODEL_OUTPUT = pathlib.Path(__file__).parent / "modelo_notificaciones_rf.pkl"
MAPA_TIPO    = {"like": 0, "comment": 1, "follow": 2, "mention": 3}
MAPA_ESTADO  = {"ENVIADO": 1, "LEIDO": 1, "PENDIENTE": 0, "FALLIDO": 0}


def cargar_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["interactuo"]            = df["estado"].map(MAPA_ESTADO).fillna(0).astype(int)
    df["tipo_cod"]              = df["tipo"].str.lower().map(MAPA_TIPO).fillna(0).astype(int)
    df["historico_ctr_usuario"] = (df["score_ia"] / 1000).clip(0.05, 0.95)
    df["dias_inactivo"]         = ((1 - df["historico_ctr_usuario"]) * 30).astype(int)
    # Extraer hora — soporta tanto datetime como serial numérico de Excel
    if pd.api.types.is_datetime64_any_dtype(df["creado_en"]):
        df["hora_del_dia"] = df["creado_en"].dt.hour
    else:
        df["hora_del_dia"] = ((df["creado_en"] % 1) * 24).round(0).astype(int) % 24
    return df[["tipo_cod", "historico_ctr_usuario", "dias_inactivo", "hora_del_dia", "interactuo"]]


def generar_sintetico(n: int) -> pd.DataFrame:
    tipo_cod   = np.random.choice([0, 1, 2, 3], size=n, p=[0.40, 0.30, 0.20, 0.10])
    ctr        = np.random.uniform(0.05, 0.95, size=n)
    dias       = np.random.randint(0, 30, size=n)
    hora       = np.random.randint(0, 24, size=n)
    log_odds   = ctr * 4.5 + (tipo_cod == 3) * 2.5 + (tipo_cod == 1) * 1.2 - dias * 0.12 - 2.0
    prob       = 1 / (1 + np.exp(-log_odds))
    interactuo = (prob > np.random.uniform(0, 1, n)).astype(int)
    return pd.DataFrame({
        "tipo_cod": tipo_cod, "historico_ctr_usuario": ctr.round(4),
        "dias_inactivo": dias, "hora_del_dia": hora, "interactuo": interactuo,
    })


def entrenar(df: pd.DataFrame) -> None:
    FEATURES = ["tipo_cod", "historico_ctr_usuario", "dias_inactivo", "hora_del_dia"]
    X, y     = df[FEATURES], df["interactuo"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )

    print(f"  Train: {len(X_train)} | Test: {len(X_test)}")

    modelo = RandomForestClassifier(
        n_estimators=200, max_depth=12, min_samples_leaf=5,
        class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1,
    )
    modelo.fit(X_train, y_train)

    y_pred = modelo.predict(X_test)
    y_prob = modelo.predict_proba(X_test)[:, 1]
    auc    = roc_auc_score(y_test, y_prob)

    cv     = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_auc = cross_val_score(modelo, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)

    print("\n" + "=" * 50)
    print("  MÉTRICAS DE ENTRENAMIENTO")
    print("=" * 50)
    print(f"  Accuracy  : {accuracy_score(y_test, y_pred):.4f}")
    print(f"  Precision : {precision_score(y_test, y_pred):.4f}")
    print(f"  Recall    : {recall_score(y_test, y_pred):.4f}")
    print(f"  F1-Score  : {f1_score(y_test, y_pred):.4f}")
    print(f"  ROC-AUC   : {auc:.4f}")
    print(f"  Gini      : {2*auc-1:.4f}")
    print(f"  CV AUC    : {cv_auc.mean():.4f} ± {cv_auc.std():.4f}")
    print("=" * 50)

    joblib.dump(modelo, MODEL_OUTPUT)
    print(f"\n✅ Modelo guardado en: {MODEL_OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",      type=str,  default=None, help="Ruta al Excel de Power BI")
    parser.add_argument("--synthetic", action="store_true",     help="Forzar dataset sintético")
    parser.add_argument("--n",         type=int,  default=5000, help="Muestras sintéticas (default 5000)")
    args = parser.parse_args()

    print("=" * 50)
    print("  ENTRENAMIENTO — Motor Notificaciones IA")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    if args.synthetic or args.data is None:
        print(f"\n  Generando dataset sintético ({args.n} registros)...")
        df = generar_sintetico(args.n)
    else:
        print(f"\n  Cargando dataset real: {args.data}")
        df = cargar_excel(args.data)

    entrenar(df)

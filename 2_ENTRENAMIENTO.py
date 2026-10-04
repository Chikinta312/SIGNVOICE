"""
SIGNVOICE — ENTRENAMIENTO V2
=============================

Modelo estático:
    Random Forest
    5 sensores Flex

La evaluación se realiza separando sesiones,
evitando que muestras consecutivas de una misma
captura aparezcan simultáneamente en entrenamiento
y prueba.
"""

import warnings
warnings.filterwarnings("ignore")

import os
import joblib
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

DATASET = "dataset_signvoice.csv"

RANDOM_STATE = 42

FLEX_COLS = [
    "Flex1",
    "Flex2",
    "Flex3",
    "Flex4",
    "Flex5"
]

MPU_COLS = [
    "AX",
    "AY",
    "AZ",
    "GX",
    "GY",
    "GZ"
]

ALL_COLS = FLEX_COLS + MPU_COLS

DINAMICAS = ["J", "Ñ", "Z"]

# ============================================================
# CARGAR DATASET
# ============================================================

print("\n" + "=" * 60)
print("SIGNVOICE — ENTRENAMIENTO")
print("=" * 60)

if not os.path.exists(DATASET):

    raise FileNotFoundError(
        f"No existe {DATASET}"
    )

df = pd.read_csv(DATASET)

print(
    f"\nTotal muestras: {len(df)}"
)

print(
    f"Columnas: {list(df.columns)}"
)

# ============================================================
# LIMPIEZA
# ============================================================

df = df.dropna()

for col in ALL_COLS:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

df = df.dropna()

# ============================================================
# INFORMACIÓN
# ============================================================

print("\nDistribución:")

for letra, cantidad in (
    df["Clase"]
    .value_counts()
    .sort_index()
    .items()
):

    print(
        f"  {letra}: {cantidad}"
    )

# ============================================================
# MODELO ESTÁTICO
# ============================================================

df_est = df[
    ~df["Clase"].isin(DINAMICAS)
].copy()

print("\n" + "=" * 60)
print("MODELO ESTÁTICO — RANDOM FOREST")
print("=" * 60)

X = df_est[FLEX_COLS]
y = df_est["Clase"]

# ============================================================
# SEPARAR SESIONES
# ============================================================

sesiones = sorted(
    df_est["Sesion"].unique()
)

print(
    f"\nSesiones disponibles: "
    f"{sesiones}"
)

# Última sesión como prueba
# Las restantes como entrenamiento

if len(sesiones) >= 2:

    sesion_test = sesiones[-1]

    train_mask = (
        df_est["Sesion"] != sesion_test
    )

    test_mask = (
        df_est["Sesion"] == sesion_test
    )

else:

    print(
        "\nAdvertencia: solo existe una sesión."
    )

    print(
        "Se utilizará división aleatoria."
    )

    train_mask = None
    test_mask = None

# ============================================================
# ENCODER
# ============================================================

encoder = LabelEncoder()

encoder.fit(y)

y_encoded = encoder.transform(y)

# ============================================================
# SPLIT
# ============================================================

if train_mask is not None:

    X_train = X[train_mask]
    X_test = X[test_mask]

    y_train = y_encoded[train_mask]
    y_test = y_encoded[test_mask]

else:

    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y_encoded,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=y_encoded
    )

# ============================================================
# SCALER
# ============================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(
    X_train
)

X_test_scaled = scaler.transform(
    X_test
)

# ============================================================
# RANDOM FOREST
# ============================================================

print(
    "\nEntrenando Random Forest..."
)

modelo = RandomForestClassifier(
    n_estimators=200,
    random_state=RANDOM_STATE,
    n_jobs=-1,
    class_weight="balanced"
)

modelo.fit(
    X_train_scaled,
    y_train
)

# ============================================================
# EVALUACIÓN
# ============================================================

pred = modelo.predict(
    X_test_scaled
)

accuracy = accuracy_score(
    y_test,
    pred
)

print(
    f"\nExactitud de prueba: "
    f"{accuracy * 100:.2f}%"
)

print("\nReporte:")

print(
    classification_report(
        y_test,
        pred,
        target_names=encoder.classes_,
        zero_division=0
    )
)

# ============================================================
# GUARDAR
# ============================================================

joblib.dump(
    modelo,
    "model_estatico.pkl"
)

joblib.dump(
    scaler,
    "scaler_estatico.pkl"
)

joblib.dump(
    encoder,
    "encoder_estatico.pkl"
)

print(
    "\nModelo estático guardado."
)

# ============================================================
# MODELO DINÁMICO
# ============================================================

df_din = df[
    df["Clase"].isin(DINAMICAS)
].copy()

if len(df_din) == 0:

    print(
        "\nNo existen letras dinámicas."
    )

    modelo_dinamico_disponible = False

else:

    print(
        "\nLetras dinámicas encontradas:"
    )

    print(
        df_din["Clase"]
        .value_counts()
    )

    print(
        "\nEl entrenamiento BiLSTM se realizará "
        "cuando existan secuencias suficientes."
    )

    # Aquí se deja preparado el dataset
    # para implementar el BiLSTM con ventanas
    # temporales reales.

    modelo_dinamico_disponible = False

# ============================================================
# METADATOS
# ============================================================

letras_estaticas = sorted(
    df_est["Clase"].unique()
)

letras_dinamicas = sorted(
    df_din["Clase"].unique()
)

metadata = {

    "letras_estaticas":
        letras_estaticas,

    "letras_dinamicas":
        letras_dinamicas,

    "letras_dinamicas_esperadas":
        DINAMICAS,

    "modelo_estatico_disponible":
        True,

    "modelo_dinamico_disponible":
        modelo_dinamico_disponible,

    "flex_columns":
        FLEX_COLS,

    "mpu_columns":
        MPU_COLS,

    "sensor_imu":
        "MPU6050",

    "frecuencia_muestreo":
        "aprox. 100 Hz",

    "random_state":
        RANDOM_STATE
}

joblib.dump(
    metadata,
    "signvoice_metadata.pkl"
)

print(
    "\nMetadatos guardados."
)

print("\n" + "=" * 60)
print("ENTRENAMIENTO COMPLETADO")
print("=" * 60)
"""
SIGNVOICE — PRUEBAS EN TIEMPO REAL V2
======================================

Reconocimiento de letras estáticas mediante
Random Forest + 5 sensores Flex.

Incluye:
    - filtro temporal de predicciones
    - confianza mínima
    - consenso
    - rechazo de predicciones ambiguas
    - síntesis de voz
"""

import warnings
warnings.filterwarnings("ignore")

import socket
import time
import os
import joblib
import numpy as np

from collections import Counter, deque


# ============================================================
# CONFIGURACIÓN
# ============================================================

ESP32_IP = "192.168.4.1"
ESP32_PORT = 8080

MODEL_PATH = "model_estatico.pkl"
SCALER_PATH = "scaler_estatico.pkl"
ENCODER_PATH = "encoder_estatico.pkl"
METADATA_PATH = "signvoice_metadata.pkl"

# ------------------------------------------------------------
# Parámetros de reconocimiento
# ------------------------------------------------------------

MIN_CONFIDENCE = 0.75

CONFIRM_FRAMES = 8

CONSENSUS_RATIO = 0.75

COOLDOWN_SECONDS = 1.5

# Diferencia mínima entre primera y segunda probabilidad
MIN_MARGIN = 0.15

FLEX_COLS = [
    "Flex1",
    "Flex2",
    "Flex3",
    "Flex4",
    "Flex5"
]


# ============================================================
# CARGAR MODELO
# ============================================================

def cargar():

    if not os.path.exists(
        MODEL_PATH
    ):

        raise FileNotFoundError(
            MODEL_PATH
        )

    modelo = joblib.load(
        MODEL_PATH
    )

    scaler = joblib.load(
        SCALER_PATH
    )

    encoder = joblib.load(
        ENCODER_PATH
    )

    metadata = joblib.load(
        METADATA_PATH
    )

    print("\n" + "=" * 55)
    print("SIGNVOICE — RECONOCIMIENTO EN TIEMPO REAL")
    print("=" * 55)

    letras = metadata.get(
        "letras_estaticas",
        []
    )

    print(
        f"\nLetras disponibles "
        f"({len(letras)}):"
    )

    print(
        "  " +
        ", ".join(letras)
    )

    return (
        modelo,
        scaler,
        encoder,
        metadata
    )


# ============================================================
# VOZ
# ============================================================

def inicializar_voz():

    try:

        import pyttsx3

        engine = pyttsx3.init()

        engine.setProperty(
            "rate",
            150
        )

        engine.setProperty(
            "volume",
            1.0
        )

        print(
            "\nSíntesis de voz activada."
        )

        return engine

    except Exception:

        print(
            "\nSíntesis de voz no disponible."
        )

        return None


def hablar(engine, texto):

    if engine is None:

        return

    try:

        engine.say(texto)
        engine.runAndWait()

    except Exception:

        pass


# ============================================================
# CONEXIÓN
# ============================================================

def conectar():

    print(
        f"\nConectando al ESP32 "
        f"{ESP32_IP}:{ESP32_PORT}..."
    )

    while True:

        try:

            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            sock.settimeout(5)

            sock.connect(
                (
                    ESP32_IP,
                    ESP32_PORT
                )
            )

            print(
                "Conectado correctamente."
            )

            return sock

        except Exception as e:

            print(
                f"Error: {e}"
            )

            print(
                "Reintentando..."
            )

            time.sleep(2)


# ============================================================
# LEER TCP
# ============================================================

def leer_linea(
    sock,
    buffer
):

    while b"\n" not in buffer:

        chunk = sock.recv(512)

        if not chunk:

            raise ConnectionError(
                "ESP32 desconectado."
            )

        buffer += chunk

    linea, _, resto = buffer.partition(
        b"\n"
    )

    return (
        linea.decode(
            errors="ignore"
        ).strip(),
        resto
    )


# ============================================================
# PARSEAR
# ============================================================

def parsear(linea):

    try:

        valores = [
            float(x)
            for x in linea.split(",")
        ]

        if len(valores) != 11:

            return None

        return valores

    except:

        return None


# ============================================================
# PREDICCIÓN
# ============================================================

def predecir(
    valores,
    modelo,
    scaler,
    encoder
):

    flex = np.array(
        valores[:5]
    ).reshape(
        1,
        -1
    )

    flex = scaler.transform(
        flex
    )

    probabilidades = (
        modelo.predict_proba(
            flex
        )[0]
    )

    indices = np.argsort(
        probabilidades
    )[::-1]

    indice_1 = indices[0]
    indice_2 = indices[1]

    prob_1 = probabilidades[
        indice_1
    ]

    prob_2 = probabilidades[
        indice_2
    ]

    margen = (
        prob_1 -
        prob_2
    )

    letra = encoder.inverse_transform(
        [indice_1]
    )[0]

    # --------------------------------------------------------
    # RECHAZAR PREDICCIÓN AMBIGUA
    # --------------------------------------------------------

    if prob_1 < MIN_CONFIDENCE:

        return (
            None,
            prob_1,
            margen
        )

    if margen < MIN_MARGIN:

        return (
            None,
            prob_1,
            margen
        )

    return (
        letra,
        prob_1,
        margen
    )


# ============================================================
# MOSTRAR
# ============================================================

def mostrar(
    letra,
    confianza,
    margen
):

    barra = "#" * int(
        confianza * 20
    )

    vacio = "-" * (
        20 -
        int(confianza * 20)
    )

    print(
        f"\n  +----------------------+"
    )

    print(
        f"  |      {letra:^5}           |"
    )

    print(
        f"  +----------------------+"
    )

    print(
        f"  Confianza: "
        f"[{barra}{vacio}] "
        f"{confianza * 100:.1f}%"
    )

    print(
        f"  Margen: "
        f"{margen * 100:.1f}%"
    )


# ============================================================
# RECONOCIMIENTO
# ============================================================

def reconocer(
    sock,
    modelo,
    scaler,
    encoder,
    engine
):

    buffer = b""

    historial = deque(
        maxlen=CONFIRM_FRAMES
    )

    ultima_letra = None

    ultimo_tiempo = 0

    frames = 0

    print("\n" + "=" * 55)

    print(
        "Realiza una seña con el guante."
    )

    print(
        "Presiona Ctrl+C para salir."
    )

    print("=" * 55)

    while True:

        try:

            linea, buffer = leer_linea(
                sock,
                buffer
            )

        except Exception:

            print(
                "\nConexión perdida."
            )

            sock.close()

            sock = conectar()

            buffer = b""

            historial.clear()

            continue

        valores = parsear(
            linea
        )

        if valores is None:

            continue

        frames += 1

        letra, confianza, margen = predecir(
            valores,
            modelo,
            scaler,
            encoder
        )

        # ----------------------------------------------------
        # SIN PREDICCIÓN
        # ----------------------------------------------------

        if letra is None:

            historial.clear()

            if frames % 20 == 0:

                print(
                    f"\rLeyendo... "
                    f"| SIN PREDICCIÓN "
                    f"| Confianza: "
                    f"{confianza * 100:.1f}%",
                    end=""
                )

            continue

        # ----------------------------------------------------
        # AGREGAR HISTORIAL
        # ----------------------------------------------------

        historial.append(
            (
                letra,
                confianza
            )
        )

        # ----------------------------------------------------
        # CONSENSO
        # ----------------------------------------------------

        if len(historial) == CONFIRM_FRAMES:

            letras = [
                x[0]
                for x in historial
            ]

            comun, cantidad = (
                Counter(
                    letras
                ).most_common(1)[0]
            )

            ratio = (
                cantidad /
                CONFIRM_FRAMES
            )

            if ratio >= CONSENSUS_RATIO:

                ahora = time.time()

                if (
                    comun != ultima_letra
                    or
                    (
                        ahora -
                        ultimo_tiempo
                        >
                        COOLDOWN_SECONDS
                    )
                ):

                    conf = np.mean(
                        [
                            x[1]
                            for x in historial
                            if x[0] == comun
                        ]
                    )

                    mostrar(
                        comun,
                        conf,
                        margen
                    )

                    hablar(
                        engine,
                        comun
                    )

                    ultima_letra = comun

                    ultimo_tiempo = ahora

                    historial.clear()

        if frames % 20 == 0:

            print(
                f"\rLeyendo... "
                f"| Pred: {letra} "
                f"({confianza * 100:.0f}%) "
                f"| Buffer: "
                f"{''.join(x[0] for x in historial)}",
                end=""
            )


# ============================================================
# MAIN
# ============================================================

def main():

    (
        modelo,
        scaler,
        encoder,
        metadata
    ) = cargar()

    engine = inicializar_voz()

    print(
        "\nConéctate a:"
    )

    print(
        "SIGNVOICE_GLOVE"
    )

    sock = conectar()

    try:

        reconocer(
            sock,
            modelo,
            scaler,
            encoder,
            engine
        )

    except KeyboardInterrupt:

        print(
            "\n\nReconocimiento detenido."
        )

    finally:

        sock.close()

        print(
            "\nConexión cerrada."
        )


# ============================================================

if __name__ == "__main__":

    main()
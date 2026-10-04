"""
SIGNVOICE — REGISTRO DE DATASET V3
===================================

Captura datos del ESP32 mediante WiFi TCP.

ESP32:
    IP   = 192.168.4.1
    PORT = 8080

Frecuencia esperada:
    delay(10) ≈ 100 muestras/s

Formato esperado:
    Flex1, Flex2, Flex3, Flex4, Flex5,
    AX, AY, AZ, GX, GY, GZ

Total:
    11 valores + Clase + Sesion
"""

import socket
import pandas as pd
import time
import os


# ============================================================
# CONFIGURACIÓN
# ============================================================

ESP32_IP = "192.168.4.1"
ESP32_PORT = 8080

MUESTRAS_POR_SESION = 200
SESIONES_POR_LETRA = 10

PAUSA_SESION = 2

ARCHIVO_DATASET = "dataset_signvoice.csv"

# Timeout del socket.
# No significa que la conexión se cierre inmediatamente.
TIMEOUT_SOCKET = 5

# Número máximo de timeouts consecutivos antes
# de considerar que realmente se perdió la conexión.
MAX_TIMEOUTS = 3


# ============================================================
# COLUMNAS
# ============================================================

COLUMNAS = [
    "Flex1",
    "Flex2",
    "Flex3",
    "Flex4",
    "Flex5",
    "AX",
    "AY",
    "AZ",
    "GX",
    "GY",
    "GZ",
    "Clase",
    "Sesion"
]


# ============================================================
# CONEXIÓN
# ============================================================

def conectar():

    while True:

        try:

            print(
                f"\nConectando al ESP32 "
                f"{ESP32_IP}:{ESP32_PORT}..."
            )

            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            sock.settimeout(TIMEOUT_SOCKET)

            sock.connect(
                (ESP32_IP, ESP32_PORT)
            )

            print("[OK] ESP32 conectado.")

            return sock

        except Exception as e:

            print(
                f"[!] No se pudo conectar: {e}"
            )

            print(
                "    Reintentando en 2 segundos..."
            )

            time.sleep(2)


# ============================================================
# LEER LÍNEA TCP
# ============================================================

def leer_linea(sock, buffer):

    """
    Lee datos TCP hasta encontrar '\n'.

    Maneja correctamente:
    - Fragmentación TCP
    - Varias líneas recibidas juntas
    - Timeout temporal
    """

    while b"\n" not in buffer:

        try:

            chunk = sock.recv(1024)

        except socket.timeout:

            # Timeout temporal.
            # No significa que el ESP32 se haya desconectado.
            raise

        if not chunk:

            raise ConnectionError(
                "El ESP32 cerró la conexión."
            )

        buffer += chunk

    linea, _, resto = buffer.partition(b"\n")

    return (
        linea.decode(
            errors="ignore"
        ).strip(),
        resto
    )


# ============================================================
# PARSEAR DATOS
# ============================================================

def parsear_linea(linea):

    try:

        valores = [
            float(x.strip())
            for x in linea.split(",")
        ]

        # Debemos recibir exactamente:
        #
        # 5 FLEX
        # 3 ACCEL
        # 3 GYRO
        #
        # TOTAL = 11

        if len(valores) != 11:

            return None

        return valores

    except (ValueError, TypeError):

        return None


# ============================================================
# CUENTA REGRESIVA
# ============================================================

def cuenta_regresiva():

    print("\nPreparado...")
    print("3")
    time.sleep(1)

    print("2")
    time.sleep(1)

    print("1")
    time.sleep(1)

    print("\n>>> CAPTURANDO <<<")


# ============================================================
# CAPTURAR SESIÓN
# ============================================================

def capturar_sesion(
    sock,
    buffer,
    letra,
    sesion
):

    dataset = []

    print("\n--------------------------------------")

    print(
        f"Letra: {letra} | "
        f"Sesión: {sesion}/{SESIONES_POR_LETRA}"
    )

    print(
        f"Muestras: {MUESTRAS_POR_SESION}"
    )

    cuenta_regresiva()

    timeouts = 0

    inicio = time.time()

    while len(dataset) < MUESTRAS_POR_SESION:

        try:

            linea, buffer = leer_linea(
                sock,
                buffer
            )

            # Si recibimos datos correctamente,
            # reiniciamos contador de timeouts.
            timeouts = 0

        except socket.timeout:

            timeouts += 1

            print(
                f"\n[!] Esperando datos del ESP32..."
                f" ({timeouts}/{MAX_TIMEOUTS})"
            )

            if timeouts < MAX_TIMEOUTS:

                continue

            raise ConnectionError(
                "El ESP32 dejó de enviar datos."
            )

        except ConnectionError:

            raise

        except OSError as e:

            raise ConnectionError(
                f"Error de comunicación: {e}"
            )

        valores = parsear_linea(linea)

        if valores is None:

            continue

        dataset.append(
            valores + [
                letra,
                sesion
            ]
        )

        # Mostrar progreso cada 25 muestras

        if len(dataset) % 25 == 0:

            tiempo = time.time() - inicio

            velocidad = (
                len(dataset) / tiempo
                if tiempo > 0
                else 0
            )

            print(
                f"  {len(dataset)}/"
                f"{MUESTRAS_POR_SESION}"
                f"  | {velocidad:.1f} muestras/s"
            )

    tiempo_total = time.time() - inicio

    velocidad = (
        len(dataset) / tiempo_total
        if tiempo_total > 0
        else 0
    )

    print(
        f"\n>>> SESIÓN {sesion} COMPLETADA"
    )

    print(
        f"    Muestras : {len(dataset)}"
    )

    print(
        f"    Tiempo   : {tiempo_total:.2f} s"
    )

    print(
        f"    Velocidad: {velocidad:.1f} muestras/s"
    )

    return dataset, buffer


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print("       SIGNVOICE — GENERADOR DE DATASET V3")
    print("=" * 60)

    print(
        f"\nMuestras por sesión : "
        f"{MUESTRAS_POR_SESION}"
    )

    print(
        f"Sesiones por letra  : "
        f"{SESIONES_POR_LETRA}"
    )

    print(
        f"Muestras por letra  : "
        f"{MUESTRAS_POR_SESION * SESIONES_POR_LETRA}"
    )

    print(
        "\nFrecuencia esperada del ESP32:"
    )

    print(
        "  delay(10) ≈ 100 muestras/s"
    )

    print(
        "\nEscribe FIN para terminar."
    )

    # --------------------------------------------------------
    # CONECTAR
    # --------------------------------------------------------

    sock = conectar()

    buffer = b""

    dataset_total = []

    try:

        while True:

            letra = input(
                "\nIngrese letra: "
            ).strip().upper()

            if letra == "FIN":

                break

            if len(letra) == 0:

                continue

            print(
                f"\n>>> REGISTRANDO LETRA: {letra}"
            )

            print(
                "\nIMPORTANTE:"
            )

            print(
                "Mantén la misma seña durante "
                "cada sesión."
            )

            print(
                "Entre sesiones puedes modificar "
                "ligeramente la posición/orientación."
            )

            # ------------------------------------------------
            # SESIONES
            # ------------------------------------------------

            for sesion in range(
                1,
                SESIONES_POR_LETRA + 1
            ):

                try:

                    datos, buffer = capturar_sesion(
                        sock,
                        buffer,
                        letra,
                        sesion
                    )

                except ConnectionError as e:

                    print(
                        f"\n[!] {e}"
                    )

                    print(
                        "[!] Intentando reconectar..."
                    )

                    try:
                        sock.close()
                    except:
                        pass

                    sock = conectar()

                    buffer = b""

                    print(
                        "\n[OK] Reconectado."
                    )

                    print(
                        "Esta sesión se repetirá."
                    )

                    # Repetir la misma sesión
                    # sin incrementar el contador.

                    continue

                dataset_total.extend(
                    datos
                )

                print(
                    f"Total acumulado: "
                    f"{len(dataset_total)}"
                )

                # ------------------------------------------------
                # PAUSA
                # ------------------------------------------------

                if sesion < SESIONES_POR_LETRA:

                    print(
                        f"\nPausa de "
                        f"{PAUSA_SESION} segundos..."
                    )

                    time.sleep(
                        PAUSA_SESION
                    )

            # ------------------------------------------------
            # LETRA COMPLETADA
            # ------------------------------------------------

            print(
                "\n================================"
            )

            print(
                f"LETRA {letra} COMPLETADA"
            )

            print(
                f"Muestras: "
                f"{MUESTRAS_POR_SESION * SESIONES_POR_LETRA}"
            )

            print(
                "================================"
            )

    except KeyboardInterrupt:

        print(
            "\n\nCaptura interrumpida por el usuario."
        )

    finally:

        try:
            sock.close()
        except:
            pass

        print(
            "\nConexión cerrada."
        )

    # ========================================================
    # GUARDAR DATASET
    # ========================================================

    if not dataset_total:

        print(
            "\nNo se capturaron datos."
        )

        return

    df_nuevo = pd.DataFrame(
        dataset_total,
        columns=COLUMNAS
    )

    # ========================================================
    # DATASET EXISTENTE
    # ========================================================

    if os.path.exists(
        ARCHIVO_DATASET
    ):

        print(
            f"\nYa existe: "
            f"{ARCHIVO_DATASET}"
        )

        opcion = input(
            "¿Reemplazar (R) o agregar (A)? "
        ).strip().upper()

        if opcion == "A":

            df_anterior = pd.read_csv(
                ARCHIVO_DATASET
            )

            df = pd.concat(
                [
                    df_anterior,
                    df_nuevo
                ],
                ignore_index=True
            )

        else:

            df = df_nuevo

    else:

        df = df_nuevo

    # ========================================================
    # GUARDAR
    # ========================================================

    df.to_csv(
        ARCHIVO_DATASET,
        index=False
    )

    print("\n")
    print("=" * 60)
    print("             DATASET GUARDADO")
    print("=" * 60)

    print(
        f"\nArchivo:"
        f" {ARCHIVO_DATASET}"
    )

    print(
        f"Total muestras:"
        f" {len(df)}"
    )

    print("\nDistribución por letra:")

    print(
        df["Clase"]
        .value_counts()
        .sort_index()
    )

    print("\nDistribución por sesión:")

    print(
        df["Sesion"]
        .value_counts()
        .sort_index()
    )

    print(
        "\n>>> Registro finalizado correctamente."
    )


# ============================================================

if __name__ == "__main__":

    main()
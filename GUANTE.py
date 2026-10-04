"""
GUANTE_WIFI.py — Generador de dataset SIGNVOICE vía WiFi
==========================================================
Se conecta al ESP32 (modo Access Point + servidor TCP) mediante sockets,
en lugar de un puerto serial Bluetooth.

INSTRUCCIONES DE CONEXION:
1. Sube GUANTE_WIFI.ino al ESP32 y abre el Monitor Serie para ver su IP.
2. En tu PC, conéctate a la red WiFi "SIGNVOICE_GLOVE"
   (contraseña: signvoice2026).
3. Ajusta la variable ESP32_IP abajo con la IP que muestra el Monitor Serie
   (normalmente 192.168.4.1 si no la cambiaste).
4. Ejecuta este script.

Nota: mientras tu PC esté conectada a la red del guante, no tendrá
acceso a Internet simultáneamente (a menos que uses un segundo
adaptador WiFi o datos móviles de respaldo).
"""

import socket
import pandas as pd
import time

# ====================================
# CONFIGURACION
# ====================================
ESP32_IP   = "192.168.4.1"   # IP del ESP32 en modo Access Point
ESP32_PORT = 8080
MUESTRAS   = 2000

# ====================================
# CONEXION TCP
# ====================================

def conectar() -> socket.socket:
    """Crea y retorna un socket conectado al ESP32, con reintentos."""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((ESP32_IP, ESP32_PORT))
            print(f"Conectado al ESP32 en {ESP32_IP}:{ESP32_PORT}")
            return sock
        except (socket.timeout, ConnectionRefusedError, OSError) as exc:
            print(f"No se pudo conectar ({exc}). Reintentando en 2s...")
            time.sleep(2)


def leer_linea(sock: socket.socket, buffer: bytes) -> tuple[str, bytes]:
    """
    Lee del socket hasta encontrar un salto de línea, manejando el buffer
    de bytes que puede contener fragmentos de líneas anteriores.

    Returns:
        Tupla (linea_decodificada, buffer_restante)
    """
    while b"\n" not in buffer:
        chunk = sock.recv(256)
        if not chunk:
            raise ConnectionError("El ESP32 cerró la conexión.")
        buffer += chunk

    linea, _, resto = buffer.partition(b"\n")
    return linea.decode(errors="ignore").strip(), resto


# ====================================
# PROGRAMA PRINCIPAL
# ====================================

def main() -> None:
    sock = conectar()
    buffer = b""
    dataset: list[list[str]] = []

    print("\n================================")
    print("SIGNVOICE DATASET GENERATOR (WiFi)")
    print("================================")

    try:
        while True:
            letra = input("\nIngrese letra (A-Z) o FIN: ").upper()
            if letra == "FIN":
                break

            print(f"\nPreparado para capturar '{letra}'")
            print("3..."); time.sleep(1)
            print("2..."); time.sleep(1)
            print("1..."); time.sleep(1)
            print("\nCAPTURANDO...")

            contador = 0
            while contador < MUESTRAS:
                try:
                    linea, buffer = leer_linea(sock, buffer)
                except (ConnectionError, socket.timeout, OSError) as exc:
                    print(f"\nConexión perdida ({exc}). Reconectando...")
                    sock.close()
                    sock = conectar()
                    buffer = b""
                    continue

                valores = linea.split(",")
                if len(valores) != 11:
                    continue

                dataset.append(valores + [letra])
                contador += 1

                if contador % 100 == 0:
                    print(f"{contador}/{MUESTRAS}")

            print(f"\nLETRA '{letra}' COMPLETADA — {contador} muestras")

    finally:
        sock.close()
        print("\nConexión TCP cerrada.")

        if dataset:
            columnas = [
                "Flex1", "Flex2", "Flex3", "Flex4", "Flex5",
                "AX", "AY", "AZ", "GX", "GY", "GZ",
                "Clase",
            ]
            df = pd.DataFrame(dataset, columns=columnas)
            nombre = "dataset_signvoice.csv"
            df.to_csv(nombre, index=False)

            print("\n================================")
            print("DATASET GUARDADO")
            print(f"{nombre}  ({len(dataset)} filas totales)")
            print("================================")
        else:
            print("\nNo se capturó ninguna muestra; no se generó archivo.")


if __name__ == "__main__":
    main()

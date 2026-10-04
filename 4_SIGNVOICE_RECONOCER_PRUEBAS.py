"""
SIGNVOICE_RECONOCER_PRUEBAS.py — Reconocimiento en tiempo real con registro de pruebas
=======================================================================================
Versión mejorada con:
  • Registro automático de datos por usuario (15 usuarios max)
  • Carpeta PRUEBAS con subcarpetas USER1, USER2, ... USER15
  • Exportación de datos a Excel (editable)
  • Gráficos de resultados por usuario
  • Resumen final consolidado con estadísticas generales

Sistema dual de modelos:
  Letras estáticas (A-Z sin J,Ñ,Z) → Modelo Flex solamente
  Letras dinámicas (J, Ñ, Z)        → Modelo Flex + MPU9250

Requisitos:
    pip install scikit-learn joblib pyttsx3 pandas openpyxl matplotlib seaborn
"""

import warnings
warnings.filterwarnings("ignore")

import socket
import time
import os
import shutil
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from datetime import datetime
from pathlib import Path

# ====================================
# CONFIGURACION
# ====================================

ESP32_IP   = "192.168.4.1"
ESP32_PORT = 8080

MODEL_ESTATICO_PATH   = "model_estatico.pkl"
SCALER_ESTATICO_PATH  = "scaler_estatico.pkl"
ENCODER_ESTATICO_PATH = "encoder_estatico.pkl"

MODEL_DINAMICO_PATH   = "model_dinamico.pkl"
SCALER_DINAMICO_PATH  = "scaler_dinamico.pkl"
ENCODER_DINAMICO_PATH = "encoder_dinamico.pkl"

METADATA_PATH = "signvoice_metadata.pkl"

CONFIRM_FRAMES   = 8
MIN_CONFIDENCE   = 0.70
COOLDOWN_SECONDS = 1.5

FLEX_COLS = ["Flex1", "Flex2", "Flex3", "Flex4", "Flex5"]
ALL_COLS  = FLEX_COLS + ["AX", "AY", "AZ", "GX", "GY", "GZ"]

# Carpeta de pruebas
PRUEBAS_DIR = "PRUEBAS"
MAX_USUARIOS = 15


# ====================================
# GESTION DE CARPETAS DE PRUEBAS
# ====================================

def crear_estructura_pruebas():
    """Crea la estructura de carpetas PRUEBAS/USER1, USER2, etc."""
    if os.path.exists(PRUEBAS_DIR):
        print(f"\n  ⚠ La carpeta '{PRUEBAS_DIR}' ya existe.")
        respuesta = input("  ¿Deseas limpiarla y crear una nueva? (s/n): ").lower()
        if respuesta == 's':
            shutil.rmtree(PRUEBAS_DIR)
            print(f"  Carpeta '{PRUEBAS_DIR}' eliminada.")
        else:
            print(f"  Usando carpeta existente.")
    
    os.makedirs(PRUEBAS_DIR, exist_ok=True)
    print(f"  Carpeta principal creada: {PRUEBAS_DIR}/")


def obtener_proxima_carpeta_usuario():
    """Encuentra el próximo número de usuario disponible."""
    if not os.path.exists(PRUEBAS_DIR):
        return 1
    
    carpetas_existentes = [
        int(d.replace("USER", "")) 
        for d in os.listdir(PRUEBAS_DIR) 
        if d.startswith("USER") and d[4:].isdigit()
    ]
    
    if not carpetas_existentes:
        return 1
    
    return max(carpetas_existentes) + 1


def crear_carpeta_usuario(num_usuario):
    """Crea carpeta para un usuario específico."""
    carpeta = os.path.join(PRUEBAS_DIR, f"USER{num_usuario}")
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


# ====================================
# REGISTRO DE DATOS
# ====================================

class RegistroPruebas:
    """Gestiona el registro de datos y métricas de una prueba de usuario."""
    
    def __init__(self, num_usuario):
        self.num_usuario = num_usuario
        self.carpeta = crear_carpeta_usuario(num_usuario)
        self.timestamp_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Datos de reconocimientos exitosos
        self.reconocimientos = []  # Lista de dicts con datos de cada reconocimiento
        
        # Estadísticas
        self.letras_completadas = {}  # {letra: {count, avg_confidence, latencias}}
        self.tiempo_inicio_prueba = time.time()
        
    def registrar_reconocimiento(self, letra, confianza, modelo_usado, latencia_ms):
        """Registra un reconocimiento exitoso."""
        registro = {
            'timestamp': datetime.now().isoformat(),
            'letra': letra,
            'confianza': confianza,
            'modelo': modelo_usado,
            'latencia_ms': latencia_ms,
        }
        self.reconocimientos.append(registro)
        
        # Actualizar estadísticas por letra
        if letra not in self.letras_completadas:
            self.letras_completadas[letra] = {
                'count': 0,
                'confianzas': [],
                'latencias': [],
            }
        
        self.letras_completadas[letra]['count'] += 1
        self.letras_completadas[letra]['confianzas'].append(confianza)
        self.letras_completadas[letra]['latencias'].append(latencia_ms)
    
    def calcular_metricas(self):
        """Calcula métricas consolidadas."""
        total_reconocimientos = len(self.reconocimientos)
        tiempo_total = time.time() - self.tiempo_inicio_prueba
        
        metricas = {
            'usuario_id': self.num_usuario,
            'timestamp_inicio': self.timestamp_inicio,
            'timestamp_fin': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_reconocimientos': total_reconocimientos,
            'tiempo_prueba_segundos': tiempo_total,
            'letras_unicas': len(self.letras_completadas),
            'confianza_promedio': 0,
            'latencia_promedio_ms': 0,
            'latencia_min_ms': 0,
            'latencia_max_ms': 0,
        }
        
        if self.reconocimientos:
            confianzas = [r['confianza'] for r in self.reconocimientos]
            latencias = [r['latencia_ms'] for r in self.reconocimientos]
            
            metricas['confianza_promedio'] = np.mean(confianzas)
            metricas['confianza_min'] = np.min(confianzas)
            metricas['confianza_max'] = np.max(confianzas)
            metricas['confianza_std'] = np.std(confianzas)
            
            metricas['latencia_promedio_ms'] = np.mean(latencias)
            metricas['latencia_min_ms'] = np.min(latencias)
            metricas['latencia_max_ms'] = np.max(latencias)
            metricas['latencia_std_ms'] = np.std(latencias)
        
        return metricas
    
    def exportar_excel(self):
        """Exporta datos a archivo Excel con formato."""
        archivo = os.path.join(self.carpeta, f"usuario_{self.num_usuario}_datos.xlsx")
        
        # Crear dataframe con reconocimientos
        df_reconocimientos = pd.DataFrame(self.reconocimientos)
        
        # Crear dataframe con resumen por letra
        resumen_letras = []
        for letra, datos in sorted(self.letras_completadas.items()):
            resumen_letras.append({
                'Letra': letra,
                'Reconocimientos': datos['count'],
                'Confianza Promedio': np.mean(datos['confianzas']),
                'Confianza Min': np.min(datos['confianzas']),
                'Confianza Max': np.max(datos['confianzas']),
                'Latencia Promedio (ms)': np.mean(datos['latencias']),
                'Latencia Min (ms)': np.min(datos['latencias']),
                'Latencia Max (ms)': np.max(datos['latencias']),
            })
        df_resumen = pd.DataFrame(resumen_letras)
        
        # Métricas generales
        metricas = self.calcular_metricas()
        df_metricas = pd.DataFrame([metricas])
        
        # Escribir a Excel
        with pd.ExcelWriter(archivo, engine='openpyxl') as writer:
            df_metricas.to_excel(writer, sheet_name='Metricas Generales', index=False)
            df_resumen.to_excel(writer, sheet_name='Resumen por Letra', index=False)
            df_reconocimientos.to_excel(writer, sheet_name='Datos Detallados', index=False)
        
        print(f"  ✓ Excel exportado: {archivo}")
        return archivo
    
    def generar_graficos(self):
        """Genera gráficos de resultados."""
        if not self.reconocimientos:
            print(f"  ⚠ No hay datos para generar gráficos")
            return
        
        df = pd.DataFrame(self.reconocimientos)
        
        # Gráfico 1: Distribución de confianza
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f'Usuario {self.num_usuario} - Análisis de Rendimiento', 
                     fontsize=16, fontweight='bold')
        
        # Histograma de confianza
        axes[0, 0].hist(df['confianza'], bins=30, color='#2E86AB', edgecolor='black', alpha=0.7)
        axes[0, 0].set_xlabel('Confianza')
        axes[0, 0].set_ylabel('Frecuencia')
        axes[0, 0].set_title('Distribución de Confianza')
        axes[0, 0].axvline(df['confianza'].mean(), color='red', linestyle='--', 
                          label=f'Promedio: {df["confianza"].mean():.3f}')
        axes[0, 0].legend()
        axes[0, 0].grid(alpha=0.3)
        
        # Histograma de latencia
        axes[0, 1].hist(df['latencia_ms'], bins=30, color='#A23B72', edgecolor='black', alpha=0.7)
        axes[0, 1].set_xlabel('Latencia (ms)')
        axes[0, 1].set_ylabel('Frecuencia')
        axes[0, 1].set_title('Distribución de Latencia')
        axes[0, 1].axvline(df['latencia_ms'].mean(), color='red', linestyle='--',
                          label=f'Promedio: {df["latencia_ms"].mean():.1f} ms')
        axes[0, 1].legend()
        axes[0, 1].grid(alpha=0.3)
        
        # Reconocimientos por letra
        letra_counts = df['letra'].value_counts().sort_index()
        axes[1, 0].bar(letra_counts.index, letra_counts.values, color='#F18F01', edgecolor='black', alpha=0.7)
        axes[1, 0].set_xlabel('Letra')
        axes[1, 0].set_ylabel('Cantidad de Reconocimientos')
        axes[1, 0].set_title('Reconocimientos por Letra')
        axes[1, 0].tick_params(axis='x', rotation=0)
        axes[1, 0].grid(alpha=0.3, axis='y')
        
        # Confianza promedio por letra
        letra_conf = df.groupby('letra')['confianza'].mean().sort_index()
        axes[1, 1].bar(letra_conf.index, letra_conf.values, color='#C73E1D', edgecolor='black', alpha=0.7)
        axes[1, 1].set_xlabel('Letra')
        axes[1, 1].set_ylabel('Confianza Promedio')
        axes[1, 1].set_title('Confianza Promedio por Letra')
        axes[1, 1].set_ylim([0, 1.0])
        axes[1, 1].tick_params(axis='x', rotation=0)
        axes[1, 1].grid(alpha=0.3, axis='y')
        
        plt.tight_layout()
        archivo_grafico = os.path.join(self.carpeta, f"usuario_{self.num_usuario}_graficos.png")
        plt.savefig(archivo_grafico, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Gráficos generados: {archivo_grafico}")
        return archivo_grafico


# ====================================
# VOZ
# ====================================

def inicializar_voz():
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.setProperty("volume", 1.0)
        voices = engine.getProperty("voices")
        for v in voices:
            if "es" in v.id.lower() or "spanish" in v.name.lower():
                engine.setProperty("voice", v.id)
                break
        print("  ✓ Síntesis de voz activada.")
        return engine
    except Exception:
        print("  ⚠ pyttsx3 no disponible — solo se mostrará texto.")
        return None


def hablar(engine, texto):
    if engine:
        try:
            engine.say(texto)
            engine.runAndWait()
        except Exception:
            pass


# ====================================
# CARGAR MODELOS
# ====================================

def cargar_modelos():
    """
    Carga los modelos disponibles y los metadatos del entrenamiento.
    Muestra al usuario qué letras están registradas.
    """
    if not os.path.exists(METADATA_PATH):
        raise FileNotFoundError(
            f"No se encontro: {METADATA_PATH}\n"
            "Ejecuta primero SIGNVOICE_TRAIN.py."
        )

    metadata = joblib.load(METADATA_PATH)

    print("\n" + "="*60)
    print("  SIGNVOICE — RECONOCIMIENTO CON REGISTRO DE PRUEBAS")
    print("="*60)

    letras_estaticas = metadata.get("letras_estaticas", [])
    letras_dinamicas = metadata.get("letras_dinamicas", [])
    letras_esperadas = metadata.get("letras_dinamicas_esperadas", [])
    todas            = sorted(letras_estaticas + letras_dinamicas)

    print(f"\n  Letras registradas ({len(todas)}):")
    print(f"    {', '.join(todas) if todas else '(ninguna)'}")

    print(f"\n  Letras estáticas ({len(letras_estaticas)}) — solo Flex:")
    print(f"    {', '.join(sorted(letras_estaticas)) if letras_estaticas else '(ninguna)'}")

    print(f"\n  Letras dinámicas ({len(letras_dinamicas)}) — Flex + MPU:")
    print(f"    {', '.join(sorted(letras_dinamicas)) if letras_dinamicas else '(ninguna aun)'}")

    faltantes = set(letras_esperadas) - set(letras_dinamicas)
    if faltantes:
        print(f"\n  Pendientes de capturar: {', '.join(sorted(faltantes))}")

    # Cargar modelo estático
    modelo_est = scaler_est = encoder_est = None
    if metadata.get("modelo_estatico_disponible"):
        modelo_est  = joblib.load(MODEL_ESTATICO_PATH)
        scaler_est  = joblib.load(SCALER_ESTATICO_PATH)
        encoder_est = joblib.load(ENCODER_ESTATICO_PATH)
        print(f"\n  ✓ Modelo estático cargado")

    # Cargar modelo dinámico
    modelo_din = scaler_din = encoder_din = None
    if metadata.get("modelo_dinamico_disponible"):
        modelo_din  = joblib.load(MODEL_DINAMICO_PATH)
        scaler_din  = joblib.load(SCALER_DINAMICO_PATH)
        encoder_din = joblib.load(ENCODER_DINAMICO_PATH)
        print(f"  ✓ Modelo dinámico cargado")

    return (
        modelo_est, scaler_est, encoder_est,
        modelo_din, scaler_din, encoder_din,
        metadata,
    )


# ====================================
# CONEXION WIFI
# ====================================

def conectar():
    print(f"\n  Conectando al guante ({ESP32_IP}:{ESP32_PORT})...")
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((ESP32_IP, ESP32_PORT))
            print(f"  ✓ ¡Conectado!")
            return sock
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            print(f"  ⏳ Reintentando... ({e})")
            time.sleep(2)


def leer_linea(sock, buffer):
    while b"\n" not in buffer:
        chunk = sock.recv(512)
        if not chunk:
            raise ConnectionError("El guante cerró la conexión.")
        buffer += chunk
    linea, _, resto = buffer.partition(b"\n")
    return linea.decode(errors="ignore").strip(), resto


def parsear_linea(linea):
    try:
        valores = [float(v) for v in linea.split(",")]
        return valores if len(valores) == 11 else None
    except ValueError:
        return None


# ====================================
# RECONOCIMIENTO DUAL
# ====================================

def predecir(
    valores,
    modelo_est, scaler_est, encoder_est,
    modelo_din, scaler_din, encoder_din,
    letras_dinamicas,
):
    """
    Aplica ambos modelos y retorna la predicción más confiable.
    """
    candidatos = []

    # Predicción estática (solo Flex)
    if modelo_est is not None:
        X_flex = scaler_est.transform([valores[:5]])
        pred   = modelo_est.predict(X_flex)[0]
        probs  = modelo_est.predict_proba(X_flex)[0]
        conf   = float(probs[pred])
        letra  = encoder_est.inverse_transform([pred])[0]
        candidatos.append((letra, conf, "EST"))

    # Predicción dinámica (Flex + MPU)
    if modelo_din is not None:
        X_all = scaler_din.transform([valores])
        pred  = modelo_din.predict(X_all)[0]
        probs = modelo_din.predict_proba(X_all)[0]
        conf  = float(probs[pred])
        letra = encoder_din.inverse_transform([pred])[0]
        candidatos.append((letra, conf, "DIN"))

    if not candidatos:
        return None

    # Ganar por confianza
    mejor = max(candidatos, key=lambda x: x[1])
    return mejor


def mostrar_resultado(letra, confianza, modelo_usado):
    barra = "#" * int(confianza * 20)
    vacio = "-" * (20 - int(confianza * 20))
    tipo  = "Flex+MPU" if modelo_usado == "DIN" else "Flex"
    border = "-" * (len(letra) + 10)
    print(f"\n  +{border}+")
    print(f"  |   {letra}   [{tipo}]  |")
    print(f"  +{border}+")
    print(f"  Confianza: [{barra}{vacio}] {confianza*100:.1f}%\n")


def reconocer(sock, modelo_est, scaler_est, encoder_est,
              modelo_din, scaler_din, encoder_din, metadata, engine, registro):

    letras_dinamicas = set(metadata.get("letras_dinamicas", []))
    buffer      = b""
    historial   = []
    ultima      = ""
    ultimo_ts   = 0.0
    frames      = 0
    tiempo_frame_anterior = time.time()

    print("\n" + "="*60)
    print("  Realiza una seña con el guante...")
    print("  Presiona Ctrl+C para finalizar la prueba.")
    print("="*60 + "\n")

    while True:
        try:
            tiempo_inicio_frame = time.time()
            linea, buffer = leer_linea(sock, buffer)
            tiempo_recepcion = time.time()
        except (ConnectionError, socket.timeout, OSError) as e:
            print(f"\n  ⚠ Conexión perdida ({e}). Reconectando...")
            sock.close()
            sock = conectar()
            buffer = b""
            historial.clear()
            continue

        valores = parsear_linea(linea)
        if valores is None:
            continue

        frames += 1
        latencia_ms = (tiempo_recepcion - tiempo_inicio_frame) * 1000

        resultado = predecir(
            valores,
            modelo_est, scaler_est, encoder_est,
            modelo_din, scaler_din, encoder_din,
            letras_dinamicas,
        )
        if resultado is None:
            continue

        letra_pred, confianza, modelo_usado = resultado

        # Acumular en buffer de confirmación
        if confianza >= MIN_CONFIDENCE:
            historial.append((letra_pred, confianza, modelo_usado, latencia_ms))
        else:
            historial.clear()

        if len(historial) > CONFIRM_FRAMES:
            historial.pop(0)

        # Verificar consenso
        if len(historial) == CONFIRM_FRAMES:
            letras_buf = [h[0] for h in historial]
            mas_comun, conteo = Counter(letras_buf).most_common(1)[0]
            ratio = conteo / CONFIRM_FRAMES

            if ratio >= 0.75:
                ahora = time.time()
                mismo    = (mas_comun == ultima)
                cooldown = (ahora - ultimo_ts) < COOLDOWN_SECONDS

                if not (mismo and cooldown):
                    # Tomar el modelo_usado más frecuente
                    modelos_buf = [h[2] for h, l in zip(historial, letras_buf) if l == mas_comun]
                    modelo_final = Counter(modelos_buf).most_common(1)[0][0]
                    
                    conf_promedio = float(np.mean([
                        h[1] for h in historial if h[0] == mas_comun
                    ]))
                    
                    latencia_promedio = float(np.mean([
                        h[3] for h in historial if h[0] == mas_comun
                    ]))

                    mostrar_resultado(mas_comun, conf_promedio, modelo_final)
                    hablar(engine, mas_comun)
                    
                    # Registrar el reconocimiento
                    registro.registrar_reconocimiento(
                        mas_comun, conf_promedio, modelo_final, latencia_promedio
                    )

                    ultima    = mas_comun
                    ultimo_ts = ahora
                    historial.clear()

        # Estado en tiempo real cada 20 frames
        if frames % 20 == 0:
            estado = f"{letra_pred}({confianza*100:.0f}%)" if resultado else "---"
            buf_visual = ''.join([h[0] for h in historial[-5:]]) or '---'
            print(f"  Leyendo... | Pred: {estado:15} | Buffer: {buf_visual}",
                  end="\r")


# ====================================
# RESUMEN FINAL
# ====================================

def generar_resumen_final():
    """Genera un resumen consolidado de todas las pruebas."""
    if not os.path.exists(PRUEBAS_DIR):
        print("  No hay pruebas registradas.")
        return
    
    carpeta_resumen = os.path.join(PRUEBAS_DIR, "RESUMEN_FINAL")
    os.makedirs(carpeta_resumen, exist_ok=True)
    
    print("\n" + "="*60)
    print("  GENERANDO RESUMEN FINAL DE PRUEBAS")
    print("="*60)
    
    # Recopilar datos de todos los usuarios
    resumen_usuarios = []
    todos_datos_detallados = []
    
    for usuario_dir in sorted(os.listdir(PRUEBAS_DIR)):
        if usuario_dir.startswith("USER"):
            num_usuario = int(usuario_dir.replace("USER", ""))
            carpeta_usuario = os.path.join(PRUEBAS_DIR, usuario_dir)
            
            # Buscar archivo Excel
            archivo_excel = os.path.join(carpeta_usuario, f"usuario_{num_usuario}_datos.xlsx")
            if os.path.exists(archivo_excel):
                try:
                    df_metricas = pd.read_excel(archivo_excel, sheet_name='Metricas Generales')
                    df_detallados = pd.read_excel(archivo_excel, sheet_name='Datos Detallados')
                    
                    resumen_usuarios.append(df_metricas.iloc[0].to_dict())
                    todos_datos_detallados.append(df_detallados)
                    
                    print(f"  ✓ Datos de USER{num_usuario} recopilados")
                except Exception as e:
                    print(f"  ⚠ Error al leer USER{num_usuario}: {e}")
    
    if not resumen_usuarios:
        print("  No hay datos de usuarios para resumir.")
        return
    
    # Crear DataFrames de resumen
    df_resumen_usuarios = pd.DataFrame(resumen_usuarios)
    df_todos_datos = pd.concat(todos_datos_detallados, ignore_index=True) if todos_datos_detallados else pd.DataFrame()
    
    # Calcular estadísticas generales
    stats_generales = {
        'Métrica': [
            'Total Usuarios',
            'Total Reconocimientos',
            'Confianza Promedio Global',
            'Confianza Min',
            'Confianza Max',
            'Confianza Std Dev',
            'Latencia Promedio (ms)',
            'Latencia Min (ms)',
            'Latencia Max (ms)',
            'Latencia Std Dev (ms)',
            'Tiempo Total Pruebas (min)',
        ],
        'Valor': [
            len(df_resumen_usuarios),
            df_resumen_usuarios['total_reconocimientos'].sum(),
            df_todos_datos['confianza'].mean() if len(df_todos_datos) > 0 else 0,
            df_todos_datos['confianza'].min() if len(df_todos_datos) > 0 else 0,
            df_todos_datos['confianza'].max() if len(df_todos_datos) > 0 else 0,
            df_todos_datos['confianza'].std() if len(df_todos_datos) > 0 else 0,
            df_todos_datos['latencia_ms'].mean() if len(df_todos_datos) > 0 else 0,
            df_todos_datos['latencia_ms'].min() if len(df_todos_datos) > 0 else 0,
            df_todos_datos['latencia_ms'].max() if len(df_todos_datos) > 0 else 0,
            df_todos_datos['latencia_ms'].std() if len(df_todos_datos) > 0 else 0,
            df_resumen_usuarios['tiempo_prueba_segundos'].sum() / 60,
        ]
    }
    df_stats = pd.DataFrame(stats_generales)
    
    # Exportar a Excel
    archivo_resumen = os.path.join(carpeta_resumen, "RESUMEN_GENERAL.xlsx")
    with pd.ExcelWriter(archivo_resumen, engine='openpyxl') as writer:
        df_stats.to_excel(writer, sheet_name='Estadísticas Generales', index=False)
        df_resumen_usuarios.to_excel(writer, sheet_name='Resumen Usuarios', index=False)
        if len(df_todos_datos) > 0:
            df_todos_datos.to_excel(writer, sheet_name='Todos Los Datos', index=False)
    
    print(f"  ✓ Resumen general exportado: {archivo_resumen}")
    
    # Generar gráficos consolidados
    if len(df_todos_datos) > 0:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Resumen General - Todas las Pruebas', fontsize=18, fontweight='bold')
        
        # Confianza por usuario
        confianza_por_usuario = df_resumen_usuarios.groupby('usuario_id')['confianza_promedio'].mean()
        axes[0, 0].bar(confianza_por_usuario.index, confianza_por_usuario.values, 
                       color='#2E86AB', edgecolor='black', alpha=0.7)
        axes[0, 0].set_xlabel('Usuario')
        axes[0, 0].set_ylabel('Confianza Promedio')
        axes[0, 0].set_title('Confianza Promedio por Usuario')
        axes[0, 0].set_ylim([0, 1.0])
        axes[0, 0].grid(alpha=0.3, axis='y')
        
        # Latencia por usuario
        latencia_por_usuario = df_resumen_usuarios.groupby('usuario_id')['latencia_promedio_ms'].mean()
        axes[0, 1].bar(latencia_por_usuario.index, latencia_por_usuario.values,
                       color='#A23B72', edgecolor='black', alpha=0.7)
        axes[0, 1].set_xlabel('Usuario')
        axes[0, 1].set_ylabel('Latencia Promedio (ms)')
        axes[0, 1].set_title('Latencia Promedio por Usuario')
        axes[0, 1].grid(alpha=0.3, axis='y')
        
        # Distribución global de confianza
        axes[1, 0].hist(df_todos_datos['confianza'], bins=40, color='#F18F01', 
                        edgecolor='black', alpha=0.7)
        axes[1, 0].set_xlabel('Confianza')
        axes[1, 0].set_ylabel('Frecuencia')
        axes[1, 0].set_title('Distribución Global de Confianza')
        axes[1, 0].axvline(df_todos_datos['confianza'].mean(), color='red', 
                          linestyle='--', linewidth=2)
        axes[1, 0].grid(alpha=0.3)
        
        # Distribución global de latencia
        axes[1, 1].hist(df_todos_datos['latencia_ms'], bins=40, color='#C73E1D',
                        edgecolor='black', alpha=0.7)
        axes[1, 1].set_xlabel('Latencia (ms)')
        axes[1, 1].set_ylabel('Frecuencia')
        axes[1, 1].set_title('Distribución Global de Latencia')
        axes[1, 1].axvline(df_todos_datos['latencia_ms'].mean(), color='red',
                          linestyle='--', linewidth=2)
        axes[1, 1].grid(alpha=0.3)
        
        plt.tight_layout()
        archivo_grafico_resumen = os.path.join(carpeta_resumen, "graficos_resumen_general.png")
        plt.savefig(archivo_grafico_resumen, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Gráficos del resumen: {archivo_grafico_resumen}")
    
    print(f"\n  📁 Carpeta de resumen: {carpeta_resumen}/\n")


# ====================================
# PROGRAMA PRINCIPAL
# ====================================

def main():
    crear_estructura_pruebas()
    
    (modelo_est, scaler_est, encoder_est,
     modelo_din, scaler_din, encoder_din,
     metadata) = cargar_modelos()

    engine = inicializar_voz()

    print(f"\n  Asegurate de estar conectado a la red WiFi 'SIGNVOICE_GLOVE'")
    
    # Determinar número de usuario
    num_usuario = obtener_proxima_carpeta_usuario()
    
    if num_usuario > MAX_USUARIOS:
        print(f"\n  ⚠ Se ha alcanzado el máximo de {MAX_USUARIOS} usuarios.")
        print(f"  Por favor, ejecuta generar_resumen_final.py para consolidar resultados.")
        return
    
    print(f"\n  Iniciando prueba para USER{num_usuario}...")
    
    # Crear registro para este usuario
    registro = RegistroPruebas(num_usuario)
    
    sock = conectar()

    try:
        reconocer(
            sock,
            modelo_est, scaler_est, encoder_est,
            modelo_din, scaler_din, encoder_din,
            metadata, engine, registro,
        )
    except KeyboardInterrupt:
        print("\n\n  Reconocimiento detenido.")
    finally:
        sock.close()
        print("  Conexión cerrada.")
        
        # Procesar datos del usuario
        print(f"\n  Guardando datos de USER{num_usuario}...")
        registro.exportar_excel()
        registro.generar_graficos()
        
        # Preguntar si continuar con el siguiente usuario
        print(f"\n  ¿Deseas continuar con el siguiente usuario? (s/n): ", end="")
        respuesta = input().lower()
        if respuesta == 's':
            main()  # Recursivo para siguiente usuario
        else:
            print(f"\n  Generando resumen final...")
            generar_resumen_final()


if __name__ == "__main__":
    main()

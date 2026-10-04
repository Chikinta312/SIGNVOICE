# SIGNVOICE

**SIGNVOICE** es un prototipo de guante inteligente desarrollado para el reconocimiento de un conjunto delimitado de señas de la **Lengua de Señas Peruana (LSP)** y su conversión a una salida de voz.

El proyecto integra sensores de flexión, una unidad de medición inercial, un microcontrolador ESP32, comunicación inalámbrica y algoritmos de aprendizaje automático con el propósito de apoyar la comunicación entre personas sordas y personas oyentes.

El sistema fue desarrollado como parte de una investigación de tesis de la carrera de **Ingeniería Electrónica de la Universidad Tecnológica del Perú (UTP), Lima, Perú, 2026**.

---

## Descripción del proyecto

SIGNVOICE utiliza un guante instrumentado para adquirir información relacionada con la configuración de los dedos y el movimiento de la mano.

El prototipo está compuesto principalmente por:

- 5 sensores Flex de 2.2".
- Unidad de medición inercial MPU6050.
- Microcontrolador ESP32.
- Comunicación inalámbrica mediante WiFi.
- Comunicación TCP entre el ESP32 y el computador.
- Procesamiento de datos mediante Python.
- Filtrado de señales mediante EMA.
- Clasificación mediante Random Forest.
- Reconocimiento de señas estáticas y dinámicas.
- Conversión del resultado reconocido a voz mediante Text-to-Speech (TTS).

La información adquirida por los sensores es enviada desde el ESP32 hacia un computador, donde se realiza el procesamiento, clasificación y generación de la salida audible.

---

## Objetivo

Diseñar, implementar y evaluar el guante lector inteligente de Lengua de Señas Peruana SIGNVOICE como herramienta tecnológica de apoyo a la comunicación efectiva de personas sordas.

---

## Arquitectura general

El funcionamiento del sistema puede resumirse en las siguientes etapas:

```text
Movimiento de la mano
        │
        ▼
┌──────────────────────────────┐
│        Guante SIGNVOICE      │
│                              │
│  5 sensores Flex             │
│  MPU6050                     │
│  ESP32                       │
└──────────────┬───────────────┘
               │
               │ Adquisición de datos
               ▼
        Filtrado de señales
               │
               ▼
       Transmisión WiFi
               │
               ▼
        Servidor TCP / PC
               │
               ▼
      Procesamiento en Python
               │
               ▼
         Random Forest
               │
               ▼
       Seña reconocida
               │
               ▼
        Texto correspondiente
               │
               ▼
       Text-to-Speech (TTS)
               │
               ▼
          Salida de voz

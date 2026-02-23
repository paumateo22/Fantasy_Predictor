# ⚽ Fantasy Predictor: Moneyball Edition

Este proyecto es una infraestructura completa de **Ingeniería de Datos, Procesamiento de Imágenes (OCR) y Modelado Predictivo** diseñada para optimizar alineaciones en ligas Fantasy basándose en datos reales y eficiencia económica.

El sistema cierra la brecha entre la información visual de la App (precios y posiciones) y la información estadística web (puntos y rendimiento), permitiendo tomar decisiones basadas en el valor esperado de cada jugador.



## 🚀 Componentes del Sistema

### 1. Extracción de Mercado (OCR)
Procesa capturas de pantalla de la app mediante un pipeline de visión artificial:
* **Filtro Anti-Escudos:** Recorte dinámico para eliminar ruido visual y centrar el OCR en datos críticos.
* **Detector de Posiciones HSV:** Clasificación de jugadores por color (Portero, Defensa, Mediocampista, Delantero) con umbrales de seguridad para evitar errores por degradados.
* **Modo Rayos X:** Aplicación de filtros de cascada (Grises -> Resize -> Threshold) con `EasyOCR` para una lectura precisa de precios y puntos.

### 2. Adquisición de Datos (Web Scraping)
Scrapers robustos desarrollados con `BeautifulSoup` para extraer:
* Alineaciones probables, estados médicos y probabilidad de juego.
* Contexto táctico: datos de entrenadores, previsibilidad y rotaciones.
* Histórico de estadísticas por jornada (Goles, asistencias, tarjetas, etc.).

### 3. Entity Resolution (Cruce Inteligente)
Sistema de emparejamiento de identidades para resolver inconsistencias de nombres (ej: "A. Sancris" vs "Alejandro Sancris"):
* **Fase 0 (Memoria):** Uso de un diccionario de alias persistente en `recursos/diccionario_jugadores.json`.
* **Fase 1 (Exacta):** Coincidencia por nombre normalizado (sin tildes ni mayúsculas).
* **Fase 2 (IA):** Cruce por similitud de puntos con validación por distancia de Levenshtein.
* **Fase 3 (Manual/Global):** Interfaz de terminal para resolución de conflictos y aprendizaje de nuevas relaciones.

## 📂 Estructura del Proyecto

```text
ProyectoFantasy/
├── venv/                   # Entorno virtual
├── recursos/               # Diccionarios JSON de alias y constantes
├── fuentes/
│   ├── capturas_raw/       # Screenshots originales
│   └── capturas_pro/       # Imágenes procesadas para OCR
├── datasets/
│   └── JaJ/                # Datos de Jornada a Jornada (TXX-XX/JXX)
│       ├── mercado.csv     # Output del OCR
│       ├── jugadores.csv   # Output del Scraper
│       └── jugadores_con_mercado.csv  # Dataset unificado (Dataset Oro)
└── JaJ/
    ├── cruzado_datos/      # Scripts de consolidación y alias
    └── scripts/            # Scripts de preparación de imagen y extracción

## 🧠 Roadmap de IA y Modelado

El proyecto se divide en tres hitos fundamentales para alcanzar la predicción total:

1.  **Ingeniería de Atributos:** Consolidación del "CSV Masivo" (histórico) para crear perfiles de rendimiento por jugador, equipo y contexto (local/visitante).
2.  **Predicción de Rendimiento (Modelos de Regresión):** * **Modelo A:** Estimación de estadísticas individuales (Goles, Asistencias, Pases Clave, etc.).
    * **Modelo B:** Traducción de estadísticas a Puntos DAZN esperados según la posición del jugador.
3.  **Optimizador del 11 Ideal:** Algoritmo de optimización lineal para maximizar los puntos bajo restricción presupuestaria y táctica:

$$\text{maximizar} \sum_{i \in J} P_i \cdot x_i$$

$$\text{sujeto a:} \sum_{i \in J} C_i \cdot x_i \leq \text{Presupuesto}$$

Donde $P_i$ representa los puntos proyectados y $C_i$ el coste de cada jugador.

## 🛠️ Instalación y Uso

1. **Entorno:** Clonar el repositorio y crear un entorno virtual: `python -m venv venv`.
2. **Dependencias:** Instalar los requisitos: `pip install pandas opencv-python easyocr beautifulsoup4 requests`.
3. **Configuración:** Definir la `TEMPORADA` y `JORNADA` en el controlador `main.py`.
4. **Ejecución:** * Cargar capturas en `fuentes/capturas_raw/`.
    * Ejecutar el pipeline: `python main.py`.
    * Validar relaciones desconocidas en el prompt de la terminal para alimentar el `diccionario_jugadores.json`.

---
**Desarrollado con Python, OpenCV y pasión por la ingeniería de datos aplicada al deporte.**

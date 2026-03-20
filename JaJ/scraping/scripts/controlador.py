import time
import os
import sys

directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_raiz = os.path.dirname(os.path.dirname(os.path.dirname(directorio_actual)))
sys.path.append(directorio_raiz)

import pandas as pd
from crawler_url import obtener_urls_presente_jornada
# NUEVO: Importamos la función de clasificación
from scraper_motor import scrap_datos_entrenador, scrap_datos_alineaciones, scrap_datos_clasificacion
from auxiliar.comprobar_archivo import obtener_nombre_archivo_unico

def ejecutar_extraccion_previa(temporada, jornada):
    # --- CONFIGURACIÓN DINÁMICA DE RUTAS ---
    partes_temp = temporada.split('/')
    temp_corta = f"T{partes_temp[0][-2:]}-{partes_temp[1]}"

    ruta_base_entrenadores = os.path.join("datasets", "JaJ", temp_corta, f"J{jornada}", "entrenadores.csv")
    ruta_base_alineaciones = os.path.join("JaJ", "scraping", "datasets", temp_corta, f"J{jornada}", "jugadores.csv")
    
    # NUEVO: Definimos la ruta de la clasificación (misma carpeta que entrenadores)
    ruta_base_clasificacion = os.path.join("datasets", "JaJ", temp_corta, f"J{jornada}", "clasificacion.csv")

    print("=======================================================")
    print(f"  🚀 INICIANDO EXTRACCIÓN DUAL Y CLASIFICACIÓN - JORNADA {jornada} ({temporada})")
    print("=======================================================")

    # --- 1. EXTRACCIÓN DE CLASIFICACIÓN (Solo se hace 1 vez) ---
    print(f"🔍 Obteniendo datos de clasificación general...")
    datos_clasif = scrap_datos_clasificacion()
    if datos_clasif:
        print(f"       ✅ {len(datos_clasif)} Equipos extraídos.")
    
    # --- 2. EXTRACCIÓN DE PARTIDOS ---
    urls = obtener_urls_presente_jornada()
    
    if not urls:
        print("⚠️ No se han encontrado partidos.")
        return

    todos_entrenadores = []
    todos_jugadores = []

    for i, url in enumerate(urls, 1):
        nombre_partido = url.split('/')[-1]
        print(f"\n[{i}/10] Scrapeando partido: {nombre_partido}")
        
        # Extraer Entrenadores
        datos_mister = scrap_datos_entrenador(url, jornada, temporada)
        if datos_mister:
            todos_entrenadores.extend(datos_mister)
            print(f"       ✅ 2 Entrenadores extraídos.")
            
        # Extraer Jugadores
        datos_plantilla = scrap_datos_alineaciones(url, jornada, temporada)
        if datos_plantilla:
            todos_jugadores.extend(datos_plantilla)
            print(f"       ✅ {len(datos_plantilla)} Jugadores extraídos.")
        
        time.sleep(1.5) # Pausa Anti-ban

    # --- GUARDADO INTELIGENTE (Carpetas + Nombres Únicos) ---
    print("\n=======================================================")
    print("  💾 GUARDANDO ARCHIVOS...")
    print("=======================================================")

    # Guardado de CSV 1: Entrenadores
    if todos_entrenadores:
        dir_entrenadores = os.path.dirname(ruta_base_entrenadores)
        os.makedirs(dir_entrenadores, exist_ok=True)
        archivo_final_entrenadores = obtener_nombre_archivo_unico(ruta_base_entrenadores)
        df_entrenadores = pd.DataFrame(todos_entrenadores)
        df_entrenadores.to_csv(archivo_final_entrenadores, index=False, encoding='utf-8-sig')
        print(f"✔️ Guardado: {archivo_final_entrenadores} ({len(df_entrenadores)} filas)")

    # Guardado de CSV 2: Jugadores
    if todos_jugadores:
        dir_alineaciones = os.path.dirname(ruta_base_alineaciones)
        os.makedirs(dir_alineaciones, exist_ok=True)
        archivo_final_alineaciones = obtener_nombre_archivo_unico(ruta_base_alineaciones)
        df_jugadores = pd.DataFrame(todos_jugadores)
        df_jugadores.to_csv(archivo_final_alineaciones, index=False, encoding='utf-8-sig')
        print(f"✔️ Guardado: {archivo_final_alineaciones} ({len(df_jugadores)} filas)")

    # NUEVO: Guardado de CSV 3: Clasificación
    if datos_clasif:
        dir_clasif = os.path.dirname(ruta_base_clasificacion)
        os.makedirs(dir_clasif, exist_ok=True)
        archivo_final_clasif = obtener_nombre_archivo_unico(ruta_base_clasificacion)
        df_clasif = pd.DataFrame(datos_clasif)
        df_clasif.to_csv(archivo_final_clasif, index=False, encoding='utf-8-sig')
        print(f"✔️ Guardado: {archivo_final_clasif} ({len(df_clasif)} equipos)")

    print("\n=======================================================")
    print("  🏁 PROCESO COMPLETADO AL 100%")
    print("=======================================================")

if __name__ == "__main__":
    temporada = "2025/26"
    jornada = 29
    
    ejecutar_extraccion_previa(temporada, jornada)
import time
import os
import pandas as pd
from crawler_url import obtener_urls_presente_jornada
from scraper_motor import scrap_datos_entrenador, scrap_datos_alineaciones

def ejecutar_extraccion_previa(temporada, jornada):
    # --- CONFIGURACIÓN DINÁMICA DE RUTAS ---
    # Transformamos "2025/26" a formato corto "T25-26"
    partes_temp = temporada.split('/')
    temp_corta = f"T{partes_temp[0][-2:]}-{partes_temp[1]}"

    # Generamos la ruta de carpetas dinámica basada en los parámetros
    directorio_salida = os.path.join("datasets", "JaJ", temp_corta, f"J{jornada}")

    # Nombres finales de los archivos
    archivo_entrenadores = os.path.join(directorio_salida, "entrenadores.csv")
    archivo_alineaciones = os.path.join(directorio_salida, "jugadores.csv")

    print("=======================================================")
    print(f"  🚀 INICIANDO EXTRACCIÓN DUAL - JORNADA {jornada} ({temporada})")
    print("=======================================================")

    urls = obtener_urls_presente_jornada()
    
    if not urls:
        print("⚠️ No se han encontrado partidos.")
        return

    todos_entrenadores = []
    todos_jugadores = []

    for i, url in enumerate(urls, 1):
        nombre_partido = url.split('/')[-1]
        print(f"\n[{i}/10] Scrapeando partido: {nombre_partido}")
        
        # 1. Extraer Entrenadores
        datos_mister = scrap_datos_entrenador(url, jornada, temporada)
        if datos_mister:
            todos_entrenadores.extend(datos_mister)
            print(f"       ✅ 2 Entrenadores extraídos.")
            
        # 2. Extraer Jugadores
        datos_plantilla = scrap_datos_alineaciones(url, jornada, temporada)
        if datos_plantilla:
            todos_jugadores.extend(datos_plantilla)
            print(f"       ✅ {len(datos_plantilla)} Jugadores extraídos.")
        
        time.sleep(1.5) # Pausa Anti-ban

    # --- GUARDADO CON CREACIÓN DE CARPETAS ---
    # Esto creará 'datasets/JaJ/T25-26/J25' automáticamente si no existe
    os.makedirs(directorio_salida, exist_ok=True)

    # Guardado de CSV 1: Entrenadores
    if todos_entrenadores:
        df_entrenadores = pd.DataFrame(todos_entrenadores)
        df_entrenadores.to_csv(archivo_entrenadores, index=False, encoding='utf-8')
        print(f"\n💾 Guardado: {archivo_entrenadores} ({len(df_entrenadores)} filas)")

    # Guardado de CSV 2: Jugadores
    if todos_jugadores:
        df_jugadores = pd.DataFrame(todos_jugadores)
        df_jugadores.to_csv(archivo_alineaciones, index=False, encoding='utf-8')
        print(f"💾 Guardado: {archivo_alineaciones} ({len(df_jugadores)} filas)")

    print("\n=======================================================")
    print("  🏁 PROCESO COMPLETADO AL 100%")
    print("=======================================================")

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    # Ahora defines los valores aquí al llamar a la función
    temporada = "2025/26"
    joranda = 25
    
    ejecutar_extraccion_previa(temporada, joranda)
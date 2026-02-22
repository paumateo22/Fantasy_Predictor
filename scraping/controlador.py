import time
import pandas as pd
import os
from scraping.crawler_url import obtener_partidos_jornada
from scraping.scraper_motor import scrap_puntos_fantasy 

ARCHIVO_CSV = "prueba_jornada_actual.csv"

# Diccionario traductor para arreglar el desfase de URLs de FutbolFantasy
MAPA_URLS_TEMPORADA = {
    "2023/24": "2024-25",
    "2024/25": "2025-26",
    "2025/26": "2026-27"
}

def ejecutar_temporada_completa(tareas):
    # Cargar CSV existente para evitar duplicados
    if os.path.exists(ARCHIVO_CSV):
        df_existente = pd.read_csv(ARCHIVO_CSV)
    else:
        df_existente = pd.DataFrame(columns=["ID_Partido", "Temporada", "Jornada", "Local", "Visitante", "Jugador", "Puntos"])

    # Iteramos sobre el diccionario que mandas desde main.py
    for temporada, config in tareas.items():
        inicio = config[0]
        fin = config[1]
        jornadas_saltar = config[2]
        
        # Obtenemos el "slug" para la URL (ej: "2025-26")
        slug_temporada = MAPA_URLS_TEMPORADA.get(temporada, "2026-27")

        print(f"\n=======================================================")
        print(f"  INICIANDO TEMPORADA {temporada} (Ruta URL: {slug_temporada})")
        print(f"=======================================================")

        for j in range(inicio, fin + 1):
            # Comprobamos si la jornada está en la lista de ignoradas
            if j in jornadas_saltar:
                print(f"\n--- ⏭️ Saltando Jornada {j} por configuración ---")
                continue

            print(f"\n--- ⚽ Trabajando en la Jornada {j} ---")
            
            # Pasamos la jornada Y el slug de la temporada al crawler
            urls = obtener_partidos_jornada(j, slug_temporada)
            
            if not urls:
                print(f"No se encontraron URLs para la Jornada {j}. Saltando...")
                continue
                
            datos_nuevos_jornada = []
            
            for url in urls:
                nombre_partido = url.split('-', 1)[1] if '-' in url else url.split('/')[-1]
                print(f"  -> Scrapeando: {nombre_partido}")
                
                try:
                    partido_data = scrap_puntos_fantasy(url, j, temporada)
                    
                    if partido_data:
                        loc = partido_data[0].get("Local", "Local")
                        vis = partido_data[0].get("Visitante", "Visitante")

                        # Control de partidos no jugados
                        if loc == "Local" or vis == "Visitante" or not loc or not vis:
                            print("     -> ❌ Partido no encontrado o no jugado (omitido)")
                            continue

                        # Comprobación de duplicados (Misma Temporada, Jornada, Local y Visitante)
                        duplicado = False
                        if not df_existente.empty:
                            filtro_duplicado = df_existente[
                                (df_existente["Temporada"].astype(str) == str(temporada)) & 
                                (df_existente["Jornada"].astype(int) == int(j)) & 
                                (df_existente["Local"] == loc) & 
                                (df_existente["Visitante"] == vis)
                            ]
                            if not filtro_duplicado.empty:
                                duplicado = True

                        if duplicado:
                            print(f"     ⚠️ Omitido: Partido ya existe en el CSV ({loc} vs {vis})")
                        else:
                            datos_nuevos_jornada.extend(partido_data)
                            # Añadimos a la memoria temporal para evitar repetidos en la misma tanda
                            df_nuevo = pd.DataFrame(partido_data)
                            df_existente = pd.concat([df_existente, df_nuevo], ignore_index=True)
                            print(f"     ✅ Extraído: {loc} vs {vis}")

                except Exception as e:
                    print(f"     !!! Error en este partido: {e}")
                
                time.sleep(1.5) # Anti-Ban de servidor
            
            # Guardado final de la jornada procesada
            if datos_nuevos_jornada:
                df_guardar = pd.DataFrame(datos_nuevos_jornada)
                
                if not os.path.exists(ARCHIVO_CSV):
                    df_guardar.to_csv(ARCHIVO_CSV, mode='w', index=False, header=True)
                else:
                    df_guardar.to_csv(ARCHIVO_CSV, mode='a', index=False, header=False)
                    
                print(f"💾 Jornada {j} finalizada. {len(df_guardar)} nuevas filas guardadas.")
            else:
                print(f"ℹ️ Ningún dato nuevo para guardar en la Jornada {j}.")
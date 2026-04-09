import time
import pandas as pd
import os
from crawler_url import obtener_partidos_jornada
from scraper_motor import scrap_puntos_fantasy 

# Diccionario traductor para arreglar el desfase de URLs de FutbolFantasy
MAPA_URLS_TEMPORADA = {
    "23-24": "2024-25",
    "24-25": "2025-26",
    "25-26": "2026-27"
}
def ejecutar_temporada_completa(tareas):
    # Base para movernos por las carpetas (apunta a la carpeta pasado)
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    dir_raiz = os.path.dirname(os.path.dirname(directorio_actual)) 

    # 🚨 NUEVO: Lista para guardar los registros de los partidos que fallen
    partidos_fallidos = []

    # Iteramos sobre el diccionario que mandas desde main.py
    for temporada, config in tareas.items():
        inicio = config[0]
        fin = config[1]
        jornadas_saltar = config[2]
        
        # Obtenemos el "slug" para la URL de la web (ej: "2025-26")
        slug_temporada = MAPA_URLS_TEMPORADA.get(temporada, "2026-27")
        
        # Formateamos el nombre de tu carpeta local (ej: "T25-26")
        temporada_str = f"T{temporada.replace('/', '-')}"

        print(f"\n=======================================================")
        print(f"  INICIANDO TEMPORADA {temporada} (Ruta URL: {slug_temporada})")
        print(f"=======================================================")

        for j in range(inicio, fin + 1):
            if j in jornadas_saltar:
                print(f"\n--- ⏭️ Saltando Jornada {j} por configuración ---")
                continue

            print(f"\n--- ⚽ Trabajando en la Jornada {j} ---")
            
            jornada_str = f"J{j}"
            dir_salida = os.path.join(dir_raiz, "scraping_puntos", "datasets", temporada_str)
            os.makedirs(dir_salida, exist_ok=True)
            
            ruta_csv = os.path.join(dir_salida, f"{jornada_str}_puntos.csv")
            
            if os.path.exists(ruta_csv):
                df_existente = pd.read_csv(ruta_csv)
            else:
                df_existente = pd.DataFrame()

            # Pasamos la jornada Y el slug de la temporada al crawler
            urls = obtener_partidos_jornada(j, slug_temporada)
            
            if not urls:
                print(f"No se encontraron URLs para la Jornada {j}. Saltando...")
                # 🚨 NUEVO: Registramos que la jornada entera falló
                partidos_fallidos.append(f"Temporada {temporada} | Jornada {j} | FALLO CRÍTICO: No se encontraron URLs")
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
                            partidos_fallidos.append(f"Temporada {temporada} | Jornada {j} | {nombre_partido} | OMITIDO: No jugado o vacío")
                            continue

                        # Comprobación de duplicados en este archivo
                        duplicado = False
                        if not df_existente.empty:
                            filtro_duplicado = df_existente[
                                (df_existente["Temporada"].astype(str) == str(temporada)) & 
                                (df_existente["Jornada"].astype(str) == str(j)) & 
                                (df_existente["Local"] == loc) & 
                                (df_existente["Visitante"] == vis)
                            ]
                            if not filtro_duplicado.empty:
                                duplicado = True

                        if duplicado:
                            print(f"     ⚠️ Omitido: Partido ya existe en el CSV ({loc} vs {vis})")
                        else:
                            datos_nuevos_jornada.extend(partido_data)
                            df_nuevo = pd.DataFrame(partido_data)
                            df_existente = pd.concat([df_existente, df_nuevo], ignore_index=True) if not df_existente.empty else df_nuevo
                            print(f"     ✅ Extraído: {loc} vs {vis}")

                except Exception as e:
                    print(f"     !!! Error en este partido: {e}")
                    # 🚨 NUEVO: Registramos el error de este partido concreto
                    partidos_fallidos.append(f"Temporada {temporada} | Jornada {j} | {nombre_partido} | ERROR: {e}")
                
                time.sleep(1.5) # Anti-Ban de servidor
            
            # Guardado final de la jornada procesada
            if datos_nuevos_jornada:
                df_existente.to_csv(ruta_csv, index=False, encoding='utf-8-sig')
                print(f"💾 Jornada {j} finalizada. {len(datos_nuevos_jornada)} nuevas filas guardadas en {ruta_csv}")
            else:
                print(f"ℹ️ Ningún dato nuevo para guardar en la Jornada {j}.")

    # 🚨 NUEVO: REPORTE FINAL Y CREACIÓN DEL TXT
    print("\n=======================================================")
    if not partidos_fallidos:
        print(" 🏆 EXTRACCIÓN LIMPIA: 0 errores registrados.")
    else:
        ruta_txt = os.path.join(dir_raiz, "scraping_puntos", "errores_scraping_puntos.txt")
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write("=== REGISTRO DE PARTIDOS FALLIDOS ===\n\n")
            for error in partidos_fallidos:
                f.write(f"- {error}\n")
                
        print(f" ⚠️ PROCESO TERMINADO CON AVISOS: Hubo problemas en {len(partidos_fallidos)} partidos/jornadas.")
        print(f" 📝 Se ha generado el reporte de fallos en: {ruta_txt}")
    print("=======================================================")
    
if __name__ == "__main__":
    
    tareas_a_ejecutar = {
        "25-26": [30, 30, []]
    }
    
    print("\n🚀 INICIANDO EL MOTOR DE SCRAPING DE PUNTOS FANTASY 🚀")
    ejecutar_temporada_completa(tareas_a_ejecutar)
    print("\n✅ ¡PROCESO GLOBAL DE EXTRACCIÓN DE PUNTOS COMPLETADO! ✅")
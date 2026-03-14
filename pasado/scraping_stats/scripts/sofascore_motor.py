import pandas as pd
import os
import time
from curl_cffi import requests

# --- 1. EL MINERO (Extractor de datos de un partido) ---
def extraer_stats_partido(match_id, temporada, jornada):
    """
    Extrae todas las estadísticas fantasy de un partido y las devuelve como lista de diccionarios,
    incluyendo el nombre del equipo real.
    """
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/lineups"
    
    headers = {
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }
    
    print(f"🌐 Extrayendo datos del partido {match_id}...")
    
    # Usa impersonate="chrome110" si usas curl_cffi. Si no, quítalo.
    respuesta = requests.get(url, headers=headers, impersonate="chrome110")
    
    if respuesta.status_code != 200:
        print(f"❌ Error al conectar con la API: {respuesta.status_code}")
        return [] 

    datos = respuesta.json()
    jugadores_procesados = []
    
    # 🚨 NUEVO: Extraemos los nombres de los equipos desde un endpoint secundario
    # SofaScore a veces no pone el nombre del equipo en el endpoint de 'lineups'. 
    # Para ser 100% seguros, hacemos una llamada rápida al resumen del partido.
    url_info = f"https://api.sofascore.com/api/v1/event/{match_id}"
    res_info = requests.get(url_info, headers=headers, impersonate="chrome110")
    
    nombre_local = "Desconocido"
    nombre_visitante = "Desconocido"
    
    if res_info.status_code == 200:
        info_partido = res_info.json().get('event', {})
        nombre_local = info_partido.get('homeTeam', {}).get('name', 'Desconocido')
        nombre_visitante = info_partido.get('awayTeam', {}).get('name', 'Desconocido')

    # Iteramos sobre los dos equipos
    for bando in ['home', 'away']:
        if bando not in datos or 'players' not in datos[bando]:
            continue
            
        # 🚨 NUEVO: Asignamos el nombre correcto según el bando
        equipo_real = nombre_local if bando == 'home' else nombre_visitante
            
        for item in datos[bando]['players']:
            jugador = item.get('player', {})
            stats = item.get('statistics', {})
            
            nombre = jugador.get('name', 'Desconocido')
            posicion = item.get('position', 'Desconocido')
            
            fila = {
                "ID_Partido": match_id,
                "Temporada": temporada,
                "Jornada": jornada,
                "Equipo_Bando": "Local" if bando == 'home' else "Visitante",
                "Equipo_Nombre": equipo_real, # <--- AÑADIDO AQUÍ
                "Jugador": nombre,
                "Posicion": posicion,
                
                # Acciones Generales y Ofensivas
                "Minutos_jugados": stats.get('minutesPlayed', 0),
                "Goles": stats.get('goals', 0),
                "Asistencias_de_gol": stats.get('goalAssist', 0),
                "Asistencias_sin_gol": stats.get('keyPass', 0),
                "Balones_al_area": stats.get('accurateCross', 0),
                "Tiros_a_puerta": stats.get('onTargetScoringAttempt', 0),
                "Regates": stats.get('successfulDribbles', 0),
                
                # Acciones Defensivas y Portero
                "Balones_recuperados": stats.get('ballRecovery', 0),
                "Despejes": stats.get('totalClearance', 0),
                "Paradas": stats.get('saves', 0),
                "Goles_en_contra": stats.get('goalsConceded', 0),
                
                # Penaltis y Sanciones
                "Penaltis_provocados": stats.get('penaltyWon', 0),
                "Penaltis_cometidos": stats.get('penaltyConceded', 0),
                "Penaltis_parados": stats.get('penaltySave', 0),
                "Penaltis_fallados": stats.get('penaltyMiss', 0),
                "Goles_en_propia_puerta": stats.get('ownGoals', 0),
                
                # Tarjetas y Pérdidas
                "Amarillas": stats.get('yellowCards', 0),
                "Rojas": stats.get('redCards', 0),
                "Posesiones_perdidas": stats.get('possessionLostCtrl', 0),
                
                # Rating SofaScore
                "Nota_SofaScore": stats.get('rating', 0.0)
            }
            
            if fila["Minutos_jugados"] > 0:
                jugadores_procesados.append(fila)

    return jugadores_procesados

# --- 2. EL CAPATAZ (Controlador que recibe la lista) ---
def procesar_lista_partidos(lista_ids, temporada, jornada):
    """
    Recorre una lista de IDs de partidos, junta todos los datos y guarda un único CSV.
    """
    print(f"\n🚀 Iniciando extracción de SofaScore | {temporada} - {jornada}")
    print("="*60)
    
    todos_los_datos = []
    
    for i, match_id in enumerate(lista_ids, 1):
        print(f"[{i}/{len(lista_ids)}] Scrapeando partido ID: {match_id}...")
        
        datos_partido = extraer_stats_partido(match_id, temporada, jornada)
        
        if datos_partido:
            todos_los_datos.extend(datos_partido)
            print(f"    ✅ {len(datos_partido)} jugadores extraídos.")
        
        # 🚨 PAUSA VITAL: Esperamos 1 segundo entre partido y partido para no saturar la API
        time.sleep(1)
        
    # --- GUARDADO FINAL (ESTRUCTURA PLANA POR TEMPORADA) ---
    if todos_los_datos:
        df = pd.DataFrame(todos_los_datos)
        
        # Navegamos hasta pasado/scraping_stats/datasets/Temporada/
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        dir_raiz = os.path.dirname(os.path.dirname(directorio_actual)) 
        
        # 🚨 CAMBIO AQUÍ: La carpeta de salida es solo la temporada
        dir_salida = os.path.join(dir_raiz, "scraping_stats", "datasets", temporada)
        
        os.makedirs(dir_salida, exist_ok=True)
        
        # 🚨 CAMBIO AQUÍ: El nombre del archivo incluye la jornada (Ej: J24_stats.csv)
        nombre_archivo = f"{jornada}_stats.csv"
        ruta_csv = os.path.join(dir_salida, nombre_archivo)
        
        df.to_csv(ruta_csv, index=False, encoding='utf-8-sig')
        
        print("="*60)
        print(f"🏁 ¡Proceso completado! Archivo final: {ruta_csv} ({len(df)} filas)")
    else:
        print("\n⚠️ No se extrajeron datos de ningún partido.")

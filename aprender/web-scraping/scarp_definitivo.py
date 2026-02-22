import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

url = "https://www.futbolfantasy.com/partidos/20311-real-oviedo-athletic"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def limpiar_nombre_equipo(texto):
    if not texto: return "Desconocido"
    # Eliminamos "Puntos", "del" y cualquier espacio extra o tabulación
    limpio = texto.replace("Puntos", "").replace("del", "").strip()
    # A veces hay dobles espacios, los colapsamos
    limpio = " ".join(limpio.split())
    return limpio

try:
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # --- 1. EXTRAER INFORMACIÓN DE CONTEXTO ---
    match_id = re.search(r'/partidos/(\d+)-', url).group(1)
    
    texto_pagina = soup.get_text()
    jornada = re.search(r'Jornada\s*(\d+)', texto_pagina, re.IGNORECASE).group(1)
    
    # Equipos (Limpiando el "Puntos del ")
    titulos = soup.select('h2.title')
    local = limpiar_nombre_equipo(titulos[0].text) if len(titulos) >= 1 else "Local"
    visitante = limpiar_nombre_equipo(titulos[1].text) if len(titulos) >= 2 else "Visitante"

    # --- 2. PROCESAR JUGADORES ---
    datos_jugadores = []
    bloques_jugadores = soup.select('.juggador')
    
    for jugador in bloques_jugadores:
        nombre_elem = jugador.select_one('.truncate-name')
        if not nombre_elem: continue
        
        # Nombre limpio (sin minutos de cambio)
        nombre = nombre_elem.text.strip().split('\n')[0].strip()
        
        # Puntos oficiales
        span_puntos = jugador.select_one('span[data-juego="laliga-fantasy"]')
        puntos = 0
        if span_puntos:
            txt = span_puntos.text.strip()
            if txt.lstrip('-').isdigit(): puntos = int(txt)
            
        datos_jugadores.append({
            "ID_Partido": match_id,
            "Temporada": "2025/26",
            "Jornada": jornada,
            "Local": local,
            "Visitante": visitante,
            "Jugador": nombre,
            "Puntos": puntos
        })

    # 3. GENERAR EL CSV LIMPIO
    if datos_jugadores:
        df = pd.DataFrame(datos_jugadores)
        
        # Definimos el orden de las columnas (Sin Nombre_Partido)
        columnas = ["ID_Partido", "Temporada", "Jornada", "Local", "Visitante", "Jugador", "Puntos"]
        df = df[columnas]
        
        print("\n--- Vista previa del Dataset Limpio ---")
        print(df.head())
        
        df.to_csv("dataset_fantasy_ia_v1.csv", index=False)
        print("\n¡Éxito! CSV guardado como 'dataset_fantasy_ia_v1.csv'")
    else:
        print("No se encontraron jugadores.")

except Exception as e:
    print(f"Error: {e}")
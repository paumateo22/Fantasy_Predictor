import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL del partido
url = "https://www.futbolfantasy.com/partidos/20311-real-oviedo-athletic"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print(f"Procesando: {url}")

try:
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    datos_jugadores = []
    
    # Seleccionamos todos los bloques de jugadores
    bloques_jugadores = soup.select('.juggador')
    
    print(f"Analizando {len(bloques_jugadores)} jugadores...")

    for jugador in bloques_jugadores:
        # 1. NOMBRE
        nombre_elem = jugador.select_one('.truncate-name')
        if not nombre_elem: continue
        
        nombre = nombre_elem.text.strip()
        
        # 2. PUNTOS (Solo LaLiga Fantasy)
        # Buscamos DIRECTAMENTE el span de LaLiga Fantasy
        span_puntos = jugador.select_one('span[data-juego="laliga-fantasy"]')
        
        puntos = 0 # Valor por defecto
        
        if span_puntos:
            texto = span_puntos.text.strip()
            # Limpieza: Si es número lo guardamos, si es guion es 0
            if texto.lstrip('-').isdigit(): # lstrip para aceptar negativos como -2
                puntos = int(texto)
            
        # 3. GUARDAR
        # Guardamos solo lo que nos interesa
        datos_jugadores.append({
            "Jugador": nombre,
            "Puntos": puntos
        })

    # Generar CSV
    if datos_jugadores:
        df = pd.DataFrame(datos_jugadores)
        
        print("\n¡Extracción completada!")
        print(df.head()) 
        
        # Guardamos con un nombre claro
        archivo_salida = "puntos_fantasy_laliga.csv"
        df.to_csv(archivo_salida, index=False)
        print(f"\nDatos guardados en: {archivo_salida}")
    else:
        print("No se encontraron jugadores.")

except Exception as e:
    print(f"Error: {e}")
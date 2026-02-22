import requests
from bs4 import BeautifulSoup
import re

# Diccionario para guardar en memoria RAM (caché) los calendarios y no saturar la web
CACHE_CALENDARIOS = {}

def obtener_partidos_jornada(numero_jornada, slug_temporada):
    
    # 1. Si no tenemos la temporada cargada en memoria, la descargamos entera
    if slug_temporada not in CACHE_CALENDARIOS:
        url = f"https://www.futbolfantasy.com/laliga/calendario/{slug_temporada}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        print(f"    [!] Descargando calendario completo de {slug_temporada} a la memoria caché...")
        
        try:
            r = requests.get(url, headers=headers)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            enlaces_partidos = []
            
            # Buscamos todos los enlaces de partidos de la temporada
            enlaces = soup.find_all('a', href=re.compile(r'/partidos/\d+'))
            
            for a in enlaces:
                link = a['href']
                if not link.startswith('http'):
                    link = "https://www.futbolfantasy.com" + link
                
                # Guardamos sin duplicar, respetando el orden cronológico estricto de la web
                if link not in enlaces_partidos:
                    enlaces_partidos.append(link)
            
            # Guardamos la lista gigante en nuestra caché
            CACHE_CALENDARIOS[slug_temporada] = enlaces_partidos
            print(f"    [!] ¡Calendario guardado en RAM! {len(enlaces_partidos)} partidos listos.")
            
        except Exception as e:
            print(f"    [!] Error crítico al descargar el calendario de {slug_temporada}: {e}")
            return []

    # 2. Rescatamos la lista completa de partidos de la memoria
    todos_los_partidos = CACHE_CALENDARIOS.get(slug_temporada, [])
    
    if not todos_los_partidos:
        return []

    # 3. Matemática de recorte (Slicing)
    # Como los primeros 380 son LaLiga perfecta:
    # Jornada 1: (1-1)*10 = 0 -> fin: 1*10 = 10 (coge del 0 al 9)
    # Jornada 38: (38-1)*10 = 370 -> fin: 38*10 = 380 (coge del 370 al 379)
    inicio = (numero_jornada - 1) * 10
    fin = numero_jornada * 10
    
    # Recortamos exactamente los 10 de la jornada que nos pide el controlador
    partidos_recortados = todos_los_partidos[inicio:fin]
    
    return partidos_recortados
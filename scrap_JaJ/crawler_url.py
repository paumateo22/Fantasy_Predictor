import requests
from bs4 import BeautifulSoup
import re

def obtener_urls_presente_jornada():
    # URL directa a la jornada actual (la que está por jugarse)
    url = "https://www.futbolfantasy.com/laliga/posibles-alineaciones"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        print(f"🔍 Conectando a {url} para buscar la jornada actual...")
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        enlaces_partidos = []
        
        # Buscamos todos los enlaces que lleven a la estructura de un partido
        enlaces = soup.find_all('a', href=re.compile(r'/partidos/\d+'))
        
        for a in enlaces:
            link = a['href']
            if not link.startswith('http'):
                link = "https://www.futbolfantasy.com" + link
            
            # Evitamos URLs repetidas
            if link not in enlaces_partidos:
                enlaces_partidos.append(link)
        
        # La página tiene enlaces a otros partidos pasados/futuros más abajo,
        # pero los 10 primeros son estrictamente los de la jornada presente.
        partidos_finales = enlaces_partidos[:10]
        
        print(f"✅ ¡Éxito! Se han detectado {len(partidos_finales)} partidos de la jornada.")
        return partidos_finales

    except Exception as e:
        print(f"❌ Error al obtener las URLs: {e}")
        return []

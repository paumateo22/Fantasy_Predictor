import requests
from bs4 import BeautifulSoup
import re

def scrap_puntos_fantasy(url, jornada, temporada):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 1. Metadatos
        match_search = re.search(r'/partidos/(\d+)-', url)
        match_id = match_search.group(1) if match_search else "0"

        # 2. Extracción Global de Equipos
        titulos = soup.select('h2.title')
        
        def limpiar_equipo(texto):
            return re.sub(r'^Puntos.*? de[l]?\s+', '', texto.strip())

        local = limpiar_equipo(titulos[0].text) if len(titulos) >= 1 else "Local"
        visitante = limpiar_equipo(titulos[1].text) if len(titulos) >= 2 else "Visitante"

        if local == "Local" or visitante == "Visitante" or not local or not visitante:
            print("     -> ❌ Partido no encontrado o no jugado (omitido)")
            return []

        datos = []
        
        # 3. Iterar por cada bloque
        for selector, nombre_equipo, es_local in [('.stats-local', local, 1), (('.stats-visitante'), visitante, 0)]:
            bloque = soup.select_one(selector)
            if not bloque:
                continue
                
            for fila_jugador in bloque.select('tr.plegable'):
                
                td_name = fila_jugador.select_one('td.name')
                if not td_name:
                    continue
                    
                # --- A. JUGADOR (Limpieza de minutos) ---
                nombre = td_name.text.strip()
                nombre = re.sub(r'\s+', ' ', nombre)
                # Esta línea elimina " 76'", " 45'", " 90+2'", etc.
                nombre = re.sub(r"\s+\d+(\+\d+)?'$", "", nombre)
                
                # --- B. POSICIÓN ---
                posicion = td_name.get('data-posicion-laliga-fantasy', 'Desconocido')
                
                # --- C. PUNTOS FANTASY ---
                span_puntos = fila_jugador.select_one('span.laliga-fantasy')
                puntos = 0
                if span_puntos:
                    txt = span_puntos.text.strip()
                    if txt.lstrip('-').isdigit():
                        puntos = int(txt)
                        
                # --- D. PUNTOS RELEVO ---
                # Lo sacamos directo del 'td' de relevo en la tabla principal
                td_relevo = fila_jugador.select_one('td.relevo')
                puntos_relevo = 0
                if td_relevo:
                    txt_relevo = td_relevo.text.strip()
                    if txt_relevo.lstrip('-').isdigit():
                        puntos_relevo = int(txt_relevo)
                
                # Guardamos la fila con la estructura exacta que has pedido
                datos.append({
                    "ID_Partido": match_id,
                    "Temporada": temporada,
                    "Jornada": jornada,
                    "Local": local,
                    "Visitante": visitante,
                    "Equipo_Jugador": nombre_equipo,
                    "Es_Local": es_local,
                    "Jugador": nombre,
                    "Posicion": posicion,
                    "Puntos": puntos,
                    "Relevo": puntos_relevo
                })
                
        return datos

    except Exception as e:
        print(f"Error en {url}: {e}")
        return []
from curl_cffi import requests

def obtener_ids_jornada_sofascore(id_temporada_sofa, jornada_num):
    """
    Se conecta a la API de SofaScore y extrae la lista de IDs de los 10 partidos de una jornada.
    id_temporada_sofa: El código interno que usa SofaScore para cada año de LaLiga (ej. 52376 para la 23/24).
    jornada_num: El número de la jornada (ej. 1, 12, 38).
    """
    # 8 es el ID fijo de la liga española en SofaScore
    url = f"https://api.sofascore.com/api/v1/unique-tournament/8/season/{id_temporada_sofa}/events/round/{jornada_num}"
    
    headers = {
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }
    
    print(f"🔍 Buscando IDs de la jornada {jornada_num}...")
    
    try:
        respuesta = requests.get(url, headers=headers, impersonate="chrome110")
        
        if respuesta.status_code != 200:
            print(f"❌ Error al obtener los IDs: Estado {respuesta.status_code}")
            return []
            
        datos = respuesta.json()
        
        # SofaScore guarda la lista de partidos en la clave 'events'
        eventos = datos.get('events', [])
        
        # Extraemos solo el ID numérico de cada evento
        lista_ids = [str(partido['id']) for partido in eventos]
        
        print(f"✅ ¡Éxito! Encontrados {len(lista_ids)} partidos.")
        return lista_ids
        
    except Exception as e:
        print(f"❌ Error inesperado en el crawler: {e}")
        return []

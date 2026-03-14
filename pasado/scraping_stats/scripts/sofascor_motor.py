from curl_cffi import requests

def ver_todas_estadisticas_sofascore(match_id):
    # Endpoint de la API
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/lineups"
    
    # Cabeceras que simulan que venimos navegando desde su web oficial
    headers = {
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }
    
    print(f"🌐 Interceptando JSON del partido {match_id} (Camuflaje TLS activado)...\n")
    
    # 🚨 LA MAGIA: impersonate="chrome110" burla el bloqueo 403 de la API
    respuesta = requests.get(url, headers=headers, impersonate="chrome110")
    
    if respuesta.status_code == 200:
        datos = respuesta.json()
        
        # Navegamos por el JSON: Equipo Local -> Lista de Jugadores -> Primer Jugador Titular
        primer_jugador = datos['home']['players'][5]
        
        nombre = primer_jugador['player']['name']
        posicion = primer_jugador['position']
        
        # El diccionario completo de estadísticas de ese partido
        stats = primer_jugador['statistics']
        
        print(f"⚽ ESTADÍSTICAS COMPLETAS DE: {nombre} (Posición: {posicion})")
        print("="*60)
        
        # Iteramos e imprimimos cada métrica y su valor
        for metrica, valor in stats.items():
            print(f" 🔸 {metrica}: {valor}")
            
        print("="*60)
        print(f"📊 Total de métricas trackeadas en este partido: {len(stats)}")
        
    else:
        print(f"❌ Error al conectar con la API: {respuesta.status_code}")
        print("Cuerpo del error:", respuesta.text[:200]) # Para ver qué nos dice si falla

if __name__ == "__main__":
    # ID de un partido real
    id_partido_prueba = "11369438" 
    
    ver_todas_estadisticas_sofascore(id_partido_prueba)
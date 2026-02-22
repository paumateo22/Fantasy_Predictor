import requests
from bs4 import BeautifulSoup

url = "https://www.futbolfantasy.com/partidos/20311-real-oviedo-athletic"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print(f"Descargando y recortando: {url}")

try:
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    

    jugadores = soup.select('.juggador') # En FutbolFantasy tienen la clase juggador con 2 g
    
    print(f"He encontrado {len(jugadores)} jugadores")
    
    if len(jugadores) > 0:
        # Guardamos solo esos trozos en un archivo nuevo
        with open("solo_jugadores.html", "w", encoding="utf-8") as f:
            f.write(f"\n")
            
            for i, jugador in enumerate(jugadores):
                f.write(f"\n\n--- JUGADOR {i+1} ---\n")
                f.write(jugador.prettify())
                
        print("Proceso terminado")
    else:
        print("No encontré ningún elemento con la clase '.juggador'")

except Exception as e:
    print(f"Error: {e}")
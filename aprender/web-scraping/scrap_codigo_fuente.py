import requests

url = "https://www.futbolfantasy.com/partidos/20311-real-oviedo-athletic"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print(f'Descargando el código fuente de: {url}')

try:
    response = requests.get(url)

    if response.status_code == 200:
        nombre_archivo = "radiografia_partido.html"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f'Se ha guardado el archivo: {nombre_archivo}')

    else:
        print(f'Error al descargar: {response.status_code}')
    
except Exception as e:
    print(f'Ocurrió un error: {e}')
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from curl_cffi import requests as curl_requests

def extraer_nombres_equipos(soup):
    """Busca los nombres de los equipos de forma robusta con varios métodos de respaldo."""
    # 1. Intentamos con selectores CSS más amplios (por si han quitado la clase '.team')
    elem_local = soup.select_one('.local .name, .equipo.local, .local .nombre-equipo')
    elem_visit = soup.select_one('.visitante .name, .equipo.visitante, .visitante .nombre-equipo')
    
    local = elem_local.text.strip() if elem_local else ""
    visitante = elem_visit.text.strip() if elem_visit else ""
    
    # 2. Si falla el HTML interno, leemos el <title> de la pestaña (Ej: "Alineaciones probables Getafe - Rayo Vallecano | ...")
    if not local or not visitante:
        titulo = soup.title.string if soup.title else ""
        # Buscamos el patrón típico "EquipoA - EquipoB"
        match_tit = re.search(r'(.*?)\s+-\s+(.*?)\s+(?:\||en)', titulo)
        if match_tit:
            # Limpiamos palabras extra que suelen venir en el título
            local = re.sub(r'Alineaciones probables|Previa|Onces', '', match_tit.group(1), flags=re.IGNORECASE).strip()
            visitante = match_tit.group(2).strip()
        else:
            local, visitante = "Local", "Visitante"
            
    return local, visitante

def scrap_datos_entrenador(url, jornada, temporada):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        match_search = re.search(r'/partidos/(\d+)-', url)
        match_id = match_search.group(1) if match_search else "0"
        
        local, visitante = extraer_nombres_equipos(soup)

        datos_entrenadores = []
        bloques = [('.alineacion_superwrapper.local', local, 1), ('.alineacion_superwrapper.visitante', visitante, 0)]
        
        for selector, nombre_equipo, es_local in bloques:
            bloque = soup.select_one(selector)
            if not bloque: continue
                
            entrenador_elem = bloque.select_one('.nombre-entrenador')
            entrenador = entrenador_elem.text.strip() if entrenador_elem else "Desconocido"
            
            rotaciones = "Desconocido"
            previsib_jornada = "Desconocido"
            previsib_temp = "Desconocido"
            
            columnas_titulo = bloque.select('.col-5')
            for col_titulo in columnas_titulo:
                texto_label = col_titulo.text.strip().lower()
                col_valor = col_titulo.find_next_sibling('div', class_=re.compile('col-7'))
                
                if col_valor:
                    valor_final = ""
                    barra = col_valor.select_one('.prevision')
                    if barra and barra.has_attr('style'):
                        match_width = re.search(r'width:\s*([\d.]+)%', barra['style'])
                        if match_width: valor_final = match_width.group(1) + "%"
                    
                    if not valor_final:
                        porcentaje_elem = col_valor.select_one('.porcentaje')
                        valor_final = porcentaje_elem.text.strip() if porcentaje_elem else ""
                    
                    if valor_final:
                        if 'rotacion' in texto_label: rotaciones = valor_final
                        elif 'previsib' in texto_label and 'j' in texto_label: previsib_jornada = valor_final
                        elif 'temp' in texto_label: previsib_temp = valor_final
                            
            datos_entrenadores.append({
                "ID_Partido": match_id,
                "Temporada": temporada,
                "Jornada": jornada,
                "Equipo": nombre_equipo,
                "Es_Local": es_local,
                "Entrenador": entrenador,
                "Rotaciones": rotaciones,
                "Previsibilidad_Jornada": previsib_jornada,
                "Previsibilidad_Temporada": previsib_temp
            })
            
        return datos_entrenadores
    except Exception as e:
        print(f"❌ Error procesando {url}: {e}")
        return []


def scrap_datos_alineaciones(url, jornada, temporada):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        match_search = re.search(r'/partidos/(\d+)-', url)
        match_id = match_search.group(1) if match_search else "0"
        
        local, visitante = extraer_nombres_equipos(soup)

        datos_jugadores = []
        for selector, nombre_equipo in [('.local .camiseta-wrapper', local), ('.visitante .camiseta-wrapper', visitante)]:
            bloques_jugador = soup.select(selector)
            
            for bloque in bloques_jugador:
                nombre_elem = bloque.select_one('.truncate-name')
                nombre = nombre_elem.text.strip() if nombre_elem else "Desconocido"
                
                a_tag = bloque.select_one('a.camiseta')
                if not a_tag: continue
                
                clases = bloque.get('class', [])
                posicion = "Desconocido"
                if 'portero' in clases: posicion = "Portero"
                elif 'defensa' in clases: posicion = "Defensa"
                elif 'medio' in clases or 'centrocampista' in clases: posicion = "Mediocampista"
                elif 'delantero' in clases: posicion = "Delantero"

                edad = a_tag.get('data-edad', '0')
                nacionalidad = a_tag.get('data-nacionalidad', 'Desconocido')
                probabilidad = a_tag.get('data-probabilidad', '0%')
                lesion_val = a_tag.get('data-lesion', '-1')
                estado_medico = "Sano" if lesion_val == "-1" else "Lesionado/Duda"

                pj = a_tag.get('data-totalpartidosjugados', '0')
                goles = a_tag.get('data-totalgoles', '0')
                asist = a_tag.get('data-totalasistencias', '0')
                penaltis = a_tag.get('data-totalpenalpar', '0')
                ta = a_tag.get('data-totalamarillas', '0')
                tr = a_tag.get('data-totalrojas', '0')
                forma = a_tag.get('data-forma-value', '0')

                puntos_totales = "0"
                elem_totales = bloque.select_one('.forma-left.view.puntos span[data-juego="laliga-fantasy"]')
                if elem_totales: puntos_totales = elem_totales.text.strip()

                media_puntos = "0"
                elem_media = bloque.select_one('.forma.view.puntos.text-right span[data-juego="laliga-fantasy"]')
                if elem_media: media_puntos = elem_media.text.strip()

                pts_ult, pts_ant2, pts_ant3 = "0", "0", "0"
                cajas_racha = bloque.select('div.alineacion-juego-laliga-fantasy span.racha-box')

                if len(cajas_racha) >= 1: pts_ult = "0" if cajas_racha[0].text.strip() == "-" else cajas_racha[0].text.strip()
                if len(cajas_racha) >= 2: pts_ant2 = "0" if cajas_racha[1].text.strip() == "-" else cajas_racha[1].text.strip()
                if len(cajas_racha) >= 3: pts_ant3 = "0" if cajas_racha[2].text.strip() == "-" else cajas_racha[2].text.strip()

                datos_jugadores.append({
                    "ID_Partido": match_id,
                    "Temporada": temporada,
                    "Jornada": jornada,
                    "Equipo": nombre_equipo,
                    "Nombre": nombre,
                    "Posicion": posicion,
                    "Edad": edad,
                    "Nacionalidad": nacionalidad,
                    "Probabilidad_Jugar": probabilidad,
                    "Estado_Medico": estado_medico,
                    "Partidos_Jugados": pj,
                    "Goles": goles,
                    "Asistencias": asist,
                    "Penaltis_Parados": penaltis,
                    "Tarjetas_Amarillas": ta,
                    "Tarjetas_Rojas": tr,
                    "Estado_Forma": forma,
                    "Puntos_Totales": puntos_totales,
                    "Media_Puntos": media_puntos,
                    "Puntos_Ultima_Jornada": pts_ult,
                    "Puntos_Jornada_Ant_2": pts_ant2,
                    "Puntos_Jornada_Ant_3": pts_ant3
                })
                
        return datos_jugadores
    except Exception as e:
        print(f"❌ Error procesando alineaciones en {url}: {e}")
        return []


def scrap_datos_clasificacion():
    url = "https://es.besoccer.com/competicion/clasificacion/primera"
    
    try:
        # 🚨 Usamos el ALIAS 'curl_requests' para no interferir con las otras funciones
        r = curl_requests.get(url, impersonate="chrome120")
        
        if r.status_code != 200:
            print(f"❌ Error al conectar a la clasificación. Estado: {r.status_code}")
            return []

        soup = BeautifulSoup(r.text, 'html.parser')
        
        filas_equipos = soup.find_all('tr', class_=lambda c: c and 'row-body' in c)[:20]
        
        datos_clasificacion = []

        for fila in filas_equipos:
            columnas = fila.find_all('td')
            if len(columnas) < 11: continue
                
            try:
                equipo = fila.find('span', class_='team-name').get_text(strip=True)
                
                racha_contenedor = fila.find('div', class_='match-res')
                racha = "".join([span.get_text(strip=True) for span in racha_contenedor.find_all('span')]) if racha_contenedor else ""
                
                datos_clasificacion.append({
                    "Equipo": equipo,
                    "Racha": racha,
                    "PTS": columnas[3].get_text(strip=True),
                    "PJ": columnas[4].get_text(strip=True),
                    "PG": columnas[5].get_text(strip=True),
                    "PE": columnas[6].get_text(strip=True),
                    "PP": columnas[7].get_text(strip=True),
                    "GF": columnas[8].get_text(strip=True),
                    "GC": columnas[9].get_text(strip=True),
                    "DG": columnas[10].get_text(strip=True)
                })
            except Exception as e:
                pass 
                
        return datos_clasificacion
    except Exception as e:
        print(f"❌ Error procesando clasificación: {e}")
        return []
    

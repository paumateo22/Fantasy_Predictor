import cv2
import easyocr
import os
import re
import difflib
import pandas as pd
import glob

# --- CONFIGURACIÓN DE DICCIONARIOS ---
EQUIPOS_ESTANDAR = [
    "Alavés", "Almería", "Athletic", "Atlético", "Barcelona", "Betis", "Cádiz", 
    "Celta", "Elche", "Espanyol", "Getafe", "Girona", "Granada", "Las Palmas", 
    "Leganés", "Levante", "Mallorca", "Osasuna", "Rayo", "Real Madrid", 
    "Real Oviedo", "Real Sociedad", "Sevilla", "Valencia", "Valladolid", "Villarreal"
]

MAPEO_ALIAS_EQUIPOS = {
    "fc barcelona": "Barcelona", "atlético de madrid": "Atlético", 
    "athletic club": "Athletic", "real betis": "Betis", "rayo vallecano": "Rayo", 
    "celta de vigo": "Celta", "rcd espanyol": "Espanyol", "real valladolid": "Valladolid",
    "deportivo alavés": "Alavés", "ca osasuna": "Osasuna", "rcd mallorca": "Mallorca", 
    "valencia cf": "Valencia", "villarreal cf": "Villarreal", "getafe cf": "Getafe",
    "girona fc": "Girona", "sevilla fc": "Sevilla", "ud las palmas": "Las Palmas", 
    "cd leganés": "Leganés"
}

MAPEO_POSICIONES = {
    'POR': 'Portero', 'DEF': 'Defensa', 'CEN': 'Mediocampista',
    'MED': 'Mediocampista', 'DEL': 'Delantero'
}

def corregir_equipo(texto):
    texto_lower = texto.lower()
    for alias, real in MAPEO_ALIAS_EQUIPOS.items():
        if alias in texto_lower: return real
    coincidencias = difflib.get_close_matches(texto, EQUIPOS_ESTANDAR, n=1, cutoff=0.5)
    return coincidencias[0] if coincidencias else None

def limpiar_precio(texto):
    limpio = texto.replace('.', '').replace('o', '0').replace('O', '0').replace(' ', '').replace(',', '')
    if limpio.isdigit(): return int(limpio)
    return None

def extraer_mercado_jornada(temporada, jornada):
    # Rutas adaptadas a tu estructura mercado/scripts y mercado/fuentes
    directorio_scripts = os.path.dirname(os.path.abspath(__file__))
    carpeta_raiz = os.path.dirname(directorio_scripts)
    carpeta_procesadas = os.path.join(carpeta_raiz, "fuentes", "capturas_pro", temporada, jornada)
    
    if not os.path.exists(carpeta_procesadas):
        print(f"❌ Error: No se encontró la carpeta {carpeta_procesadas}")
        return None

    rutas_imagenes = glob.glob(os.path.join(carpeta_procesadas, "*.[jp][pn]g"))
    if not rutas_imagenes:
        print("❌ No hay imágenes procesadas para leer.")
        return None

    print(f"\n🤖 Iniciando Motor OCR (Temporada: {temporada} | Jornada: {jornada})...")
    lector = easyocr.Reader(['es'], gpu=False) 
    base_datos_mercado = {}
    
    print(f"📸 Procesando {len(rutas_imagenes)} capturas (MÉTODO EXACTO: 7 TIRAS)...\n")
    
    for i, ruta in enumerate(rutas_imagenes, 1):
        nombre_archivo = os.path.basename(ruta)
        frame = cv2.imread(ruta)
        if frame is None: continue
        
        # Matemáticas puras: Dividimos el alto total exactamente entre 7
        alto_tira = frame.shape[0] // 7
        print(f"   -> [{i}/{len(rutas_imagenes)}] {nombre_archivo} | Cortando en 7 tiras...")
        
        nuevos_en_foto = 0
        
        for j in range(7):
            y1 = j * alto_tira
            y2 = (j + 1) * alto_tira
            tira = frame[y1:y2, :]
            
            # Único filtro: Binarización adaptativa (el más letal para texto)
            grises = cv2.cvtColor(tira, cv2.COLOR_BGR2GRAY)
            ampliada = cv2.resize(grises, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            tira_filtrada = cv2.adaptiveThreshold(ampliada, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # Leemos la tira con confianza media-baja (0.25) para atrapar todo
            resultados = lector.readtext(tira_filtrada)
            textos_validos = [t for (_, t, c) in resultados if c > 0.25]
            
            # Lógica de extracción directa
            jugador = {'Nombre': None, 'Precio_Fantastica': None, 'Equipo': 'Desconocido', 'Posicion': 'Desconocido', 'Puntos_PFSY': 0}
            ignorar = ["laliga", "buscar", "favoritos", "equipo", "posición", "nombre", "fantásti", "fantasti"]
            
            for texto in textos_validos:
                texto_low = texto.lower().strip()
                if any(ign in texto_low for ign in ignorar) or len(texto_low) < 2: continue
                
                # Puntos
                match_pfsy = re.search(r'p[ef][s\$]y\s*[-]?\s*(\d+)', texto_low)
                if match_pfsy:
                    jugador['Puntos_PFSY'] = int(match_pfsy.group(1))
                    continue
                
                # Precio
                precio = limpiar_precio(texto)
                if precio is not None and precio >= 100000: 
                    jugador['Precio_Fantastica'] = precio
                    continue
                
                # Posición
                texto_upper = texto_low.upper()
                if texto_upper in MAPEO_POSICIONES:
                    jugador['Posicion'] = MAPEO_POSICIONES[texto_upper]
                    continue
                
                # Equipo
                equipo_corregido = corregir_equipo(texto)
                if equipo_corregido:
                    jugador['Equipo'] = equipo_corregido
                    continue
                
                # Nombre (si no es nada más)
                if not texto.isdigit() and jugador['Nombre'] is None:
                    limpio = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s\.\-]', '', texto).strip()
                    if len(limpio) > 2:
                        jugador['Nombre'] = limpio

            # Lo damos por bueno si al menos pilló el nombre y el precio
            if jugador['Nombre'] and jugador['Precio_Fantastica']:
                if jugador['Nombre'] not in base_datos_mercado:
                    nuevos_en_foto += 1
                base_datos_mercado[jugador['Nombre']] = jugador
                
        print(f"      ✓ {nuevos_en_foto} jugadores guardados.")

    datos_finales = list(base_datos_mercado.values())
    
    if datos_finales:
        df = pd.DataFrame(datos_finales)
        nombre_csv = f"mercado_{temporada.replace('-', '_')}_{jornada}.csv"
        archivo_salida = os.path.join(carpeta_raiz, nombre_csv)
        df.to_csv(archivo_salida, index=False, encoding='utf-8')
        print(f"\n✅ ¡Extracción completada! Dataset guardado en: {archivo_salida}")
    else:
        print("\n⚠️ Finalizado, pero no se extrajo ningún dato válido.")

    return datos_finales

if __name__ == "__main__":
    TEMP = "T25-26" 
    JORN = "J25"
    resultados = extraer_mercado_jornada(TEMP, JORN)
    
    if resultados:
        print(f"\n🏆 Total de jugadores únicos capturados en {JORN}: {len(resultados)}")
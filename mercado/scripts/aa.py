import cv2
import easyocr
import os
import re
import difflib
import pandas as pd
import glob

# --- 1. CONFIGURACIÓN DE DICCIONARIOS ---
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

EQUIPOS_MINUSCULA = [e.lower() for e in EQUIPOS_ESTANDAR]

def corregir_equipo(texto_ocr):
    texto_lower = texto_ocr.lower()
    for alias, nombre_real in MAPEO_ALIAS_EQUIPOS.items():
        if alias in texto_lower: return nombre_real
    coincidencias = difflib.get_close_matches(texto_ocr, EQUIPOS_ESTANDAR, n=1, cutoff=0.5)
    return coincidencias[0] if coincidencias else None

def limpiar_precio(texto):
    limpio = texto.replace('.', '').replace('o', '0').replace('O', '0').replace(' ', '').replace(',', '')
    match = re.search(r'(\d{5,})', limpio)
    if match:
        num = int(match.group(1))
        if num >= 100000:
            return num / 1000000
    return None

def aplicar_filtro_cascada(tira, intento):
    """3 filtros diferentes para asegurar que lee nombres blancos y puntos de colores"""
    grises = cv2.cvtColor(tira, cv2.COLOR_BGR2GRAY)
    ampliada = cv2.resize(grises, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    if intento == 1:
        # Intento 1: Blanco puro (Perfecto para Nombres y Precios)
        _, mascara = cv2.threshold(ampliada, 180, 255, cv2.THRESH_BINARY_INV)
        return mascara
    elif intento == 2:
        # Intento 2: Contraste suave (Rescata colores grises/verdes de los puntos)
        return cv2.convertScaleAbs(ampliada, alpha=1.3, beta=0)
    else:
        # Intento 3: Binarización adaptativa (Por si hay sombras en el fondo)
        return cv2.adaptiveThreshold(ampliada, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

def extraer_datos_jugador(textos_validos):
    jugador = {'Nombre': None, 'Precio_Fantastica': None, 'Equipo': 'Desconocido', 'Posicion': 'Desconocido', 'Puntos_PFSY': None}
    ignorar = ["laliga", "buscar", "favoritos", "equipo", "posición", "nombre", "fantásti", "fantasti", "revolut", "dazn", "viaje"]
    
    posibles_nombres = []

    for texto in textos_validos:
        texto_lower = texto.lower().strip()
        if any(ign in texto_lower for ign in ignorar) or len(texto_lower) < 2: continue
            
        # Puntos (Corregida la regex para aceptar puntos negativos como "-2")
        match_pfsy = re.search(r'p[ef][s\$]y\s*(-?\s*\d+)', texto_lower)
        if match_pfsy:
            # Quitamos espacios por si lee "- 2" y lo convertimos a entero
            jugador['Puntos_PFSY'] = int(match_pfsy.group(1).replace(' ', ''))
            continue
            
        # Precio
        precio = limpiar_precio(texto)
        if precio is not None: 
            jugador['Precio_Fantastica'] = precio
            continue
            
        # Posición
        texto_upper = texto_lower.upper()
        if texto_upper in MAPEO_POSICIONES:
            jugador['Posicion'] = MAPEO_POSICIONES[texto_upper]
            continue
            
        # Equipo
        equipo_corregido = corregir_equipo(texto)
        if equipo_corregido:
            jugador['Equipo'] = equipo_corregido
            continue
            
        # Nombre
        if not texto.isdigit() and "pfsy" not in texto_lower and not any(eq in texto_lower for eq in EQUIPOS_MINUSCULA):
            limpio = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑçÇ\s\.\-]', '', texto).strip()
            if len(limpio) > 2:
                posibles_nombres.append(limpio)

    if posibles_nombres:
        jugador['Nombre'] = max(posibles_nombres, key=len)

    if jugador['Nombre']:
        return jugador
    return None

def extraer_mercado_jornada(temporada, jornada):
    directorio_scripts = os.path.dirname(os.path.abspath(__file__))
    carpeta_raiz = os.path.dirname(directorio_scripts) 
    carpeta_procesadas = os.path.join(carpeta_raiz, "fuentes", "capturas_pro", temporada, jornada)
    
    if not os.path.exists(carpeta_procesadas):
        print(f"❌ Error: No se encontró la carpeta {carpeta_procesadas}")
        return None

    rutas_imagenes = glob.glob(os.path.join(carpeta_procesadas, "*.[jp][pn]g"))
    if not rutas_imagenes:
        print(f"⚠️ La carpeta {carpeta_procesadas} existe pero está vacía.")
        return []

    print(f"\n🤖 Iniciando Motor OCR (T: {temporada} | J: {jornada})...")
    lector = easyocr.Reader(['es'], gpu=True) 
    base_datos_mercado = {}
    
    print(f"📸 Procesando {len(rutas_imagenes)} capturas...\n")
    
    for i, ruta in enumerate(rutas_imagenes, 1):
        nombre_archivo = os.path.basename(ruta)
        frame_original = cv2.imread(ruta)
        if frame_original is None: continue
        
        alto_total = frame_original.shape[0]
        alto_tira = alto_total // 7 
        
        # MARGEN DE SOLAPAMIENTO (25 píxeles) -> Evita que el texto se corte por la mitad
        margen = 25 
        
        print(f"\n--- [{i}/{len(rutas_imagenes)}] Leyendo: {nombre_archivo} ---")
        
        nuevos_en_foto = 0
        
        for j in range(7):
            y1 = max(0, j * alto_tira - margen)
            y2 = min(alto_total, (j + 1) * alto_tira + margen)
            tira = frame_original[y1:y2, :]
            
            jugador_consolidado = None
            
            # MINI-CASCADA para cada tira
            for intento in range(1, 4):
                tira_filtrada = aplicar_filtro_cascada(tira, intento)
                resultados = lector.readtext(tira_filtrada)
                textos_validos = [texto for (_, texto, conf) in resultados if conf > 0.2] 
                
                jugador_intento = extraer_datos_jugador(textos_validos)
                
                if jugador_intento:
                    if jugador_consolidado is None:
                        jugador_consolidado = jugador_intento
                    else:
                        # Rellenamos los datos que faltasen con lo nuevo que haya encontrado este filtro
                        if not jugador_consolidado['Precio_Fantastica'] and jugador_intento['Precio_Fantastica']:
                            jugador_consolidado['Precio_Fantastica'] = jugador_intento['Precio_Fantastica']
                        if jugador_consolidado['Puntos_PFSY'] is None and jugador_intento['Puntos_PFSY'] is not None:
                            jugador_consolidado['Puntos_PFSY'] = jugador_intento['Puntos_PFSY']
                    
                    # Si ya tenemos lo importante (Nombre, Precio y Puntos), paramos la cascada
                    if jugador_consolidado['Precio_Fantastica'] and jugador_consolidado['Puntos_PFSY'] is not None:
                        break 
                    
            if jugador_consolidado:
                nombre = jugador_consolidado['Nombre']
                pts = jugador_consolidado['Puntos_PFSY'] if jugador_consolidado['Puntos_PFSY'] is not None else 0
                
                clave_unica = f"{nombre}_{jugador_consolidado['Equipo']}_{jugador_consolidado['Posicion']}_{pts}"
                
                precio_str = f"{jugador_consolidado['Precio_Fantastica']}M" if jugador_consolidado['Precio_Fantastica'] else "N/A"
                print(f"  🔍 {nombre:<15} | {jugador_consolidado['Equipo']:<12} | {jugador_consolidado['Posicion']:<13} | {precio_str:<6} | {pts} pts")
                
                # Para el CSV final, si no leyó puntos, le ponemos un 0
                jugador_consolidado['Puntos_PFSY'] = pts
                
                if clave_unica not in base_datos_mercado:
                    nuevos_en_foto += 1
                base_datos_mercado[clave_unica] = jugador_consolidado
                
        print(f"  => Resumen: {nuevos_en_foto} jugadores nuevos guardados.")

    print("\n✅ Procesamiento de lote finalizado.")
    
    datos_finales = list(base_datos_mercado.values())
    
    if datos_finales:
        df = pd.DataFrame(datos_finales)
        df = df.sort_values(by='Nombre', ascending=True)
        nombre_csv = f"mercado_{temporada.replace('-', '_')}_{jornada}.csv"
        archivo_salida = os.path.join(carpeta_raiz, nombre_csv)
        df.to_csv(archivo_salida, index=False, encoding='utf-8')
        
        print(f"\n🏆 --- DATASET FINAL: {len(datos_finales)} JUGADORES --- 🏆")
        print(f"💾 Guardado en orden alfabético en: {archivo_salida}")
    else:
        print("\n⚠️ Finalizado, pero no se extrajo ningún dato válido.")

    return datos_finales

if __name__ == "__main__":
    TEMP = "T25-26" 
    JORN = "J25"
    extraer_mercado_jornada(TEMP, JORN)
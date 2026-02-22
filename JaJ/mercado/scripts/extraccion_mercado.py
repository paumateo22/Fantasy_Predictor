import cv2
import numpy as np
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
    'POR': 'Portero', 'P0R': 'Portero', 'PQR': 'Portero',
    'DEF': 'Defensa', '0EF': 'Defensa', 'OEF': 'Defensa',
    'CEN': 'Mediocampista', 'MED': 'Mediocampista', 'MEO': 'Mediocampista',
    'DEL': 'Delantero', '0EL': 'Delantero', 'OEL': 'Delantero'
}

EQUIPOS_MINUSCULA = [e.lower() for e in EQUIPOS_ESTANDAR]

# --- 2. FUNCIONES AUXILIARES ---

def obtener_posicion_por_color(tira_bgr):
    """
    Detecta la posición usando rangos ultra-específicos para evitar la zona de degradado
    entre portero y delantero.
    """
    # 🛡️ FILTRO ANTI-ESCUDOS: Ignoramos los primeros 150px
    zona_limpia = tira_bgr[:, 150:]
    hsv = cv2.cvtColor(zona_limpia, cv2.COLOR_BGR2HSV)

    # --- RANGOS AJUSTADOS (Corazón del color) ---
    
    # Portero (Naranja intenso): Estrechamos para no tocar el amarillo
    lower_por = np.array([5, 150, 150]);  upper_por = np.array([15, 255, 255])
    
    # Delantero (Amarillo/Dorado): Subimos el inicio del tono para alejarnos del naranja
    lower_del = np.array([22, 130, 130]); upper_del = np.array([35, 255, 255])
    
    # Mediocampista (Azul): Se mantiene igual por ser muy distinto
    lower_med = np.array([90, 100, 100]); upper_med = np.array([125, 255, 255])
    
    # Defensa (Morado/Rosa): Se mantiene igual
    lower_def = np.array([135, 80, 80]);  upper_def = np.array([165, 255, 255])

    # Conteo de píxeles
    pix_por = cv2.countNonZero(cv2.inRange(hsv, lower_por, upper_por))
    pix_del = cv2.countNonZero(cv2.inRange(hsv, lower_del, upper_del))
    pix_med = cv2.countNonZero(cv2.inRange(hsv, lower_med, upper_med))
    pix_def = cv2.countNonZero(cv2.inRange(hsv, lower_def, upper_def))

    resultados = {
        'Portero': pix_por,
        'Delantero': pix_del,
        'Mediocampista': pix_med,
        'Defensa': pix_def
    }

    ganador = max(resultados, key=resultados.get)
    
    # 🚨 UMBRAL DE SEGURIDAD: 
    # Si el ganador tiene muy pocos píxeles, es que estamos en el degradado
    # o es un escudo. Devolvemos Desconocido para que mande el OCR (DEL, POR, etc.)
    if resultados[ganador] < 40:
        return 'Desconocido'
        
    return ganador

def corregir_equipo(texto_ocr):
    texto_lower = texto_ocr.lower()
    for alias, nombre_real in MAPEO_ALIAS_EQUIPOS.items():
        if alias in texto_lower: return nombre_real
    coincidencias = difflib.get_close_matches(texto_ocr, EQUIPOS_ESTANDAR, n=1, cutoff=0.75)
    return coincidencias[0] if coincidencias else None

def limpiar_precio(texto):
    limpio = texto.replace('.', '').replace('o', '0').replace('O', '0').replace(' ', '').replace(',', '')
    match = re.search(r'(\d{5,})', limpio)
    if match:
        num = int(match.group(1))
        if num >= 100000: return num / 1000000
    return None

def aplicar_filtro_cascada(tira, intento):
    grises = cv2.cvtColor(tira, cv2.COLOR_BGR2GRAY)
    ampliada = cv2.resize(grises, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    if intento == 1:
        _, m = cv2.threshold(ampliada, 180, 255, cv2.THRESH_BINARY_INV)
        return m
    elif intento == 2:
        _, m = cv2.threshold(ampliada, 240, 255, cv2.THRESH_BINARY_INV)
        return m
    return cv2.convertScaleAbs(ampliada, alpha=1.3, beta=0)

def extraer_datos_divididos(textos_izq, textos_der):
    # Inicializamos con None para la consolidación inteligente
    jugador = {'Nombre': None, 'Precio_Fantastica': None, 'Equipo': 'Desconocido', 'Posicion': 'Delantero', 'Puntos_PFSY': None}
    ignorar = ["laliga", "buscar", "favoritos", "equipo", "posición", "nombre", "fantásti", "fantasti", "revolut", "dazn", "viaje", "prsy", "ptsy", "pts", "pfsy"]
    
    # --- DERECHA (Puntos y Precio) ---
    for texto in textos_der:
        texto_low = texto.lower().strip()
        if any(ign == texto_low for ign in ignorar) or len(texto_low) < 1: continue
        
        match_pfsy = re.search(r'[pef][fs\$]y\s*(-?\d+)', texto_low)
        if match_pfsy:
            jugador['Puntos_PFSY'] = int(match_pfsy.group(1))
            continue
            
        precio = limpiar_precio(texto)
        if precio is not None:
            jugador['Precio_Fantastica'] = precio
            continue

        solo_num = texto_low.replace('.', '').replace(',', '').replace(' ', '')
        if solo_num.lstrip('-').isdigit():
            val = int(solo_num)
            if -20 < val < 300: jugador['Puntos_PFSY'] = val

    # --- IZQUIERDA (Nombre, Equipo, Posición) ---
    posibles_nombres = []
    for texto in textos_izq:
        texto_low = texto.lower().strip()
        if any(ign == texto_low for ign in ignorar) or len(texto_low) < 1: continue
        
        if texto_low.upper() in MAPEO_POSICIONES:
            jugador['Posicion'] = MAPEO_POSICIONES[texto_low.upper()]
            continue
            
        equipo = corregir_equipo(texto)
        if equipo and jugador['Equipo'] == 'Desconocido':
            jugador['Equipo'] = equipo
            continue
            
        if not texto.isdigit() and not any(eq in texto_low for eq in EQUIPOS_MINUSCULA):
            limpio = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑçÇ\s\.\-]', '', texto).strip()
            if len(limpio) >= 1: posibles_nombres.append(limpio)

    if posibles_nombres:
        nombres_unicos = []
        for n in posibles_nombres:
            if n not in nombres_unicos: nombres_unicos.append(n)
        jugador['Nombre'] = " ".join(nombres_unicos)

    if jugador['Nombre'] and len(jugador['Nombre']) < 3 and "." not in jugador['Nombre']:
        jugador['Nombre'] = None

    return jugador if jugador['Nombre'] else None

# --- 3. FUNCIÓN PRINCIPAL ---
def extraer_mercado_jornada(temporada, jornada):
    directorio_scripts = os.path.dirname(os.path.abspath(__file__))
    carpeta_raiz = os.path.dirname(directorio_scripts) 
    carpeta_pro = os.path.join(carpeta_raiz, "fuentes", "capturas_pro", temporada, jornada)
    
    if not os.path.exists(carpeta_pro): return None
    rutas = glob.glob(os.path.join(carpeta_pro, "*.[jp][pn]g"))
    
    lector = easyocr.Reader(['es'], gpu=True) 
    base_datos_mercado = {}
    
    for i, ruta in enumerate(rutas, 1):
        nombre_archivo = os.path.basename(ruta)
        frame = cv2.imread(ruta)
        if frame is None: continue
        
        alto, ancho = frame.shape[:2]
        corte_x = int(ancho * 0.66)
        
        mask = cv2.inRange(frame, np.array([20, 8, 8]), np.array([39, 27, 27]))
        filas = np.where(np.sum(mask == 255, axis=1) > ancho * 0.60)[0]
        
        cortes_y = [0]
        if len(filas) > 0:
            curr = filas[0]
            for y in filas[1:]:
                if y - curr > 30: cortes_y.append(curr)
                curr = y
            cortes_y.append(curr)
        cortes_y.append(alto)

        usar_lineas = len(cortes_y) == 8
        print(f"\n--- [{i}/{len(rutas)}] {nombre_archivo} ---")
        
        for j in range(7):
            y1 = max(0, cortes_y[j] - 5) if usar_lineas else max(0, j*(alto//7)-25)
            y2 = min(alto, cortes_y[j+1] + 2) if usar_lineas else min(alto, (j+1)*(alto//7)+25)
            
            tira = frame[y1:y2, :]
            t_izq, t_der = tira[:, :corte_x], tira[:, corte_x:]
            pos_color = obtener_posicion_por_color(t_izq)
            
            jugador_cons = None
            for intento in range(1, 4):
                res_izq = lector.readtext(aplicar_filtro_cascada(t_izq, intento))
                res_der = lector.readtext(aplicar_filtro_cascada(t_der, intento))
                txt_izq = [t for (_, t, c) in res_izq if c > 0.2] 
                txt_der = [t for (_, t, c) in res_der if c > 0.2] 
                
                print(f"      [RAYOS X - F{j+1} Int{intento}] IZQ: {txt_izq} | DER: {txt_der}")
                
                intent = extraer_datos_divididos(txt_izq, txt_der)
                if intent:
                    if pos_color != 'Desconocido': intent['Posicion'] = pos_color
                    
                    if jugador_cons is None:
                        jugador_cons = intent
                    else:
                        # Consolidación por None (respeta el 0)
                        if jugador_cons['Precio_Fantastica'] is None: 
                            jugador_cons['Precio_Fantastica'] = intent['Precio_Fantastica']
                        if jugador_cons['Puntos_PFSY'] is None: 
                            jugador_cons['Puntos_PFSY'] = intent['Puntos_PFSY']
                        if jugador_cons['Posicion'] == 'Delantero' and intent['Posicion'] != 'Delantero':
                            jugador_cons['Posicion'] = intent['Posicion']

                    if jugador_cons['Precio_Fantastica'] is not None and jugador_cons['Puntos_PFSY'] is not None: 
                        break

            if jugador_cons:
                clave = f"{jugador_cons['Nombre']}_{jugador_cons['Equipo']}_{jugador_cons['Posicion']}_{jugador_cons['Puntos_PFSY']}"
                if clave not in base_datos_mercado:
                    base_datos_mercado[clave] = jugador_cons
                print(f"  🔍 {jugador_cons['Nombre']:<15} | {jugador_cons['Equipo']:<12} | {jugador_cons['Posicion']:<13} | {jugador_cons['Precio_Fantastica']}M | {jugador_cons['Puntos_PFSY']} pts")

    df = pd.DataFrame(list(base_datos_mercado.values()))
    df.sort_values(by='Nombre').to_csv(os.path.join("datasets/JaJ/{temporada}/jornada", f"mercado.csv"), index=False)
    print(f"\n✅ Finalizado. Dataset: {len(df)} jugadores.")

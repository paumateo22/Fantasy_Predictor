import cv2
import numpy as np
import easyocr
import os
import re
import difflib
import unicodedata
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
    "fc barcelona": "Barcelona", "barca": "Barcelona",
    "atletico de madrid": "Atlético", "atletico": "Atlético", "atleti": "Atlético", "at madrid": "Atlético",
    "athletic club": "Athletic", "athletic": "Athletic",
    "real betis": "Betis", "betis": "Betis",
    "rayo vallecano": "Rayo", "rayo": "Rayo",
    "celta de vigo": "Celta", "celta": "Celta",
    "rcd espanyol": "Espanyol", "espanyol": "Espanyol",
    "real valladolid": "Valladolid", "valladolid": "Valladolid",
    "deportivo alaves": "Alavés", "alaves": "Alavés",
    "ca osasuna": "Osasuna", "osasuna": "Osasuna",
    "rcd mallorca": "Mallorca", "mallorca": "Mallorca",
    "valencia cf": "Valencia", "valencia": "Valencia",
    "villarreal cf": "Villarreal", "villarreal": "Villarreal",
    "getafe cf": "Getafe", "getafe": "Getafe",
    "girona fc": "Girona", "girona": "Girona",
    "sevilla fc": "Sevilla", "sevilla": "Sevilla",
    "ud las palmas": "Las Palmas", "las palmas": "Las Palmas",
    "cd leganes": "Leganés", "leganes": "Leganés",
    "levante ud": "Levante", "levante": "Levante",
    "real oviedo": "Real Oviedo", "oviedo": "Real Oviedo",
    "espanyol de b": "Espanyol", "espanyol": "Espanyol",
    "atletico de madrid": "Atlético", "atletico": "Atlético",
    "villarreal cf": "Villarreal", "villarreal": "Villarreal"
}

MAPEO_POSICIONES = {
    'POR': 'Portero', 'P0R': 'Portero', 'PQR': 'Portero',
    'DEF': 'Defensa', '0EF': 'Defensa', 'OEF': 'Defensa',
    'CEN': 'Mediocampista', 'MED': 'Mediocampista', 'MEO': 'Mediocampista',
    'DEL': 'Delantero', '0EL': 'Delantero', 'OEL': 'Delantero'
}

BASURA_NOMBRES = ["club", "clup", "real", "deportivo", "sociedad", "unión", "deportiva", "cf", "ud", "rcd", "sd", "hcd", "espanyor", "ae", "puk"]

EQUIPOS_MINUSCULA = [e.lower() for e in EQUIPOS_ESTANDAR]

# --- 2. FUNCIONES AUXILIARES ---

def obtener_posicion_por_color(tira_bgr):
    """
    Detecta la posición con ventaja para delanteros y penalización para porteros
    para evitar errores por saturación de color.
    """
    zona_limpia = tira_bgr[:, 150:]
    hsv = cv2.cvtColor(zona_limpia, cv2.COLOR_BGR2HSV)

    # 1. Rangos ultra-ajustados
    lower_por = np.array([5, 160, 160]);  upper_por = np.array([14, 255, 255])
    lower_del = np.array([21, 130, 130]); upper_del = np.array([39, 255, 255])
    lower_med = np.array([95, 100, 100]); upper_med = np.array([125, 255, 255])
    lower_def = np.array([135, 80, 80]);  upper_def = np.array([165, 255, 255])

    # 2. Conteo de píxeles
    pix_por = cv2.countNonZero(cv2.inRange(hsv, lower_por, upper_por))
    pix_del = cv2.countNonZero(cv2.inRange(hsv, lower_del, upper_del))
    pix_med = cv2.countNonZero(cv2.inRange(hsv, lower_med, upper_med))
    pix_def = cv2.countNonZero(cv2.inRange(hsv, lower_def, upper_def))

    # 3. APLICAR VENTAJAS (BIAS)
    # Le damos un 50% de valor extra a los píxeles amarillos
    pix_del_ponderado = pix_del * 1.5
    
    res = {
        'Portero': pix_por,
        'Delantero': pix_del_ponderado,
        'Mediocampista': pix_med,
        'Defensa': pix_def
    }

    ganador = max(res, key=res.get)
    
    # 4. REGLAS DE DESEMPATE INTELIGENTES
    # Regla A: Si el ganador es Portero pero el Delantero tiene una cantidad similar de píxeles,
    # elegimos Delantero por probabilidad estadística.
    if ganador == 'Portero':
        # Solo aceptamos Portero si tiene el doble de píxeles que el Delantero
        if pix_por < (pix_del * 2):
            ganador = 'Delantero'
            
    # Regla B: Umbral mínimo de confianza
    if res[ganador] < 50: 
        return 'Desconocido'
        
    return ganador

def eliminar_tildes(texto):
    """Limpia tildes y caracteres especiales para comparaciones seguras."""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) 
                   if unicodedata.category(c) != 'Mn')

def corregir_equipo_con_puntuacion(texto_ocr):
    """
    Devuelve el nombre del equipo y su puntuación de similitud (0 a 1).
    """
    texto_raw = texto_ocr.strip()
    texto_ocr_limpio = eliminar_tildes(texto_raw.lower().replace('.', ''))
    
    # 1. Prioridad: Diccionario de Alias (Puntuación máxima 1.0)
    for alias, nombre_real in MAPEO_ALIAS_EQUIPOS.items():
        alias_limpio = eliminar_tildes(alias.lower().replace('.', ''))
        if alias_limpio == texto_ocr_limpio: # Coincidencia exacta
            return nombre_real, 1.0
        if alias_limpio in texto_ocr_limpio: # Contenido
            return nombre_real, 0.95

    # 2. Protección de iniciales: Si parece nombre de jugador, bajamos su puntuación drásticamente
    if re.search(r'^[A-Z]\.\s', texto_raw):
        return None, 0.0
            
    # 3. Fuzzy Match contra lista ESTÁNDAR
    equipos_low = [eliminar_tildes(e.lower()) for e in EQUIPOS_ESTANDAR]
    coincidencias = difflib.get_close_matches(texto_ocr_limpio, equipos_low, n=1, cutoff=0.5)
    
    if coincidencias:
        # Calculamos el ratio real de similitud
        score = difflib.SequenceMatcher(None, texto_ocr_limpio, coincidencias[0]).ratio()
        idx = equipos_low.index(coincidencias[0])
        return EQUIPOS_ESTANDAR[idx], score
        
    return None, 0.0

def extraer_datos_divididos(textos_izq, textos_der):
    jugador = {'Nombre': None, 'Precio_Fantastica': None, 'Equipo': 'Desconocido', 'Posicion': 'Delantero', 'Puntos_PFSY': None}
    ignorar = ["laliga", "buscar", "favoritos", "equipo", "posición", "nombre", "fantásti", "fantasti", "revolut", "dazn", "viaje", "prsy", "ptsy", "pts", "pfsy"]
    fragmentos_posicion = ["D", "DE", "DF", "C", "CE", "CN", "M", "ME", "P", "PO", "PR", "L", "POR", "DEF", "CEN", "DEL"]

    # --- 1. PROCESAR DERECHA (Puntos y Precio) ---
    puntos_confirmados = False
    for texto in textos_der:
        texto_low = texto.lower().strip()
        if any(ign == texto_low for ign in ignorar) or len(texto_low) < 1: continue
        match_pfsy = re.search(r'[pef][fs\$]y\s*(-?\d+)', texto_low)
        if match_pfsy:
            jugador['Puntos_PFSY'] = int(match_pfsy.group(1)); puntos_confirmados = True; continue
        precio = limpiar_precio(texto)
        if precio is not None: jugador['Precio_Fantastica'] = precio; continue
        solo_num = texto_low.replace('.', '').replace(',', '').replace(' ', '')
        if solo_num.lstrip('-').isdigit() and not puntos_confirmados:
            val = int(solo_num)
            if -20 < val < 300: jugador['Puntos_PFSY'] = val

    # --- 2. TORNEO EQUIPOS ---
    mejor_s = 0.0
    ganador_e, idx_e = "Desconocido", -1
    for i, t in enumerate(textos_izq):
        eq, s = corregir_equipo_con_puntuacion(t)
        if s > mejor_s and s > 0.65: mejor_s = s; ganador_e = eq; idx_e = i
    jugador['Equipo'] = ganador_e

    # --- 3. NOMBRE ---
    nombres_finales = []
    for i, t in enumerate(textos_izq):
        if i == idx_e: continue
        t_up, t_low = t.upper().strip(), t.lower().strip()
        
        # Filtros previos
        if any(ign in t_low for ign in ignorar) or len(t_low) < 1: continue
        if t_up in MAPEO_POSICIONES: jugador['Posicion'] = MAPEO_POSICIONES[t_up]; continue
        if any(basura in t_low for basura in BASURA_NOMBRES): continue

        # 🚨 REGLA DE LAS INICIALES (I. y O.)
        # Solo transformamos si encontramos "1." o "0." (el punto es obligatorio)
        # Esto permite casos como "I. Benito" o "Pathe I. Ciss" y evita "1" aleatorios.
        t_fix = re.sub(r'\b1\.', 'I.', t)
        t_fix = re.sub(r'\b0\.', 'O.', t_fix)
        
        # Limpieza: Eliminamos cualquier número que haya quedado suelto (como dorsales)
        # y mantenemos solo letras, espacios, puntos y guiones.
        limpio = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑçÇ\s\.\-]', '', t_fix).strip()
        
        if len(limpio) >= 1: 
            nombres_finales.append(limpio)

    if nombres_finales:
        nombre_str = " ".join(nombres_finales).strip()
        # Limpiamos posibles puntos huérfanos al principio por errores de lectura
        jugador['Nombre'] = re.sub(r'^\. ', '', nombre_str).strip()

    return jugador if jugador['Nombre'] else None

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
        _, m = cv2.threshold(ampliada, 180, 255, cv2.THRESH_BINARY_INV); return m
    elif intento == 2:
        _, m = cv2.threshold(ampliada, 240, 255, cv2.THRESH_BINARY_INV); return m
    return cv2.convertScaleAbs(ampliada, alpha=1.3, beta=0)

# --- 3. FUNCIÓN PRINCIPAL ---
def extraer_mercado_jornada(temporada, jornada):
    directorio_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    carpeta_pro = os.path.join(directorio_raiz, "fuentes", "capturas_pro", temporada, jornada)

    if not os.path.exists(carpeta_pro):
        print(f"❌ Carpeta no encontrada: {carpeta_pro}")
        return
        
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
                if y - curr > 30: cortes_y.append(curr); curr = y
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
                
                # 🚀 AQUÍ TIENES TUS RAYOS X VOLVIENDO A LA VIDA
                print(f"      [RAYOS X - F{j+1} Int{intento}] IZQ: {txt_izq} | DER: {txt_der}")
                
                intent = extraer_datos_divididos(txt_izq, txt_der)
                if intent:
                    if pos_color != 'Desconocido': intent['Posicion'] = pos_color
                    if jugador_cons is None: jugador_cons = intent
                    else:
                        if jugador_cons['Precio_Fantastica'] is None: jugador_cons['Precio_Fantastica'] = intent['Precio_Fantastica']
                        if jugador_cons['Puntos_PFSY'] is None: jugador_cons['Puntos_PFSY'] = intent['Puntos_PFSY']
                        if jugador_cons['Posicion'] == 'Delantero' and intent['Posicion'] != 'Delantero': jugador_cons['Posicion'] = intent['Posicion']
                        if jugador_cons['Equipo'] == 'Desconocido': jugador_cons['Equipo'] = intent['Equipo']
                    
                    if jugador_cons['Precio_Fantastica'] and jugador_cons['Puntos_PFSY'] is not None and jugador_cons['Equipo'] != 'Desconocido':
                        break

            if jugador_cons:
                clave = f"{jugador_cons['Nombre']}_{jugador_cons['Equipo']}"
                if clave not in base_datos_mercado:
                    base_datos_mercado[clave] = jugador_cons
                    print(f"  🔍 {jugador_cons['Nombre']:<15} | {jugador_cons['Equipo']:<12} | {jugador_cons['Posicion']:<13} | {jugador_cons['Precio_Fantastica']}M | {jugador_cons['Puntos_PFSY']} Puntos")

    df = pd.DataFrame(list(base_datos_mercado.values()))
    ruta_csv = os.path.join(directorio_raiz, "datasets", "JaJ", temporada, jornada, "mercado.csv")
    os.makedirs(os.path.dirname(ruta_csv), exist_ok=True)
    df.sort_values(by='Nombre').to_csv(ruta_csv, index=False)
    print(f"\n✅ Archivo guardado en: {ruta_csv}")


import re
import difflib
import unicodedata
import cv2
import numpy as np
import sys
import os

directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_raiz = os.path.dirname(os.path.dirname(directorio_actual))
if directorio_raiz not in sys.path:
    sys.path.append(directorio_raiz)

from auxiliar.constantes_mercado import MAPEO_ALIAS_EQUIPOS, EQUIPOS_ESTANDAR, MAPEO_POSICIONES, BASURA_NOMBRES

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

        # 🚨 REGLA MEJORADA DE LAS INICIALES (I. y O.)
        # Convierte "1Lekue", "1.Lekue", "1 Lekue" o "1. Benito" a "I. Lekue" / "I. Benito"
        # Funciona buscando un 1 o un 0 seguido (opcionalmente) por un punto o un espacio, y luego una letra.
        t_fix = re.sub(r'\b1\.?\s*(?=[a-zA-ZáéíóúÁÉÍÓÚñÑçÇ])', 'I. ', t)
        t_fix = re.sub(r'\b0\.?\s*(?=[a-zA-ZáéíóúÁÉÍÓÚñÑçÇ])', 'O. ', t_fix)
        
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

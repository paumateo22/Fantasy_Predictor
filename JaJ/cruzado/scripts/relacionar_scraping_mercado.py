import pandas as pd
import difflib
import os
import sys

# --- BRÚJULA DE RUTAS ---
directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_raiz = os.path.dirname(os.path.dirname(os.path.dirname(directorio_actual)))

def obtener_rutas_cruce(temporada, jornada):
    dir_mercado = os.path.join(directorio_raiz, "JaJ", "mercado", "datasets", temporada, jornada)
    dir_scraping = os.path.join(directorio_raiz, "JaJ", "scraping", "datasets", temporada, jornada)
    dir_cruzado = os.path.join(directorio_raiz, "JaJ", "cruzado", "datasets", temporada, jornada)
    
    rutas = {
        'mercado': os.path.join(dir_mercado, "mercado_limpio.csv"),
        'scraping': os.path.join(dir_scraping, "jugadores.csv"),
        'diccionario_cruce': os.path.join(dir_cruzado, "relaciones_scraping_mercado.csv")
    }
    return rutas

def cargar_diccionario_cruce(ruta_csv):
    diccionario = {}
    if os.path.exists(ruta_csv):
        try:
            df = pd.read_csv(ruta_csv, dtype=str).dropna()
            for _, fila in df.iterrows():
                diccionario[fila['Clave_Scraping']] = fila['Clave_Mercado']
        except Exception as e:
            print(f"⚠️ Error leyendo el diccionario de cruce: {e}")
    return diccionario

def guardar_diccionario_cruce(diccionario, ruta_csv):
    filas = [{'Clave_Scraping': k, 'Clave_Mercado': v} for k, v in diccionario.items() if v != "IGNORAR"]
    df = pd.DataFrame(filas)
    
    if not df.empty:
        df = df.sort_values(by=['Clave_Scraping'], ascending=[True])
        os.makedirs(os.path.dirname(ruta_csv), exist_ok=True)
        df.to_csv(ruta_csv, index=False, encoding='utf-8-sig')

def parsear_puntos(valor):
    """Convierte los puntos a número entero de forma segura. Retorna None si falla."""
    try:
        if pd.isna(valor) or valor == "N/A":
            return None
        return int(float(valor))
    except (ValueError, TypeError):
        return None

def relacionar_bases_datos(temporada, jornada):
    rutas = obtener_rutas_cruce(temporada, jornada)
    
    # 1. Validar archivos
    if not os.path.exists(rutas['mercado']):
        print(f"❌ Falta el mercado limpio: {rutas['mercado']}")
        return
    if not os.path.exists(rutas['scraping']):
        print(f"❌ Faltan los datos del scraping: {rutas['scraping']}")
        return

    # 2. Cargar datos
    df_mercado = pd.read_csv(rutas['mercado'], dtype=str).fillna("N/A")
    df_scraping = pd.read_csv(rutas['scraping'], dtype=str).fillna("N/A")
    
    # 3. Preparar la información del Mercado (con valores numéricos guardados)
    info_mercado = {}
    puntos_mercado_num = {}
    claves_mercado = []
    
    for _, fila in df_mercado.iterrows():
        clave_m = f"{fila['Nombre']}_{fila['Equipo']}"
        display_m = f"{fila['Nombre']} | {fila['Equipo']} | {fila['Posicion']} | {fila.get('Puntos_PFSY', '0')}pts | {fila.get('Precio_Fantastica', '0')}M"
        info_mercado[clave_m] = display_m
        puntos_mercado_num[clave_m] = parsear_puntos(fila.get('Puntos_PFSY'))
        claves_mercado.append(clave_m)
        
    # 4. Preparar las claves del Scraping y extraer sus puntos
    info_scraping_puntos_str = {}
    puntos_scraping_num = {}
    claves_scraping = []
    
    for _, fila in df_scraping.iterrows():
        clave_s = f"{fila['Nombre']}_{fila['Equipo']}"
        if clave_s not in claves_scraping:
            claves_scraping.append(clave_s)
            
        pts_str = fila.get('Puntos_Totales', 'N/A')
        info_scraping_puntos_str[clave_s] = pts_str
        puntos_scraping_num[clave_s] = parsear_puntos(pts_str)
    
    # 5. Cargar diccionario y filtrar pendientes
    diccionario_cruce = cargar_diccionario_cruce(rutas['diccionario_cruce'])
    pendientes = [c for c in claves_scraping if c not in diccionario_cruce]
    
    # --- FASE 1: Emparejamiento Automático Mejorado ---
    automaticos = 0
    for clave_s in list(pendientes):
        # Condición A: Coincidencia exacta de texto
        if clave_s in claves_mercado:
            diccionario_cruce[clave_s] = clave_s
            pendientes.remove(clave_s)
            automaticos += 1
            continue
            
        # Condición B: Los puntos son idénticos y el texto se parece al menos un 70%
        pts_s_val = puntos_scraping_num.get(clave_s)
        if pts_s_val is not None:
            # Buscamos quién en el mercado tiene esos mismos puntos exactos
            candidatos_mismos_puntos = [c_m for c_m in claves_mercado if puntos_mercado_num.get(c_m) == pts_s_val]
            
            if candidatos_mismos_puntos:
                # Si alguien tiene esos puntos, vemos si el nombre encaja (cutoff=0.7)
                match_puntos_texto = difflib.get_close_matches(clave_s, candidatos_mismos_puntos, n=1, cutoff=0.7)
                if match_puntos_texto:
                    diccionario_cruce[clave_s] = match_puntos_texto[0]
                    pendientes.remove(clave_s)
                    automaticos += 1
            
    guardar_diccionario_cruce(diccionario_cruce, rutas['diccionario_cruce'])

    print("\n" + "="*50)
    print(f" 🔗 MATCHMAKER: SCRAPING vs MERCADO ({jornada})")
    print("="*50)
    print(f"📊 Jugadores base (Scraping): {len(claves_scraping)}")
    print(f"🛒 Jugadores disponibles (Mercado): {len(claves_mercado)}")
    print(f"⚡ Emparejados automáticamente: {automaticos}")
    print(f"🤔 Pendientes de revisión: {len(pendientes)}")
    
    if not pendientes:
        print("\n✅ ¡Todos los jugadores del scraping están enlazados con el mercado!")
        return

    # --- FASE 2: Interactivo con Filtro de Puntos ---
    for clave_s in pendientes:
        nombre_s, equipo_s = clave_s.split("_", 1)
        pts_s_str = info_scraping_puntos_str.get(clave_s, 'N/A')
        pts_s_val = puntos_scraping_num.get(clave_s)
        
        print(f"\n" + "="*50)
        print(f"❓ SCRAPING HA REGISTRADO A: {nombre_s} ({equipo_s}) | {pts_s_str} pts")
        print("="*50)
        
        # 🚨 FILTRO INTELIGENTE: Descartamos los que difieran en más de 10 puntos
        candidatos_filtrados = []
        for c_m in claves_mercado:
            pts_m_val = puntos_mercado_num.get(c_m)
            # Si alguno no tiene puntos legibles, lo mantenemos por precaución para no perderlo
            if pts_s_val is None or pts_m_val is None:
                candidatos_filtrados.append(c_m)
            elif abs(pts_s_val - pts_m_val) <= 10:
                candidatos_filtrados.append(c_m)
        
        # Ahora buscamos los más parecidos SOLO dentro de los filtrados
        parecidos = difflib.get_close_matches(clave_s, candidatos_filtrados, n=10, cutoff=0.1)
        
        print("0. ✍️  Escribir nombre manualmente o descartar jugador")
        for i, clave_candidato in enumerate(parecidos, 1):
            print(f"{i}. {info_mercado[clave_candidato]}")
            
        while True:
            opcion = input(f"\nElige una opción (0-{len(parecidos)}): ").strip()
            if opcion.isdigit() and 0 <= int(opcion) <= len(parecidos):
                opcion = int(opcion)
                break
            print("❌ Opción no válida.")
            
        if opcion == 0:
            while True:
                print("\n👉 Introduce SOLO el nombre del jugador en el mercado (Ej: Alvaro Garcia)")
                manual = input("👉 O pulsa '0' de nuevo si este jugador NO está en el mercado: ").strip()
                
                if manual == '0':
                    diccionario_cruce[clave_s] = "IGNORAR"
                    print("🚫 Jugador ignorado (no se guardará relación).")
                    break
                elif manual:
                    matches = [k for k in claves_mercado if k.split("_", 1)[0].lower() == manual.lower()]
                    
                    if len(matches) == 0:
                        print("❌ No se ha encontrado a ningún jugador con ese nombre en el mercado. Revisa si hay tildes o abreviaturas.")
                    elif len(matches) == 1:
                        elegido = matches[0]
                        diccionario_cruce[clave_s] = elegido
                        nom_e, eq_e = elegido.split("_", 1)
                        print(f"✅ Relación hecha automáticamente: {nom_e} - {eq_e}")
                        break
                    else:
                        print(f"\n🤔 Se han encontrado varios '{manual}'. Elige el correcto:")
                        for idx, match_key in enumerate(matches, 1):
                            print(f"{idx}. {info_mercado[match_key]}")
                        
                        while True:
                            sub_opcion = input(f"\nElige una opción (1-{len(matches)}): ").strip()
                            if sub_opcion.isdigit() and 1 <= int(sub_opcion) <= len(matches):
                                sub_opcion = int(sub_opcion)
                                break
                            print("❌ Opción no válida.")
                        
                        elegido = matches[sub_opcion - 1]
                        diccionario_cruce[clave_s] = elegido
                        nom_e, eq_e = elegido.split("_", 1)
                        print(f"✅ Relación hecha: {nom_e} - {eq_e}")
                        break
        else:
            elegido = parecidos[opcion - 1]
            diccionario_cruce[clave_s] = elegido
            
        guardar_diccionario_cruce(diccionario_cruce, rutas['diccionario_cruce'])

    print("\n✅ ¡Emparejamiento finalizado! Diccionario de cruce de la jornada actualizado.")

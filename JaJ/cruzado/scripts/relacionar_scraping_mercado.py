import pandas as pd
import difflib
import os
import sys

# --- BRÚJULA DE RUTAS ---
directorio_actual = os.path.dirname(os.path.abspath(__file__))
# Subimos 3 niveles: scripts -> cruzado -> JaJ -> ProyectoFantasy
directorio_raiz = os.path.dirname(os.path.dirname(os.path.dirname(directorio_actual)))

def obtener_rutas_cruce(temporada, jornada):
    """Genera las rutas apuntando a las carpetas correctas de tu estructura."""
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
    """Carga el diccionario. Estructura: Clave_Scraping -> Clave_Mercado"""
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
    """Guarda el diccionario, omitiendo los marcados como IGNORAR."""
    filas = [{'Clave_Scraping': k, 'Clave_Mercado': v} for k, v in diccionario.items() if v != "IGNORAR"]
    df = pd.DataFrame(filas)
    
    if not df.empty:
        df = df.sort_values(by=['Clave_Scraping'], ascending=[True])
        os.makedirs(os.path.dirname(ruta_csv), exist_ok=True)
        df.to_csv(ruta_csv, index=False, encoding='utf-8-sig')

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
    
    # 3. Preparar la información del Mercado
    info_mercado = {}
    claves_mercado = []
    
    for _, fila in df_mercado.iterrows():
        clave_m = f"{fila['Nombre']}_{fila['Equipo']}"
        display_m = f"{fila['Nombre']} | {fila['Equipo']} | {fila['Posicion']} | {fila.get('Puntos_PFSY', '0')}pts | {fila.get('Precio_Fantastica', '0')}M"
        info_mercado[clave_m] = display_m
        claves_mercado.append(clave_m)
        
    # 4. Preparar las claves del Scraping (Los directores de orquesta)
    claves_scraping = (df_scraping['Nombre'] + "_" + df_scraping['Equipo']).unique().tolist()
    
    # 5. Cargar diccionario y filtrar pendientes
    diccionario_cruce = cargar_diccionario_cruce(rutas['diccionario_cruce'])
    pendientes = [c for c in claves_scraping if c not in diccionario_cruce]
    
    # --- FASE 1: Emparejamiento Automático ---
    automaticos = 0
    for clave_s in list(pendientes):
        if clave_s in claves_mercado:
            diccionario_cruce[clave_s] = clave_s
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

    # --- FASE 2: Interactivo ---
    for clave_s in pendientes:
        nombre_s, equipo_s = clave_s.split("_", 1)
        
        print(f"\n" + "="*50)
        print(f"❓ SCRAPING HA REGISTRADO A: {nombre_s} ({equipo_s})")
        print("="*50)
        
        # 10 más parecidos en todo el mercado
        parecidos = difflib.get_close_matches(clave_s, claves_mercado, n=10, cutoff=0.1)
        
        print("0. ✍️  Escribir clave manualmente o descartar jugador")
        for i, clave_candidato in enumerate(parecidos, 1):
            print(f"{i}. {info_mercado[clave_candidato]}")
            
        while True:
            opcion = input(f"\nElige una opción (0-{len(parecidos)}): ").strip()
            if opcion.isdigit() and 0 <= int(opcion) <= len(parecidos):
                opcion = int(opcion)
                break
            print("❌ Opción no válida.")
            
        if opcion == 0:
            print("\n👉 Introduce la clave exacta del mercado (Ej: I. Benito_Osasuna)")
            manual = input("👉 O pulsa '0' de nuevo si este jugador NO está en el mercado: ").strip()
            
            if manual == '0':
                diccionario_cruce[clave_s] = "IGNORAR"
            elif manual:
                diccionario_cruce[clave_s] = manual
        else:
            elegido = parecidos[opcion - 1]
            diccionario_cruce[clave_s] = elegido
            
        guardar_diccionario_cruce(diccionario_cruce, rutas['diccionario_cruce'])

    print("\n✅ ¡Emparejamiento finalizado! Diccionario de cruce de la jornada actualizado.")

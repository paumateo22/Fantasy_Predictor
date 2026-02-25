import pandas as pd
import difflib
import os

# --- FUNCIONES DE RUTAS DINÁMICAS ---
def obtener_rutas(temporada, jornada):
    """Genera las rutas dinámicas basadas en temporada y jornada."""
    base_dir = os.path.join("JaJ", "mercado", "datasets", temporada, jornada)
    global_dir = os.path.join("JaJ", "mercado", "datasets") # <-- Carpeta global
    
    rutas = {
        'csv_entrada': [os.path.join(base_dir, "mercado_base.csv")],
        'txt_oficiales': os.path.join(global_dir, "jugadores_ordenados.txt"), # Global
        'diccionario_csv': os.path.join(global_dir, "mercado_base_relaciones.csv") # Global
    }
    return rutas

# --- FUNCIONES DE MANEJO DEL DICCIONARIO CSV ---
def cargar_diccionario_csv(ruta_diccionario_csv):
    """Lee el CSV y lo convierte en un diccionario de listas en memoria."""
    diccionario = {}
    if os.path.exists(ruta_diccionario_csv):
        try:
            df = pd.read_csv(ruta_diccionario_csv, dtype=str).dropna()
            for _, fila in df.iterrows():
                oficial = fila['Oficial']
                ocr = fila['OCR']
                if oficial not in diccionario:
                    diccionario[oficial] = []
                if ocr not in diccionario[oficial]:
                    diccionario[oficial].append(ocr)
        except Exception as e:
            print(f"⚠️ Error leyendo el diccionario CSV: {e}")
    return diccionario

def guardar_diccionario_csv(diccionario, ruta_diccionario_csv):
    """Convierte el diccionario de listas en memoria a un CSV de 2 columnas ordenado."""
    filas = []
    for oficial, lista_ocr in diccionario.items():
        for ocr in lista_ocr:
            filas.append({'Oficial': oficial, 'OCR': ocr})
    
    df = pd.DataFrame(filas)
    if not df.empty:
        # 🚨 AQUÍ ESTÁ LA MAGIA: Ordenamos alfabéticamente antes de guardar
        df = df.sort_values(by=['Oficial', 'OCR'], ascending=[True, True])
        
        # Guardamos sin índice y con utf-8-sig para que Excel lo abra perfecto
        os.makedirs(os.path.dirname(ruta_diccionario_csv), exist_ok=True)
        df.to_csv(ruta_diccionario_csv, index=False, encoding='utf-8-sig')
        
# --- FUNCIONES PRINCIPALES ---
def cargar_pool_ocr(rutas_csv):
    """Recopila todos los nombres detectados por el OCR en los CSVs."""
    nombres_ocr = set()
    for ruta in rutas_csv:
        if os.path.exists(ruta):
            try:
                df = pd.read_csv(ruta, dtype=str)
                if 'Nombre' in df.columns:
                    nombres_ocr.update(df['Nombre'].dropna().tolist())
            except Exception as e:
                print(f"⚠️ Error leyendo {ruta}: {e}")
    return list(nombres_ocr)

def crear_diccionario(temporada, jornada):
    rutas = obtener_rutas(temporada, jornada)
    ruta_txt = rutas['txt_oficiales']
    rutas_csv = rutas['csv_entrada']
    ruta_diccionario_csv = rutas['diccionario_csv']

    if not os.path.exists(ruta_txt):
        print(f"❌ No se encuentra el TXT en: {ruta_txt}")
        return
    
    with open(ruta_txt, 'r', encoding='utf-8') as f:
        oficiales = [n.strip() for n in f.read().split(',') if n.strip()]

    # 1. Cargar Diccionario desde el CSV
    diccionario = cargar_diccionario_csv(ruta_diccionario_csv)

    # 2. Cargar Piscina OCR (Lo que ha leído en esta jornada)
    nombres_ocr_totales = cargar_pool_ocr(rutas_csv)
    
    # 3. Extraer los nombres OCR que ya sabemos a quién pertenecen
    ocr_ya_mapeados = set()
    for lista_ocr in diccionario.values():
        ocr_ya_mapeados.update(lista_ocr)
        
    # Nombres que el OCR ha sacado y no están en nuestro diccionario
    ocr_pendientes = [n for n in nombres_ocr_totales if n not in ocr_ya_mapeados]

    # --- FASE 1: Emparejamiento Automático ---
    # Si por casualidad el OCR ha leído el nombre exactamente igual al del TXT,
    # lo guardamos directamente sin preguntar.
    automaticos = 0
    for ocr_name in list(ocr_pendientes):
        ocr_low = ocr_name.lower()
        match_exacto = next((of for of in oficiales if of.lower() == ocr_low), None)
        
        if match_exacto:
            if match_exacto not in diccionario:
                diccionario[match_exacto] = []
            if ocr_name not in diccionario[match_exacto]:
                diccionario[match_exacto].append(ocr_name)
                
            ocr_pendientes.remove(ocr_name)
            automaticos += 1

    # Guardado intermedio de lo automático
    guardar_diccionario_csv(diccionario, ruta_diccionario_csv)

    print(f"📄 Nombres leídos por OCR (CSV): {len(nombres_ocr_totales)}")
    print(f"📚 Jugadores oficiales (TXT): {len(oficiales)}")
    print(f"⚡ Emparejados automáticamente ahora: {automaticos}")
    print(f"💾 Jugadores con al menos un mapeo en diccionario: {len(diccionario)}")
    print(f"🏊‍♂️ Nombres OCR huérfanos a revisar: {len(ocr_pendientes)}")

    # --- FASE 2: Interactivo ---
    # Ahora iteramos SOLO por los nombres OCR que no conocemos
    for ocr_name in ocr_pendientes:
        print(f"\n" + "="*50)
        print(f"❓ ¿A qué jugador OFICIAL pertenece esta lectura del OCR?")
        print(f"👉 OCR HA LEÍDO: {ocr_name}")
        print("="*50)

        # Buscamos en el TXT los oficiales que más se parezcan a lo que ha leído el OCR
        parecidos = difflib.get_close_matches(ocr_name, oficiales, n=10, cutoff=0.1)

        print("0. ✍️  No está en la lista (Escribir nombre oficial manualmente) o saltar")
        for i, candidato in enumerate(parecidos, 1):
            print(f"{i}. {candidato}")

        while True:
            opcion = input(f"\nElige una opción (0-{len(parecidos)}): ").strip()
            if opcion.isdigit() and 0 <= int(opcion) <= len(parecidos):
                opcion = int(opcion)
                break
            print("❌ Opción no válida. Introduce un número del menú.")

        if opcion == 0:
            manual = input("Escribe el nombre OFICIAL (o pulsa Enter para saltarlo): ").strip()
            if manual:
                # Nos aseguramos de guardarlo con las mayúsculas exactas del TXT si existe
                match_manual = next((of for of in oficiales if of.lower() == manual.lower()), manual)
                if match_manual not in diccionario:
                    diccionario[match_manual] = []
                if ocr_name not in diccionario[match_manual]:
                    diccionario[match_manual].append(ocr_name)
        else:
            elegido = parecidos[opcion - 1] # Este es el nombre oficial (clave)
            if elegido not in diccionario:
                diccionario[elegido] = []
            if ocr_name not in diccionario[elegido]:
                diccionario[elegido].append(ocr_name)

        # Autoguardado silencioso tras cada respuesta
        guardar_diccionario_csv(diccionario, ruta_diccionario_csv)

    print("\n✅ ¡Revisión terminada! Diccionario completado y guardado en CSV con éxito.")

def faltantes_diccionario(temporada, jornada):
    rutas = obtener_rutas(temporada, jornada)
    ruta_txt = rutas['txt_oficiales']
    ruta_diccionario_csv = rutas['diccionario_csv']

    print("\n" + "="*50)
    print("🔍 DIAGNÓSTICO: JUGADORES FALTANTES EN EL DICCIONARIO CSV")
    print("="*50)

    if not os.path.exists(ruta_txt):
        print(f"❌ No se encuentra el archivo TXT en: {ruta_txt}")
        return
        
    with open(ruta_txt, 'r', encoding='utf-8') as f:
        oficiales = [n.strip() for n in f.read().split(',') if n.strip()]

    diccionario = cargar_diccionario_csv(ruta_diccionario_csv)
    claves_csv_low = {clave.lower() for clave in diccionario.keys()}
    
    faltantes = []
    for oficial in oficiales:
        if oficial.lower() not in claves_csv_low:
            faltantes.append(oficial)

    print(f"📚 Total de jugadores oficiales (TXT): {len(oficiales)}")
    print(f"💾 Jugadores guardados como clave (CSV): {len(diccionario.keys())}")
    print(f"❌ Jugadores faltantes: {len(faltantes)}")
    
    if faltantes:
        print("\n--- LISTA DE FALTANTES ---")
        for i, faltante in enumerate(faltantes, 1):
            print(f"{i:03d}. {faltante}")
    else:
        print("\n✅ ¡Enhorabuena! Tienes a todos los jugadores oficiales mapeados en el diccionario.")
    print("="*50 + "\n")

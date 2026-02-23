import pandas as pd
import difflib
import os

# --- RUTAS ---
rutas_csv = [
    r"JaJ\mercado\datasets\JaJ\T25-26\J25\mercado_base.csv"
]
ruta_txt = r"JaJ\mercado\datasets\jugadores_ordenados.txt"
ruta_diccionario_csv = r"JaJ\mercado\datasets\mercado_base_relaciones.csv"

# --- FUNCIONES DE MANEJO DEL DICCIONARIO CSV ---
def cargar_diccionario_csv():
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

def guardar_diccionario_csv(diccionario):
    """Convierte el diccionario de listas en memoria a un CSV de 2 columnas."""
    filas = []
    for oficial, lista_ocr in diccionario.items():
        for ocr in lista_ocr:
            filas.append({'Oficial': oficial, 'OCR': ocr})
    
    df = pd.DataFrame(filas)
    if not df.empty:
        # Guardamos sin índice y con utf-8-sig para que Excel lo abra perfecto
        df.to_csv(ruta_diccionario_csv, index=False, encoding='utf-8-sig')

# --- FUNCIONES PRINCIPALES ---
def cargar_pool_ocr():
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

def crear_o_actualizar_diccionario():
    if not os.path.exists(ruta_txt):
        print(f"❌ No se encuentra el TXT en: {ruta_txt}")
        return
    
    with open(ruta_txt, 'r', encoding='utf-8') as f:
        oficiales = [n.strip() for n in f.read().split(',') if n.strip()]

    # 1. Cargar Diccionario desde el CSV
    diccionario = cargar_diccionario_csv()

    # 2. Cargar Piscina OCR
    nombres_ocr_totales = cargar_pool_ocr()
    
    ocr_ya_mapeados = set()
    for lista_ocr in diccionario.values():
        ocr_ya_mapeados.update(lista_ocr)
        
    pool_disponible = [n for n in nombres_ocr_totales if n not in ocr_ya_mapeados]

    # --- FASE 1: Emparejamiento Automático ---
    automaticos = 0
    for oficial in oficiales:
        oficial_low = oficial.lower()
        match_exacto = next((n for n in pool_disponible if n.lower() == oficial_low), None)
        
        if match_exacto:
            if oficial not in diccionario:
                diccionario[oficial] = []
            if match_exacto not in diccionario[oficial]:
                diccionario[oficial].append(match_exacto)
                
            pool_disponible.remove(match_exacto)
            automaticos += 1

    # Guardado intermedio
    guardar_diccionario_csv(diccionario)

    print(f"📚 Jugadores oficiales (TXT): {len(oficiales)}")
    print(f"⚡ Emparejados automáticamente ahora: {automaticos}")
    print(f"💾 Jugadores con al menos un mapeo en diccionario: {len(diccionario)}")
    print(f"🏊‍♂️ Nombres OCR huérfanos en la piscina: {len(pool_disponible)}")

    # --- FASE 2: Interactivo ---
    for oficial in oficiales:
        # Si el jugador ya tiene algún mapeo en el diccionario, pasamos al siguiente
        if oficial in diccionario and len(diccionario[oficial]) > 0:
            continue
            
        # Si ya hemos asignado todos los nombres leídos por el OCR, terminamos
        if not pool_disponible:
            print("\n✅ La piscina de OCR está vacía. Todos los nombres leídos han sido asignados.")
            break

        print(f"\n" + "="*50)
        print(f"❓ ¿Quién es este jugador leído por el OCR?")
        print(f"👉 OFICIAL (TXT): {oficial}")
        print("="*50)

        parecidos = difflib.get_close_matches(oficial, pool_disponible, n=10, cutoff=0.1)

        print("0. ✍️  No está en la lista (Escribir manualmente) o saltar")
        for i, candidato in enumerate(parecidos, 1):
            print(f"{i}. {candidato}")

        while True:
            opcion = input(f"\nElige una opción (0-{len(parecidos)}): ").strip()
            if opcion.isdigit() and 0 <= int(opcion) <= len(parecidos):
                opcion = int(opcion)
                break
            print("❌ Opción no válida. Introduce un número del menú.")

        if opcion == 0:
            manual = input("Escribe cómo lo lee el OCR (o pulsa Enter para saltarlo): ").strip()
            if manual:
                if oficial not in diccionario:
                    diccionario[oficial] = []
                if manual not in diccionario[oficial]:
                    diccionario[oficial].append(manual)
                if manual in pool_disponible:
                    pool_disponible.remove(manual)
        else:
            elegido = parecidos[opcion - 1]
            if oficial not in diccionario:
                diccionario[oficial] = []
            if elegido not in diccionario[oficial]:
                diccionario[oficial].append(elegido)
            pool_disponible.remove(elegido)

        # Autoguardado silencioso tras cada respuesta
        guardar_diccionario_csv(diccionario)

    print("\n✅ ¡Revisión terminada! Diccionario completado y guardado en CSV con éxito.")

def faltantes_diccionario():
    print("\n" + "="*50)
    print("🔍 DIAGNÓSTICO: JUGADORES FALTANTES EN EL DICCIONARIO CSV")
    print("="*50)

    if not os.path.exists(ruta_txt):
        print(f"❌ No se encuentra el archivo TXT en: {ruta_txt}")
        return
        
    with open(ruta_txt, 'r', encoding='utf-8') as f:
        oficiales = [n.strip() for n in f.read().split(',') if n.strip()]

    diccionario = cargar_diccionario_csv()
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

if __name__ == '__main__':
    crear_o_actualizar_diccionario()
    faltantes_diccionario()
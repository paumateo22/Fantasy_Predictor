import pandas as pd
import difflib
import os

# --- FUNCIONES DE RUTAS DINÁMICAS ---
def obtener_rutas(temporada, jornada):
    base_dir = os.path.join("JaJ", "mercado", "datasets", temporada, jornada)
    global_dir = os.path.join("JaJ", "mercado", "datasets")
    
    rutas = {
        'csv_entrada': [os.path.join(base_dir, "mercado_base.csv")],
        'txt_oficiales': os.path.join(global_dir, "jugadores_ordenados.txt"),
        'diccionario_csv': os.path.join(global_dir, "mercado_base_relaciones.csv")
    }
    return rutas

# --- FUNCIONES DE MANEJO DEL DICCIONARIO CSV ---
def cargar_diccionario_csv(ruta_diccionario_csv):
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
    filas = []
    for oficial, lista_ocr in diccionario.items():
        for ocr in lista_ocr:
            filas.append({'Oficial': oficial, 'OCR': ocr})
    
    df = pd.DataFrame(filas)
    if not df.empty:
        df = df.sort_values(by=['Oficial', 'OCR'], ascending=[True, True])
        os.makedirs(os.path.dirname(ruta_diccionario_csv), exist_ok=True)
        df.to_csv(ruta_diccionario_csv, index=False, encoding='utf-8-sig')
        
# --- FUNCIONES PRINCIPALES ---
def cargar_pool_ocr_completo(rutas_csv):
    """Recopila la información entera de todos los nombres detectados por el OCR."""
    nombres_ocr_dict = {}
    for ruta in rutas_csv:
        if os.path.exists(ruta):
            try:
                df = pd.read_csv(ruta, dtype=str).fillna("N/A")
                for _, fila in df.iterrows():
                    nombre = str(fila.get('Nombre', '')).strip()
                    if nombre and nombre not in nombres_ocr_dict:
                        nombres_ocr_dict[nombre] = fila.to_dict()
            except Exception as e:
                print(f"⚠️ Error leyendo {ruta}: {e}")
    return nombres_ocr_dict

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

    # 1. Cargar Diccionario
    diccionario = cargar_diccionario_csv(ruta_diccionario_csv)

    # 2. Cargar Piscina OCR Completa (Diccionario de información)
    pool_datos_ocr = cargar_pool_ocr_completo(rutas_csv)
    nombres_ocr_totales = list(pool_datos_ocr.keys())
    
    # 3. Extraer mapeados
    ocr_ya_mapeados = set()
    for lista_ocr in diccionario.values():
        ocr_ya_mapeados.update(lista_ocr)
        
    ocr_pendientes = [n for n in nombres_ocr_totales if n not in ocr_ya_mapeados]

    # --- FASE 1: Emparejamiento Automático ---
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

    guardar_diccionario_csv(diccionario, ruta_diccionario_csv)

    print(f"📄 Nombres leídos por OCR (CSV): {len(nombres_ocr_totales)}")
    print(f"📚 Jugadores oficiales (TXT): {len(oficiales)}")
    print(f"⚡ Emparejados automáticamente ahora: {automaticos}")
    print(f"💾 Jugadores con al menos un mapeo en diccionario: {len(diccionario)}")
    print(f"🏊‍♂️ Nombres OCR huérfanos a revisar: {len(ocr_pendientes)}")

    # --- FASE 2: Interactivo ---
    for ocr_name in ocr_pendientes:
        
        # Extraemos toda la información del diccionario que hemos creado
        fila_ocr = pool_datos_ocr.get(ocr_name, {})
        equipo = fila_ocr.get('Equipo', 'N/A')
        posicion = fila_ocr.get('Posicion', 'N/A')
        puntos = fila_ocr.get('Puntos_PFSY', 'N/A')
        precio = fila_ocr.get('Precio_Fantastica', 'N/A')

        print(f"\n" + "="*50)
        print(f"❓ ¿A qué jugador OFICIAL pertenece esta lectura del OCR?")
        # 🚨 LA MAGIA: Imprime toda la línea detallada
        print(f"👉 OCR HA LEÍDO: {ocr_name} | {equipo} | {posicion} | {puntos} Pts | {precio}M")
        print("="*50)

        parecidos = difflib.get_close_matches(ocr_name, oficiales, n=10, cutoff=0.1)

        print("0. ✍️  No está en la lista (Escribir nombre oficial manualmente) o saltar")
        for i, candidato in enumerate(parecidos, 1):
            print(f"{i}. {candidato}")

        while True:
            opcion = input(f"\nElige una opción (0-{len(parecidos)}): ").strip()
            if opcion.isdigit() and 0 <= int(opcion) <= len(parecidos):
                opcion = int(opcion)
                break
            print("❌ Opción no válida.")

        if opcion == 0:
            manual = input("Escribe el nombre OFICIAL (o pulsa Enter para saltarlo): ").strip()
            if manual:
                match_manual = next((of for of in oficiales if of.lower() == manual.lower()), manual)
                if match_manual not in diccionario:
                    diccionario[match_manual] = []
                if ocr_name not in diccionario[match_manual]:
                    diccionario[match_manual].append(ocr_name)
        else:
            elegido = parecidos[opcion - 1] 
            if elegido not in diccionario:
                diccionario[elegido] = []
            if ocr_name not in diccionario[elegido]:
                diccionario[elegido].append(ocr_name)

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

    print(f"📚 Total de jugadores oficiales (TXT): {len(oficiales)}")
    print(f"💾 Jugadores guardados como clave (CSV): {len(diccionario.keys())}")
    
    print("="*50 + "\n")

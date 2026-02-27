import pandas as pd
import os
import sys

# --- BRÚJULA DE RUTAS ---
directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_raiz = os.path.dirname(os.path.dirname(os.path.dirname(directorio_actual)))

def obtener_rutas_fusion(temporada, jornada):
    # Rutas de origen (donde leemos los datos)
    dir_mercado = os.path.join(directorio_raiz, "JaJ", "mercado", "datasets", temporada, jornada)
    dir_scraping = os.path.join(directorio_raiz, "JaJ", "scraping", "datasets", temporada, jornada)
    dir_cruzado = os.path.join(directorio_raiz, "JaJ", "cruzado", "datasets", temporada, jornada)
    dir_global = os.path.join(directorio_raiz, "JaJ", "cruzado", "datasets") # Carpeta global para el registro
    
    # 🚨 NUEVA RUTA DE SALIDA (Raíz del proyecto)
    dir_salida_final = os.path.join(directorio_raiz, "datasets", "JaJ", temporada, jornada)
    
    return {
        'mercado': os.path.join(dir_mercado, "mercado_limpio.csv"),
        'scraping': os.path.join(dir_scraping, "jugadores.csv"),
        'diccionario': os.path.join(dir_cruzado, "relaciones_scraping_mercado.csv"),
        'registro_pos': os.path.join(dir_global, "registro_posiciones.csv"),
        
        # Archivos finales en su nueva ubicación
        'salida_csv': os.path.join(dir_salida_final, "jugadores+mercado.csv"),
        'salida_log': os.path.join(dir_salida_final, "log_disparidades.txt")
    }

# --- FUNCIONES DEL REGISTRO DE POSICIONES ---
def cargar_registro_posiciones(ruta):
    """Carga el registro global de posiciones (Clave_Jugador -> Posición)"""
    if os.path.exists(ruta):
        try:
            df = pd.read_csv(ruta, dtype=str)
            return dict(zip(df['Clave_Jugador'], df['Posicion']))
        except Exception as e:
            print(f"⚠️ Error leyendo el registro de posiciones: {e}")
    return {}

def guardar_registro_posiciones(registro, ruta):
    """Guarda el registro actualizado y ordenado alfabéticamente"""
    if registro:
        df = pd.DataFrame(list(registro.items()), columns=['Clave_Jugador', 'Posicion'])
        df = df.sort_values(by=['Clave_Jugador'])
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        df.to_csv(ruta, index=False, encoding='utf-8-sig')

def fusionar_datos_jornada(temporada, jornada):
    rutas = obtener_rutas_fusion(temporada, jornada)
    
    # 1. Validar ingredientes básicos
    for nombre in ['mercado', 'scraping', 'diccionario']:
        if not os.path.exists(rutas[nombre]):
            print(f"❌ Falta el archivo {nombre}: {rutas[nombre]}")
            return

    print("\n" + "="*50)
    print(f" 🧬 INICIANDO FUSIÓN DE BASES DE DATOS ({jornada})")
    print("="*50)

    # 2. Cargar los DataFrames y Diccionarios
    df_mercado = pd.read_csv(rutas['mercado'], dtype=str).fillna("N/A")
    df_scraping = pd.read_csv(rutas['scraping'], dtype=str).fillna("N/A")
    df_diccionario = pd.read_csv(rutas['diccionario'], dtype=str)
    
    # NUEVO: Cargamos el juez de posiciones
    registro_posiciones = cargar_registro_posiciones(rutas['registro_pos'])
    registro_modificado = False

    dict_mercado = {f"{f['Nombre']}_{f['Equipo']}": f.to_dict() for _, f in df_mercado.iterrows()}
    dict_scraping = {f"{f['Nombre']}_{f['Equipo']}": f.to_dict() for _, f in df_scraping.iterrows()}

    # 3. Preparar variables para la fusión
    filas_finales = []
    registro_errores = []
    
    registro_errores.append(f"--- REPORTE DE AUDITORÍA (OCR vs REGISTROS) | {temporada} - {jornada} ---\n")

    # 4. Cruzar los datos
    for _, relacion in df_diccionario.iterrows():
        clave_s = relacion['Clave_Scraping']
        clave_m = relacion['Clave_Mercado']
        
        if clave_m == "IGNORAR" or pd.isna(clave_m):
            continue

        jugador_s = dict_scraping.get(clave_s)
        jugador_m = dict_mercado.get(clave_m)

        if jugador_s and jugador_m:
            disparidades = []
            
            # --- 🚀 NUEVA LÓGICA DE POSICIONES ---
            pos_ocr = jugador_m.get('Posicion', 'Desconocido')
            pos_scraping = jugador_s.get('Posicion', 'Desconocido')
            
            # Si el jugador ya existe en nuestro registro maestro
            if clave_s in registro_posiciones:
                pos_final = registro_posiciones[clave_s]
                # Auditamos: ¿El OCR leyó algo distinto a lo que sabemos que es la verdad?
                if pos_ocr != pos_final and pos_ocr != 'Desconocido':
                    disparidades.append(f"Posición (OCR falló: leyó '{pos_ocr}' -> Nuestro registro dice '{pos_final}')")
            else:
                # Si es un jugador nuevo, confiamos en el OCR y lo guardamos
                pos_final = pos_ocr
                if pos_final != 'Desconocido': # Evitamos guardar basura en el registro
                    registro_posiciones[clave_s] = pos_final
                    registro_modificado = True
            
            # (El "Desconocido" del scraping se ignora por completo de las disparidades, como pediste)

            # --- LÓGICA DE PUNTOS (OCR vs Scraping) ---
            pts_ocr = jugador_m.get('Puntos_PFSY', 'N/A')
            pts_scraping = jugador_s.get('Puntos_Totales', 'N/A')
            if pts_ocr != "N/A" and pts_scraping != "N/A" and str(pts_ocr) != str(pts_scraping):
                disparidades.append(f"Puntos (OCR leyó: {pts_ocr} -> Scraping oficial: {pts_scraping})")

            # Añadir al log si hay fallos
            if disparidades:
                registro_errores.append(f"⚠️ {jugador_s['Nombre']} ({jugador_s['Equipo']}):")
                for d in disparidades:
                    registro_errores.append(f"   - {d}")
                registro_errores.append("")

            # --- FUSIÓN (Creando la fila perfecta) ---
            fila_fusionada = jugador_s.copy()
            fila_fusionada['Precio_Fantastica'] = jugador_m.get('Precio_Fantastica', 'N/A')
            fila_fusionada['Posicion'] = pos_final # Imponemos la posición del OCR/Registro
            
            filas_finales.append(fila_fusionada)

    # 5. Guardar el Registro de Posiciones si hubo jugadores nuevos
    if registro_modificado:
        guardar_registro_posiciones(registro_posiciones, rutas['registro_pos'])
        print(f"📗 Registro global de posiciones actualizado.")

    # 6. Guardar el DataFrame Final Enriquecido
    df_final = pd.DataFrame(filas_finales)
    
    # Reordenamos columnas para estética (Precio después de Posición)
    cols = df_final.columns.tolist()
    if 'Precio_Fantastica' in cols and 'Posicion' in cols:
        cols.insert(cols.index('Posicion') + 1, cols.pop(cols.index('Precio_Fantastica')))
        df_final = df_final[cols]

    # Creamos las carpetas necesarias en la raíz y guardamos
    os.makedirs(os.path.dirname(rutas['salida_csv']), exist_ok=True)
    df_final.to_csv(rutas['salida_csv'], index=False, encoding='utf-8-sig')

    # 7. Guardar el Log de Disparidades
    with open(rutas['salida_log'], 'w', encoding='utf-8') as f:
        f.write("\n".join(registro_errores))

    print(f"✅ ¡Fusión completada con éxito!")
    print(f"💾 Base de datos final guardada en: {rutas['salida_csv']}")
    print(f"📝 Reporte de auditoría guardado en: {rutas['salida_log']}")
    print(f"📊 Jugadores procesados: {len(filas_finales)}")
    print("="*50 + "\n")

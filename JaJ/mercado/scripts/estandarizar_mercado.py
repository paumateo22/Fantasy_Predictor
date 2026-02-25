import pandas as pd
import os

def estandarizar_mercado_jornada(temporada, jornada):
    directorio_base = os.path.join("JaJ", "mercado", "datasets", temporada, jornada)
    
    ruta_raw = os.path.join(directorio_base, "mercado_base.csv")
    ruta_salida = os.path.join(directorio_base, "mercado_estandarizado.csv")
    
    # El diccionario lo dejamos a nivel global (datasets) para que acumule conocimiento toda la temporada
    ruta_diccionario_csv = os.path.join("JaJ", "mercado", "datasets", "mercado_base_relaciones.csv")

    print("\n" + "="*50)
    print(f" ⚙️ INICIANDO ESTANDARIZACIÓN - {jornada} ({temporada})")
    print("="*50)

    # 1. Comprobar que existen los archivos necesarios
    if not os.path.exists(ruta_raw):
        print(f"❌ No se encuentra el CSV original en: {ruta_raw}")
        return
    if not os.path.exists(ruta_diccionario_csv):
        print(f"❌ No se encuentra el diccionario en: {ruta_diccionario_csv}")
        print("👉 Recuerda ejecutar primero el Paso 3 (crear_diccionario) para generarlo.")
        return

    # 2. Cargar el diccionario CSV y preparar el mapa de traducción
    print("⏳ Cargando diccionario de relaciones...")
    df_diccionario = pd.read_csv(ruta_diccionario_csv, dtype=str)
    
    # Creamos un diccionario interno { "ocr_en_minusculas": "Oficial" } para que no falle por mayúsculas
    mapa_correcciones = {}
    for _, fila in df_diccionario.iterrows():
        oficial = fila['Oficial']
        ocr = fila['OCR']
        # Nos aseguramos de que no haya celdas vacías por error
        if pd.notna(oficial) and pd.notna(ocr):
            mapa_correcciones[ocr.strip().lower()] = oficial.strip()

    # 3. Cargar el mercado original
    print("⏳ Procesando el mercado base...")
    df_mercado = pd.read_csv(ruta_raw, dtype=str)
    
    if 'Nombre' not in df_mercado.columns:
        print("❌ Error: El archivo mercado_base.csv no tiene una columna 'Nombre'.")
        return

    # 4. Traducir los nombres
    nombres_corregidos = 0
    for idx, fila in df_mercado.iterrows():
        nombre_ocr = str(fila['Nombre']).strip()
        nombre_low = nombre_ocr.lower()
        
        # Si el nombre leído por el OCR está en nuestro diccionario, lo sustituimos
        if nombre_low in mapa_correcciones:
            nombre_oficial = mapa_correcciones[nombre_low]
            
            # Solo sumamos al contador si realmente ha habido un cambio visual
            if nombre_ocr != nombre_oficial:
                df_mercado.at[idx, 'Nombre'] = nombre_oficial
                nombres_corregidos += 1

    # 5. Guardar el nuevo dataset estandarizado
    # Usamos utf-8-sig para que Excel lea las tildes perfectamente al abrirlo
    df_mercado.to_csv(ruta_salida, index=False, encoding='utf-8-sig')

    # --- RESUMEN FINAL ---
    print("\n✅ PROCESO DE ESTANDARIZACIÓN COMPLETADO")
    print(f"📄 Archivo original: {os.path.basename(ruta_raw)}")
    print(f"💾 Archivo generado: {os.path.basename(ruta_salida)}")
    print(f"🔄 Nombres corregidos: {nombres_corregidos}")
    print("="*50 + "\n")
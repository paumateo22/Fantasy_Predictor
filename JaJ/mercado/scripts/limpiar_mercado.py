import pandas as pd
import os

def limpiar_mercado_jornada(temporada, jornada):
    # Ajustamos la ruta para que encaje con tu estructura exacta
    directorio_base = os.path.join("JaJ", "mercado", "datasets", temporada, jornada)    

    ruta_entrada = os.path.join(directorio_base, "mercado_estandarizado.csv")
    ruta_salida = os.path.join(directorio_base, "mercado_limpio.csv")

    print("\n" + "="*50)
    print(f" 🧹 INICIANDO LIMPIEZA FINAL - {jornada} ({temporada})")
    print("="*50)

    # 1. Comprobar que existe el archivo estandarizado
    if not os.path.exists(ruta_entrada):
        print(f"❌ No se encuentra el CSV estandarizado en: {ruta_entrada}")
        print("👉 Recuerda ejecutar primero el Paso 4 (estandarizar_mercado).")
        return

    print("⏳ Limpiando y ordenando datos...")
    # Leemos todo como texto para evitar que pandas modifique formatos de números
    df = pd.read_csv(ruta_entrada, dtype=str)
    
    registros_originales = len(df)
    
    # 2. Eliminar filas exactamente iguales
    df = df.drop_duplicates()
    registros_unicos = len(df)
    duplicados_eliminados = registros_originales - registros_unicos
    
    # 3. Ordenar alfabéticamente por la columna 'Nombre'
    if 'Nombre' in df.columns:
        df = df.sort_values(by='Nombre', ascending=True)
    else:
        # Fallback a la primera columna si por algún motivo no se llama 'Nombre'
        columna_nombre = df.columns[0]
        df = df.sort_values(by=columna_nombre, ascending=True)
    
    # 4. Guardar el resultado final
    # Usamos utf-8-sig para la compatibilidad perfecta con Excel
    os.makedirs(directorio_base, exist_ok=True)
    df.to_csv(ruta_salida, index=False, encoding='utf-8-sig')
    
    # --- RESUMEN FINAL ---
    print(f"\n✅ PROCESO DE LIMPIEZA COMPLETADO")
    print(f"🗑️ Duplicados eliminados: {duplicados_eliminados}")
    print(f"💾 Archivo final guardado: {os.path.basename(ruta_salida)}")
    print(f"📊 Total de jugadores únicos en el mercado: {registros_unicos}")
    print("="*50 + "\n")
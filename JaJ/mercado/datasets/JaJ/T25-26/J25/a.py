import pandas as pd

def limpiar_y_ordenar_csv(ruta_archivo):
    # Usamos r"" para que Windows no se líe con las barras \
    df = pd.read_csv(ruta_archivo)
    
    # 1. Eliminar filas exactamente iguales
    df = df.drop_duplicates()
    
    # 2. Ordenar alfabéticamente por la primera columna (el nombre)
    columna_nombre = df.columns[0]
    df = df.sort_values(by=columna_nombre, ascending=True)
    
    # Guardar el resultado
    df.to_csv("mercado_limpio_y_ordenado.csv", index=False)
    
    print(f"✅ Proceso completado.")
    print(f"Archivo guardado como: mercado_limpio_y_ordenado.csv")
    print(f"Total de registros únicos: {len(df)}")

# Tu ruta específica
ruta = r"JaJ\mercado\datasets\JaJ\T25-26\J25\mercado_estandarizado.csv"
limpiar_y_ordenar_csv(ruta)

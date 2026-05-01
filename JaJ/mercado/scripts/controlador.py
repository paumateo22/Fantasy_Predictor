from procesar_capturas import preparar_imagenes
from extraccion_mercado import extraer_mercado_jornada
from crear_diccionario import crear_diccionario, faltantes_diccionario
from estandarizar_mercado import estandarizar_mercado_jornada
from limpiar_mercado import limpiar_mercado_jornada

"""
El flujo que se debería seguir es:
1. Preparar las imágenes: procesar_capturas.py
2. Extraer datos: extraccion_mercado.py & auxiliar_mercado.py
3. Preparar guardado: crear_diccionario.py
4. Guardar datos: estandarizar_mercado.py
5. Limpiar y ordenar datos: limpiar_mercado.py
"""

def ejecutar_pipeline(temporada, jornada):
    
    # ---------------|| PASO 1 ||---------------
    try:
        preparar_imagenes(temporada, jornada)
    except Exception as e:
        print(f"\n❌ Error fatal en el Paso 1: {e}")
        return
    
    # ---------------|| PASO 2 ||---------------
    try:
        extraer_mercado_jornada(temporada, jornada)
    except Exception as e:
        print(f"\n❌ Error fatal en el Paso 2: {e}")
        return
    
    # ---------------|| PASO 3 ||---------------
    try:
        crear_diccionario(temporada, jornada)
        faltantes_diccionario(temporada, jornada)
    except Exception as e:
        print(f"\n❌ Error fatal en el Paso 3: {e}")
        return
    
    # ---------------|| PASO 4 ||---------------
    try:
        estandarizar_mercado_jornada(temporada, jornada)
    except Exception as e:
        print(f"\n❌ Error fatal en el Paso 4: {e}")
        return
    
    # ---------------|| PASO 5 ||---------------
    try:
        limpiar_mercado_jornada(temporada, jornada)
    except Exception as e:
        print(f"\n❌ Error fatal en el Paso 5: {e}")
        return



if __name__ == "__main__":
    TEMPORADA_ACTUAL = "T25-26"
    JORNADA_ACTUAL = "J34"
    
    ejecutar_pipeline(TEMPORADA_ACTUAL, JORNADA_ACTUAL)
from procesar_capturas import preparar_imagenes
from extraccion_mercado import extraer_mercado_jornada

def ejecutar_pipeline(temporada, jornada):    
    try:
        preparar_imagenes(temporada, jornada)
    except Exception as e:
        print(f"\n❌ Error fatal en el Paso 1: {e}")
        return

    try:
        datos = extraer_mercado_jornada(temporada, jornada)
    except Exception as e:
        print(f"\n❌ Error fatal en el Paso 2: {e}")
        return


if __name__ == "__main__":
    TEMPORADA_ACTUAL = "T25-26"
    JORNADA_ACTUAL = "J25"
    
    ejecutar_pipeline(TEMPORADA_ACTUAL, JORNADA_ACTUAL)
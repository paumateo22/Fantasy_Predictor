import os
import sys

# Nos aseguramos de que Python pueda leer los módulos de esta misma carpeta
directorio_actual = os.path.dirname(os.path.abspath(__file__))
if directorio_actual not in sys.path:
    sys.path.append(directorio_actual)

from relacionar_scraping_mercado import relacionar_bases_datos
from cruzar_bases import fusionar_datos_jornada

def ejecutar_pipeline_cruzado(temporada, jornada):
    print("\n" + "★"*60)
    print(f" 🚀 INICIANDO PIPELINE DE FUSIÓN: {temporada} - {jornada}")
    print("★"*60)

    # ---------------|| PASO 1: RELACIONAR (MATCHMAKER) ||---------------
    try:
        relacionar_bases_datos(temporada, jornada)
    except Exception as e:
        print(f"\n❌ Error fatal en el Paso 1 (Matchmaker): {e}")
        return
    
    # ---------------|| PASO 2: FUSIONAR Y AUDITAR ||---------------
    try:
        fusionar_datos_jornada(temporada, jornada)
    except Exception as e:
        print(f"\n❌ Error fatal en el Paso 2 (Fusión y Auditoría): {e}")
        return
    
    print("\n" + "★"*60)
    print(" 🎉 PIPELINE DE FUSIÓN COMPLETADO CON ÉXITO 🎉")
    print("★"*60 + "\n")

if __name__ == "__main__":
    TEMPORADA_ACTUAL = "T25-26"
    JORNADA_ACTUAL = "J30"
    
    ejecutar_pipeline_cruzado(TEMPORADA_ACTUAL, JORNADA_ACTUAL)
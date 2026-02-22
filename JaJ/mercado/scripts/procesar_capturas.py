import cv2
import os
import glob

def preparar_imagenes(temporada, jornada, recorte_superior_pct=0.275, recorte_inferior_pct=0.21, recorte_lateral_izq=0.155):
    directorio_scripts = os.path.dirname(os.path.abspath(__file__))
    carpeta_raiz = os.path.dirname(directorio_scripts) 
    
    carpeta_origen = os.path.join(carpeta_raiz, "fuentes", "capturas_raw", temporada, jornada)
    carpeta_destino = os.path.join(carpeta_raiz, "fuentes", "capturas_pro", temporada, jornada)
    
    if not os.path.exists(carpeta_origen):
        print(f"❌ Error: No existe la carpeta {carpeta_origen}")
        return False

    os.makedirs(carpeta_destino, exist_ok=True)
    rutas_imagenes = glob.glob(os.path.join(carpeta_origen, "*.[jp][pn]g"))
    
    print(f"✂️  Recortando {len(rutas_imagenes)} capturas de {temporada} - {jornada}...")

    for i, ruta in enumerate(rutas_imagenes, 1):
        nombre_archivo = os.path.basename(ruta)
        imagen = cv2.imread(ruta)
        
        if imagen is None: continue

        # Calculamos los píxeles exactos para cortar la UI del móvil
        alto_total = imagen.shape[0]
        
        if i == len(rutas_imagenes):
            pixel_inicio_y = int(alto_total * (recorte_superior_pct+0.03))
            pixel_fin_y = alto_total - int(alto_total * (recorte_inferior_pct-0.025))
            pixel_inicio_x = int(imagen.shape[1] * recorte_lateral_izq)


        else:
            pixel_inicio_y = int(alto_total * recorte_superior_pct)
            pixel_fin_y = alto_total - int(alto_total * recorte_inferior_pct)
            pixel_inicio_x = int(imagen.shape[1] * recorte_lateral_izq)

            # Cortamos y guardamos
        imagen_recortada = imagen[pixel_inicio_y:pixel_fin_y, pixel_inicio_x: ]
        cv2.imwrite(os.path.join(carpeta_destino, nombre_archivo), imagen_recortada)

    print(f"✅ ¡Listo! Guardadas en 'capturas_pro'.")

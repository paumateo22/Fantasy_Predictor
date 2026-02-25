import cv2
import numpy as np
import easyocr
import os
import sys
import pandas as pd
import glob

directorio_actual = os.path.dirname(os.path.abspath(__file__))

# 1. Brújula para Importaciones (Subimos 3 niveles hasta ProyectoFantasy)
directorio_proyecto = os.path.dirname(os.path.dirname(os.path.dirname(directorio_actual)))
if directorio_proyecto not in sys.path:
    sys.path.append(directorio_proyecto)

# 2. Brújula para Archivos (Subimos 1 nivel hasta JaJ/mercado)
carpeta_mercado = os.path.dirname(directorio_actual)

from auxiliar_mercado import obtener_posicion_por_color, aplicar_filtro_cascada, extraer_datos_divididos

def extraer_mercado_jornada(temporada, jornada):
    # Buscamos las fotos en JaJ/mercado/fuentes/...
    carpeta_pro = os.path.join(carpeta_mercado, "fuentes", "capturas_pro", temporada, jornada)

    if not os.path.exists(carpeta_pro):
        print(f"❌ Carpeta no encontrada: {carpeta_pro}")
        return
        
    rutas = glob.glob(os.path.join(carpeta_pro, "*.[jp][pn]g"))
    if not rutas:
        print(f"⚠️ No hay imágenes para procesar en: {carpeta_pro}")
        return

    # 🚨 NUEVO: Preguntas interactivas antes de empezar
    print("\n" + "="*50)
    print(" 🛠️  CONFIGURACIÓN DE EXTRACCIÓN")
    print("="*50)
    
    val_normal = input("👉 ¿Cuántos jugadores hay por imagen (por defecto 7)?: ").strip()
    esperados_normal = int(val_normal) if val_normal.isdigit() else 7
    
    val_ultima = input("👉 ¿Cuántos jugadores hay en la ÚLTIMA imagen?: ").strip()
    esperados_ultima = int(val_ultima) if val_ultima.isdigit() else 7
    print("="*50 + "\n")

    lector = easyocr.Reader(['es'], gpu=True) 
    base_datos_mercado = {}
    
    for i, ruta in enumerate(rutas, 1):
        nombre_archivo = os.path.basename(ruta)
        frame = cv2.imread(ruta)
        if frame is None: continue
        alto, ancho = frame.shape[:2]
        corte_x = int(ancho * 0.66)
        
        mask = cv2.inRange(frame, np.array([20, 8, 8]), np.array([39, 27, 27]))
        filas = np.where(np.sum(mask == 255, axis=1) > ancho * 0.60)[0]
        
        cortes_y = [0]
        if len(filas) > 0:
            curr = filas[0]
            for y in filas[1:]:
                if y - curr > 30: cortes_y.append(curr); curr = y
            cortes_y.append(curr)
        cortes_y.append(alto)

        usar_lineas = len(cortes_y) == 8
        print(f"\n--- [{i}/{len(rutas)}] {nombre_archivo} ---")
        
        jugadores_en_imagen = 0
        
        # Determinamos cuántos jugadores deberíamos encontrar en ESTA imagen en concreto
        esperados_actual = esperados_ultima if i == len(rutas) else esperados_normal
        
        for j in range(7):
            y1 = max(0, cortes_y[j] - 5) if usar_lineas else max(0, j*(alto//7)-25)
            y2 = min(alto, cortes_y[j+1] + 2) if usar_lineas else min(alto, (j+1)*(alto//7)+25)
            
            tira = frame[y1:y2, :]
            t_izq, t_der = tira[:, :corte_x], tira[:, corte_x:]
            pos_color = obtener_posicion_por_color(t_izq)
            
            jugador_cons = None
            for intento in range(1, 4):
                res_izq = lector.readtext(aplicar_filtro_cascada(t_izq, intento))
                res_der = lector.readtext(aplicar_filtro_cascada(t_der, intento))
                txt_izq = [t for (_, t, c) in res_izq if c > 0.2]
                txt_der = [t for (_, t, c) in res_der if c > 0.2] 
                
                # Restaurado el print de RAYOS X tal y como pediste
                print(f"      [RAYOS X - F{j+1} Int{intento}] IZQ: {txt_izq} | DER: {txt_der}")
                
                intent_datos = extraer_datos_divididos(txt_izq, txt_der)
                if intent_datos:
                    if pos_color != 'Desconocido': intent_datos['Posicion'] = pos_color
                    if jugador_cons is None: jugador_cons = intent_datos
                    else:
                        if jugador_cons['Precio_Fantastica'] is None: jugador_cons['Precio_Fantastica'] = intent_datos['Precio_Fantastica']
                        if jugador_cons['Puntos_PFSY'] is None: jugador_cons['Puntos_PFSY'] = intent_datos['Puntos_PFSY']
                        if jugador_cons['Posicion'] == 'Delantero' and intent_datos['Posicion'] != 'Delantero': jugador_cons['Posicion'] = intent_datos['Posicion']
                        if jugador_cons['Equipo'] == 'Desconocido': jugador_cons['Equipo'] = intent_datos['Equipo']
                    
                    if jugador_cons['Precio_Fantastica'] and jugador_cons['Puntos_PFSY'] is not None and jugador_cons['Equipo'] != 'Desconocido':
                        break

            if jugador_cons:
                clave = f"{jugador_cons['Nombre']}_{jugador_cons['Equipo']}"
                if clave not in base_datos_mercado:
                    base_datos_mercado[clave] = jugador_cons
                    
                print(f"  🔍 {jugador_cons['Nombre']:<15} | {jugador_cons['Equipo']:<12} | {jugador_cons['Posicion']:<13} | {jugador_cons['Precio_Fantastica']}M | {jugador_cons['Puntos_PFSY']} Puntos")
                jugadores_en_imagen += 1

        # 🚨 NUEVO: Comprobación y guardado de la imagen si falla
        print("-" * 40)
        if jugadores_en_imagen < esperados_actual:
            print(f"  🔴 AVISO: Se esperaban {esperados_actual} jugadores pero se detectaron {jugadores_en_imagen}.")
            
            # Ruta donde se guardará la imagen defectuosa
            carpeta_datasets = os.path.join(carpeta_mercado, "datasets", temporada, jornada)
            os.makedirs(carpeta_datasets, exist_ok=True)
            
            # Formato: Ej. "6_registrados_Screenshot_2024.jpg"
            nombre_error = f"{jugadores_en_imagen}_registrados_{nombre_archivo}"
            ruta_guardado_error = os.path.join(carpeta_datasets, nombre_error)
            
            cv2.imwrite(ruta_guardado_error, frame)
            print(f"  📸 Imagen guardada para revisión en: {ruta_guardado_error}")
        else:
            print(f"  🟢 OK: {jugadores_en_imagen}/{esperados_actual} jugadores detectados.")

    df = pd.DataFrame(list(base_datos_mercado.values()))
    
    # 🚨 GUARDADO ESTÁNDAR DEL CSV (En JaJ/mercado/datasets/...)
    ruta_csv_base = os.path.join(carpeta_mercado, "datasets", temporada, jornada, "mercado_base.csv")
    os.makedirs(os.path.dirname(ruta_csv_base), exist_ok=True)
    
    df.to_csv(ruta_csv_base, index=False, encoding='utf-8-sig')
    print(f"\n✅ Archivo de mercado guardado en: {ruta_csv_base}")
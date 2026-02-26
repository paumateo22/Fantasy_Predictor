import cv2
import numpy as np
import easyocr
import os
import sys
import pandas as pd
import glob

directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_proyecto = os.path.dirname(os.path.dirname(os.path.dirname(directorio_actual)))
if directorio_proyecto not in sys.path:
    sys.path.append(directorio_proyecto)

carpeta_mercado = os.path.dirname(directorio_actual)

from auxiliar.comprobar_archivo import obtener_nombre_archivo_unico
from auxiliar_mercado import obtener_posicion_por_color, aplicar_filtro_cascada, extraer_datos_divididos

def extraer_mercado_jornada(temporada, jornada):
    carpeta_pro = os.path.join(carpeta_mercado, "fuentes", "capturas_pro", temporada, jornada)

    if not os.path.exists(carpeta_pro):
        print(f"❌ Carpeta no encontrada: {carpeta_pro}")
        return
        
    rutas = glob.glob(os.path.join(carpeta_pro, "*.[jp][pn]g"))
    if not rutas:
        print(f"⚠️ No hay imágenes para procesar en: {carpeta_pro}")
        return

    print("\n" + "="*50)
    print(" 🛠️  CONFIGURACIÓN DE EXTRACCIÓN")
    print("="*50)
    
    val_normal = input("👉 ¿Cuántos jugadores hay por imagen (por defecto 7)?: ").strip()
    esperados_normal = int(val_normal) if val_normal.isdigit() else 7
    
    val_ultima = input("👉 ¿Cuántos jugadores hay en la ÚLTIMA imagen?: ").strip()
    esperados_ultima = int(val_ultima) if val_ultima.isdigit() else 7
    print("="*50 + "\n")

    # Calculamos la meta absoluta de jugadores
    total_imagenes = len(rutas)
    meta_jugadores = (total_imagenes - 1) * esperados_normal + esperados_ultima

    lector = easyocr.Reader(['es'], gpu=True) 
    base_datos_mercado = {}
    
    # Aquí guardaremos las imágenes que necesitan revisión manual
    imagenes_con_fallos = []

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
        print(f"\n--- [{i}/{total_imagenes}] {nombre_archivo} ---")
        
        # OJO: Ahora contamos cuántos jugadores NUEVOS se registran
        jugadores_nuevos_en_imagen = 0
        esperados_actual = esperados_ultima if i == total_imagenes else esperados_normal
        
        historial_rayos_x = []
        jugadores_extraidos_aqui = []

        for j in range(7):
            y1 = max(0, cortes_y[j] - 5) if usar_lineas else max(0, j*(alto//7)-25)
            y2 = min(alto, cortes_y[j+1] + 2) if usar_lineas else min(alto, (j+1)*(alto//7)+25)
            
            tira = frame[y1:y2, :]
            t_izq, t_der = tira[:, :corte_x], tira[:, corte_x:]
            pos_color = obtener_posicion_por_color(t_izq)
            
            jugador_cons = None
            textos_leidos = ""

            for intento in range(1, 4):
                res_izq = lector.readtext(aplicar_filtro_cascada(t_izq, intento))
                res_der = lector.readtext(aplicar_filtro_cascada(t_der, intento))
                txt_izq = [t for (_, t, c) in res_izq if c > 0.2]
                txt_der = [t for (_, t, c) in res_der if c > 0.2] 
                
                print(f"      [RAYOS X - F{j+1} Int{intento}] IZQ: {txt_izq} | DER: {txt_der}")
                textos_leidos += f"Int{intento} IZQ: {txt_izq} | DER: {txt_der}\n"
                
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

            # Guardamos los rayos X de esta fila por si la imagen falla
            historial_rayos_x.append(f"Fila {j+1}:\n{textos_leidos}")

            if jugador_cons:
                clave = f"{jugador_cons['Nombre']}_{jugador_cons['Equipo']}"
                
                # Comprobamos que sea un jugador que no hemos visto ya
                if clave not in base_datos_mercado:
                    base_datos_mercado[clave] = jugador_cons
                    jugadores_nuevos_en_imagen += 1
                    
                print(f"  🔍 {jugador_cons['Nombre']:<15} | {jugador_cons['Equipo']:<12} | {jugador_cons['Posicion']:<13} | {jugador_cons['Precio_Fantastica']}M | {jugador_cons['Puntos_PFSY']} Puntos")
                jugadores_extraidos_aqui.append(f"{jugador_cons['Nombre']} ({jugador_cons['Equipo']})")

        print("-" * 40)
        # Verificamos los registros nuevos contra lo que esperamos
        if jugadores_nuevos_en_imagen < esperados_actual:
            print(f"  🔴 AVISO: Se esperaban {esperados_actual} jugadores nuevos pero se han registrado {jugadores_nuevos_en_imagen}.")
            
            carpeta_datasets = os.path.join(carpeta_mercado, "datasets", temporada, jornada)
            os.makedirs(carpeta_datasets, exist_ok=True)
            
            # Guardamos la imagen con el prefijo de los jugadores NUEVOS registrados
            nombre_error = f"{jugadores_nuevos_en_imagen}_{nombre_archivo}"
            ruta_guardado_error = os.path.join(carpeta_datasets, nombre_error)
            cv2.imwrite(ruta_guardado_error, frame)
            
            # Añadimos toda la info al buffer para la revisión manual del final
            imagenes_con_fallos.append({
                'archivo': nombre_archivo,
                'faltan': esperados_actual - jugadores_nuevos_en_imagen,
                'rayos_x': historial_rayos_x,
                'extraidos': jugadores_extraidos_aqui
            })
        else:
            print(f"  🟢 OK: {jugadores_nuevos_en_imagen}/{esperados_actual} jugadores nuevos registrados.")

    # ==========================================
    # --- FASE DE REVISIÓN MANUAL DE FALLOS ---
    # ==========================================
    if imagenes_con_fallos:
        print("\n" + "🚨"*25)
        print(" INICIANDO REVISIÓN MANUAL DE IMÁGENES INCOMPLETAS")
        print("🚨"*25)
        
        for fallo in imagenes_con_fallos:
            print(f"\n🖼️  IMAGEN: {fallo['archivo']}")
            print(f"⚠️ Faltan {fallo['faltan']} jugadores por registrar en esta imagen.\n")
            
            print("--- RAYOS X DE LA IMAGEN ---")
            for rx in fallo['rayos_x']:
                print(rx)
            print("----------------------------")
            
            print(f"✅ Jugadores extraídos correctamente de esta foto: {', '.join(fallo['extraidos']) if fallo['extraidos'] else 'Ninguno'}")
            
            for f in range(fallo['faltan']):
                while True:
                    print(f"\n👉 Introduce los datos del jugador faltante {f+1}/{fallo['faltan']}")
                    print("Formato: Nombre,Precio,Equipo,Posicion,Puntos (Ej: A. Alti,3.0,Villarreal,Defensa,2)")
                    manual = input("> ").strip()
                    
                    partes = [p.strip() for p in manual.split(',')]
                    if len(partes) == 5:
                        nombre, precio, equipo, posicion, puntos = partes
                        clave = f"{nombre}_{equipo}"
                        if clave not in base_datos_mercado:
                            base_datos_mercado[clave] = {
                                'Nombre': nombre,
                                'Precio_Fantastica': precio,
                                'Equipo': equipo,
                                'Posicion': posicion,
                                'Puntos_PFSY': puntos
                            }
                            print(f"✔️ {nombre} añadido a la base de datos.")
                            break
                        else:
                            print("❌ Ese jugador ya está registrado en el sistema. Escribe los datos de otro o revisa.")
                    else:
                        print("❌ Formato incorrecto. Asegúrate de separar los 5 valores con comas exactas.")

    # ==========================================
    # --- CONTROL DE SEGURIDAD (CANDADO FINAL) ---
    # ==========================================
    while len(base_datos_mercado) < meta_jugadores:
        faltan_total = meta_jugadores - len(base_datos_mercado)
        print(f"\n⚠️ EL SISTEMA ESTÁ BLOQUEADO: Faltan {faltan_total} jugadores para llegar a la meta de {meta_jugadores}.")
        print("El proceso no continuará hasta que se introduzcan. Busca en tus capturas quién falta.")
        print("Formato: Nombre,Precio,Equipo,Posicion,Puntos")
        manual = input("> ").strip()
        
        partes = [p.strip() for p in manual.split(',')]
        if len(partes) == 5:
            nombre, precio, equipo, posicion, puntos = partes
            clave = f"{nombre}_{equipo}"
            if clave not in base_datos_mercado:
                base_datos_mercado[clave] = {
                    'Nombre': nombre, 'Precio_Fantastica': precio, 'Equipo': equipo,
                    'Posicion': posicion, 'Puntos_PFSY': puntos
                }
                print(f"✔️ {nombre} añadido. Faltan {meta_jugadores - len(base_datos_mercado)}.")
            else:
                print("❌ Ese jugador ya existe.")
        else:
            print("❌ Formato incorrecto.")

    # Guardado Final
    df = pd.DataFrame(list(base_datos_mercado.values()))
    ruta_csv_base = os.path.join(carpeta_mercado, "datasets", temporada, jornada, "mercado_base.csv")
    os.makedirs(os.path.dirname(ruta_csv_base), exist_ok=True)
    df.to_csv(ruta_csv_base, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ ¡Extracción 100% completada! Total: {len(df)} jugadores ({meta_jugadores} esperados).")
    print(f"💾 Guardado en: {ruta_csv_base}")

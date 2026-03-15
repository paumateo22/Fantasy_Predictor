import pandas as pd
import os
import difflib
import unicodedata

def limpiar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def estimar_puntos_dazn(nota_sofascore):
    if pd.isna(nota_sofascore): return 0
    if nota_sofascore >= 8.0: return 4
    elif nota_sofascore >= 7.5: return 3
    elif nota_sofascore >= 7.0: return 2
    elif nota_sofascore >= 6.5: return 1
    else: return 0

def calcular_puntos_objetivos(row):
    pts = 0
    pos = str(row.get('Posicion', 'M')).upper()
    mins = row.get('Minutos_jugados', 0)
    if mins == 0: return 0

    if mins >= 60: pts += 2
    elif mins > 0: pts += 1

    goles = row.get('Goles', 0)
    if goles > 0:
        if pos in ['G', 'D']: pts += goles * 6
        elif pos == 'M': pts += goles * 5
        else: pts += goles * 4

    pts += row.get('Asistencias_de_gol', 0) * 3
    pts += row.get('Asistencias_sin_gol', 0) * 1

    gc = row.get('Goles_en_contra', 0)
    if mins >= 60 and gc == 0:
        if pos == 'G': pts += 4
        elif pos == 'D': pts += 3
        elif pos == 'M': pts += 2
        elif pos == 'F': pts += 1

    if pos in ['G', 'D']: pts += (gc // 2) * -2
    else: pts += (gc // 2) * -1

    pts += row.get('Penaltis_provocados', 0) * 2
    pts += row.get('Penaltis_cometidos', 0) * -2
    pts += row.get('Penaltis_parados', 0) * 5
    pts += row.get('Penaltis_fallados', 0) * -2
    pts += row.get('Goles_en_propia_puerta', 0) * -2
    pts += row.get('Amarillas', 0) * -1
    pts += row.get('Rojas', 0) * -3

    if pos == 'G': pts += (row.get('Paradas', 0) // 2) * 1
    pts += (row.get('Balones_recuperados', 0) // 5) * 1
    pts += (row.get('Despejes', 0) // 3) * 1
    pts += (row.get('Tiros_a_puerta', 0) // 2) * 1
    pts += (row.get('Regates', 0) // 2) * 1
    pts += (row.get('Balones_al_area', 0) // 2) * 1

    perdidas = row.get('Posesiones_perdidas', 0)
    if pos in ['G', 'D']: pts += (perdidas // 8) * -1
    elif pos == 'M': pts += (perdidas // 10) * -1
    elif pos == 'F': pts += (perdidas // 12) * -1

    return pts

def similitud_strings(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def simular_cruce_con_pesos(df_puntos_og, df_stats_og, w_nombre, w_puntos, w_dazn):
    df_puntos = df_puntos_og.copy()
    df_stats = df_stats_og.copy()
    
    equipos_puntos = df_puntos['Equipo_Jugador'].unique()
    equipos_stats = df_stats['Equipo_Nombre'].unique()
    mapa_equipos = {}
    for eq_p in equipos_puntos:
        coincidencia = difflib.get_close_matches(eq_p, equipos_stats, n=1, cutoff=0.3)
        mapa_equipos[eq_p] = coincidencia[0] if coincidencia else eq_p
            
    df_puntos['Equipo_Comun'] = df_puntos['Equipo_Jugador'].map(mapa_equipos)
    df_puntos['Jugador_SofaScore'] = None
    
    for equipo in mapa_equipos.values():
        df_p_equipo = df_puntos[df_puntos['Equipo_Comun'] == equipo]
        df_s_equipo = df_stats[df_stats['Equipo_Nombre'] == equipo]
        
        posibles_matches = []
        
        for i_p, row_p in df_p_equipo.iterrows():
            nom_p = limpiar_texto(row_p['Jugador'])
            pts_reales = row_p['Stats_Reales']
            pts_dazn = row_p['Relevo']
            
            for i_s, row_s in df_s_equipo.iterrows():
                nom_s = limpiar_texto(row_s['Jugador'])
                pts_teoricos = row_s['Puntos_Teoricos']
                nota_sofascore = row_s['Nota_SofaScore']
                
                similitud = similitud_strings(nom_p, nom_s)
                if nom_p in nom_s or nom_s in nom_p:
                    similitud += 0.3 
                
                delta_puntos = abs(pts_reales - pts_teoricos)
                dazn_estimado = estimar_puntos_dazn(nota_sofascore)
                delta_bonus = abs(pts_dazn - dazn_estimado)
                
                # LA ECUACIÓN PARAMETRIZADA
                coste_match = (delta_puntos * w_puntos) + (delta_bonus * w_dazn) - ((similitud * 20) * w_nombre)
                
                posibles_matches.append({
                    'idx_puntos': i_p, 'idx_stats': i_s, 'nombre_sofa': row_s['Jugador'],
                    'coste_match': coste_match, 'delta_puntos': delta_puntos
                })
        
        posibles_matches.sort(key=lambda x: x['coste_match'])
        asignados_puntos, asignados_stats = set(), set()
        
        for match in posibles_matches:
            if match['idx_puntos'] not in asignados_puntos and match['idx_stats'] not in asignados_stats:
                df_puntos.at[match['idx_puntos'], 'Jugador_SofaScore'] = match['nombre_sofa']
                asignados_puntos.add(match['idx_puntos'])
                asignados_stats.add(match['idx_stats'])

    df_fusion = pd.merge(
        df_puntos.dropna(subset=['Jugador_SofaScore']), df_stats,
        left_on=['Jugador_SofaScore', 'Equipo_Comun'], right_on=['Jugador', 'Equipo_Nombre'],
        how='inner', suffixes=('_puntos', '_stats')
    )
    
    df_fusion['Discrepancia'] = df_fusion['Stats_Reales'] - df_fusion['Puntos_Teoricos']
    df_fusion['Error_Absoluto'] = df_fusion['Discrepancia'].abs()
    
    return df_fusion

def cargar_todos_los_datos(temporadas_dict):
    """Carga todos los CSV en la memoria RAM replicando el sistema de rutas del auditor."""
    print("📥 Cargando las 3 temporadas en memoria RAM. Esto tomará unos segundos...")
    
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    dir_raiz = os.path.dirname(os.path.dirname(directorio_actual)) 
    
    datos_memoria = []

    for temporada_cruda, config in temporadas_dict.items():
        temporada_str = f"T{temporada_cruda.replace('/', '-')}"
        inicio = config[0]
        fin = config[1]
        jornadas_saltar = config[2] if len(config) > 2 else []

        for j in range(inicio, fin + 1):
            if j in jornadas_saltar: continue
            
            jornada_str = f"J{j}"
            ruta_puntos = os.path.join(dir_raiz, "scraping_puntos", "datasets", temporada_str, f"{jornada_str}_puntos.csv")
            ruta_stats = os.path.join(dir_raiz, "scraping_stats", "datasets", temporada_str, f"{jornada_str}_stats.csv")

            if os.path.exists(ruta_puntos) and os.path.exists(ruta_stats):
                df_p = pd.read_csv(ruta_puntos)
                df_s = pd.read_csv(ruta_stats)

                # Pre-calculamos los objetivos globales solo 1 vez
                df_s['Puntos_Teoricos'] = df_s.apply(calcular_puntos_objetivos, axis=1)
                df_p['Stats_Reales'] = df_p['Puntos'] - df_p['Relevo']
                
                datos_memoria.append((temporada_str, jornada_str, df_p, df_s))
                
    print(f"✅ ¡{len(datos_memoria)} jornadas cargadas exitosamente!")
    return datos_memoria

def orquestar_optimizacion(temporadas_dict):
    datos_memoria = cargar_todos_los_datos(temporadas_dict)
    if not datos_memoria: return

    # Guardaremos los resultados en una carpeta junto a los scripts
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    dir_salida = os.path.join(directorio_actual, "optimizacion_pesos")
    os.makedirs(dir_salida, exist_ok=True)
    
    # LAS COMBINACIONES A PROBAR (Nombre, Puntos, DAZN)
    distribuciones = [
        (0.33, 0.33, 0.33), # Reparto igualitario
        (0.60, 0.20, 0.20), # Prioridad alta al Nombre
        (0.20, 0.60, 0.20), # Prioridad alta a la estadística
        (0.40, 0.50, 0.10), # Equilibrio Nombre-Puntos
        (0.50, 0.40, 0.10), # Más peso al nombre
        (0.10, 0.80, 0.10)  # Puramente matemático
    ]
    
    print("\n=======================================================")
    print(" 🔬 INICIANDO BÚSQUEDA EN CUADRÍCULA (GRID SEARCH) 🔬")
    print("=======================================================")
    
    for w_nombre, w_puntos, w_dazn in distribuciones:
        nombre_test = f"W_{w_nombre}_{w_puntos}_{w_dazn}"
        print(f"🔄 Testeando {nombre_test} en las 3 temporadas...")
        
        resultados_iteracion = []
        
        for temp, jor, df_p, df_s in datos_memoria:
            df_res = simular_cruce_con_pesos(df_p, df_s, w_nombre, w_puntos, w_dazn)
            df_res['Temporada'] = temp
            df_res['Jornada'] = jor
            resultados_iteracion.append(df_res)
            
        df_global_test = pd.concat(resultados_iteracion, ignore_index=True)
        df_errores = df_global_test[df_global_test['Error_Absoluto'] > 2].copy()
        
        total = len(df_global_test)
        exactos = len(df_global_test[df_global_test['Error_Absoluto'] == 0])
        errores_graves = len(df_errores)
        
        # Escribimos el reporte (.txt)
        ruta_txt = os.path.join(dir_salida, f"{nombre_test}.txt")
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write(f"=== RESULTADOS DISTRIBUCIÓN: Nombre={w_nombre} | Puntos={w_puntos} | DAZN={w_dazn} ===\n")
            f.write(f"Jugadores cruzados totales: {total}\n")
            f.write(f"Aciertos exactos (0 pts dif): {exactos} ({(exactos/total)*100:.2f}%)\n")
            f.write(f"Errores graves (> 2 pts dif): {errores_graves} ({(errores_graves/total)*100:.2f}%)\n")
        
        # Escribimos el CSV de errores
        if not df_errores.empty:
            columnas = ['Temporada', 'Jornada', 'Equipo_Nombre', 'Jugador_stats', 'Jugador_SofaScore', 'Stats_Reales', 'Puntos_Teoricos', 'Discrepancia']
            ruta_csv = os.path.join(dir_salida, f"{nombre_test}_errores.csv")
            df_errores = df_errores.sort_values(by='Error_Absoluto', ascending=False)
            df_errores[columnas].to_csv(ruta_csv, index=False, encoding='utf-8-sig')

    print(f"\n✅ ¡Torneo finalizado! Revisa la carpeta: {dir_salida}")

if __name__ == "__main__":
    # Formato igual que en calculo_puntos.py
    temporadas_a_auditar = {
        "23-24": [1, 38, []],
        "24-25": [1, 38, []],
        "25-26": [1, 27, []]
    }
    
    orquestar_optimizacion(temporadas_a_auditar)
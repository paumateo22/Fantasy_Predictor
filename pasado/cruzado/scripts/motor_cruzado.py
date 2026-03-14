import pandas as pd
import os
import difflib
import unicodedata

def limpiar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def calcular_puntos_objetivos(row):
    """Calcula los puntos estadísticos teóricos basados en las reglas oficiales."""
    pts = 0
    pos = str(row.get('Posicion', 'M')).upper()
    mins = row.get('Minutos_jugados', 0)

    if mins == 0: return 0

    # Minutos Jugados
    if mins >= 60: pts += 2
    elif mins > 0: pts += 1

    # Goles
    goles = row.get('Goles', 0)
    if goles > 0:
        if pos in ['G', 'D']: pts += goles * 6
        elif pos == 'M': pts += goles * 5
        elif pos == 'F': pts += goles * 4
        else: pts += goles * 4

    # Asistencias
    pts += row.get('Asistencias_de_gol', 0) * 3
    pts += row.get('Asistencias_sin_gol', 0) * 1

    # Portería a cero y Goles en contra
    gc = row.get('Goles_en_contra', 0)
    if mins >= 60 and gc == 0:
        if pos == 'G': pts += 4
        elif pos == 'D': pts += 3
        elif pos == 'M': pts += 2
        elif pos == 'F': pts += 1

    if pos in ['G', 'D']: pts += (gc // 2) * -2
    else: pts += (gc // 2) * -1

    # Penaltis
    pts += row.get('Penaltis_provocados', 0) * 2
    pts += row.get('Penaltis_cometidos', 0) * -2
    pts += row.get('Penaltis_parados', 0) * 5
    pts += row.get('Penaltis_fallados', 0) * -2

    # Sanciones y Errores
    pts += row.get('Goles_en_propia_puerta', 0) * -2
    pts += row.get('Amarillas', 0) * -1
    pts += row.get('Rojas', 0) * -3

    # Bonus Defensa/Portero
    if pos == 'G': pts += (row.get('Paradas', 0) // 2) * 1
    pts += (row.get('Balones_recuperados', 0) // 5) * 1
    pts += (row.get('Despejes', 0) // 3) * 1

    # Bonus Ataque
    pts += (row.get('Tiros_a_puerta', 0) // 2) * 1
    pts += (row.get('Regates', 0) // 2) * 1
    pts += (row.get('Balones_al_area', 0) // 2) * 1

    # Pérdidas de balón
    perdidas = row.get('Posesiones_perdidas', 0)
    if pos in ['G', 'D']: pts += (perdidas // 8) * -1
    elif pos == 'M': pts += (perdidas // 10) * -1
    elif pos == 'F': pts += (perdidas // 12) * -1

    return pts

def similitud_strings(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def cruzar_jornada(temporada_str, jornada_num):
    jornada_str = f"J{jornada_num}"
    
    # --- RUTAS ---
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    dir_pasado = os.path.dirname(os.path.dirname(directorio_actual))
    
    ruta_puntos = os.path.join(dir_pasado, "scraping_puntos", "datasets", temporada_str, f"{jornada_str}_puntos.csv")
    ruta_stats = os.path.join(dir_pasado, "scraping_stats", "datasets", temporada_str, f"{jornada_str}_stats.csv")
    dir_salida = os.path.join(dir_pasado, "cruzado", "datasets", temporada_str)
    
    if not os.path.exists(ruta_puntos) or not os.path.exists(ruta_stats):
        print(f"⚠️ Faltan archivos para {temporada_str} - {jornada_str}")
        return

    print(f"\n🔄 Cruzando datos de {temporada_str} - {jornada_str} (Algoritmo de Fusión Avanzado)...")
    df_puntos = pd.read_csv(ruta_puntos)
    df_stats = pd.read_csv(ruta_stats)
    
    # Pre-calculamos los puntos teóricos en SofaScore para el desempate
    df_stats['Puntos_Teoricos'] = df_stats.apply(calcular_puntos_objetivos, axis=1)
    # Calculamos los puntos reales (sin Relevo)
    df_puntos['Stats_Reales'] = df_puntos['Puntos'] - df_puntos['Relevo']

    # Emparejamiento de Equipos
    equipos_puntos = df_puntos['Equipo_Jugador'].unique()
    equipos_stats = df_stats['Equipo_Nombre'].unique()
    mapa_equipos = {}
    for eq_p in equipos_puntos:
        coincidencia = difflib.get_close_matches(eq_p, equipos_stats, n=1, cutoff=0.3)
        mapa_equipos[eq_p] = coincidencia[0] if coincidencia else eq_p
            
    df_puntos['Equipo_Comun'] = df_puntos['Equipo_Jugador'].map(mapa_equipos)
    df_puntos['Jugador_SofaScore'] = None
    
    # 🚨 LA MAGIA: Emparejamiento por equipo usando Matriz de Compatibilidad
    for equipo in mapa_equipos.values():
        df_p_equipo = df_puntos[df_puntos['Equipo_Comun'] == equipo]
        df_s_equipo = df_stats[df_stats['Equipo_Nombre'] == equipo]
        
        posibles_matches = []
        
        # Comparamos todos contra todos dentro del mismo equipo
        for i_p, row_p in df_p_equipo.iterrows():
            nom_p = limpiar_texto(row_p['Jugador'])
            pts_reales = row_p['Stats_Reales']
            
            for i_s, row_s in df_s_equipo.iterrows():
                nom_s = limpiar_texto(row_s['Jugador'])
                pts_teoricos = row_s['Puntos_Teoricos']
                
                similitud = similitud_strings(nom_p, nom_s)
                # Bonificación si un nombre está contenido en el otro (ej. "n. williams" en "nico williams")
                if nom_p in nom_s or nom_s in nom_p:
                    similitud += 0.3 
                
                delta_puntos = abs(pts_reales - pts_teoricos)
                
                # Solo consideramos candidatos viables (similitud razonable)
                if similitud > 0.3:
                    posibles_matches.append({
                        'idx_puntos': i_p,
                        'idx_stats': i_s,
                        'nombre_sofa': row_s['Jugador'],
                        'similitud': similitud,
                        'delta_puntos': delta_puntos
                    })
        
        # Ordenamos las parejas: Primero las que tienen el nombre más parecido, 
        # y en caso de nombres parecidos, las que tienen menor diferencia de puntos.
        posibles_matches.sort(key=lambda x: (-x['similitud'], x['delta_puntos']))
        
        asignados_puntos = set()
        asignados_stats = set()
        
        for match in posibles_matches:
            if match['idx_puntos'] not in asignados_puntos and match['idx_stats'] not in asignados_stats:
                df_puntos.at[match['idx_puntos'], 'Jugador_SofaScore'] = match['nombre_sofa']
                asignados_puntos.add(match['idx_puntos'])
                asignados_stats.add(match['idx_stats'])

    # Fusión y Limpieza
    df_puntos_con_match = df_puntos.dropna(subset=['Jugador_SofaScore']).copy()
    
    df_final = pd.merge(
        df_puntos_con_match, df_stats,
        left_on=['Jugador_SofaScore', 'Equipo_Comun'], right_on=['Jugador', 'Equipo_Nombre'],
        how='inner', suffixes=('_puntos', '_stats')
    )
    
    columnas_mantener = [
        'Temporada_puntos', 'Jornada_puntos', 'Equipo_Nombre', 'Jugador_stats', 'Posicion_stats',
        'Puntos', 'Relevo', 'Nota_SofaScore', 'Minutos_jugados', 'Goles', 'Asistencias_de_gol',
        'Asistencias_sin_gol', 'Balones_al_area', 'Tiros_a_puerta', 'Regates', 'Balones_recuperados',
        'Despejes', 'Paradas', 'Goles_en_contra', 'Penaltis_provocados', 'Penaltis_cometidos',
        'Penaltis_parados', 'Penaltis_fallados', 'Goles_en_propia_puerta', 'Amarillas', 'Rojas', 'Posesiones_perdidas'
    ]
    
    df_final = df_final[columnas_mantener].rename(columns={
        'Temporada_puntos': 'Temporada', 'Jornada_puntos': 'Jornada', 'Equipo_Nombre': 'Equipo',
        'Jugador_stats': 'Jugador', 'Posicion_stats': 'Posicion'
    })
    
    # Guardado
    os.makedirs(dir_salida, exist_ok=True)
    ruta_salida = os.path.join(dir_salida, f"{jornada_str}_cruzado.csv")
    df_final.to_csv(ruta_salida, index=False, encoding='utf-8-sig')
    print(f"✅ ¡Cruce inteligente con éxito! {len(df_final)} jugadores fusionados.")

def orquestar_cruce(temporadas_dict):
    print("\n=======================================================")
    print(" 🧬 INICIANDO MOTOR DE FUSIÓN INTELIGENTE 🧬")
    print("=======================================================")
    for temporada_cruda, jornadas_lista in temporadas_dict.items():
        temporada_str = f"T{temporada_cruda.replace('/', '-')}"
        for j in jornadas_lista:
            cruzar_jornada(temporada_str, j)
    print("\n🏁 ¡FUSIÓN GLOBAL COMPLETADA! 🏁\n")

if __name__ == "__main__":
    temporadas_a_cruzar = { "25/26": [1] }
    orquestar_cruce(temporadas_a_cruzar)
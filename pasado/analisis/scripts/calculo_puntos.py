import pandas as pd
import os

def calcular_puntos_estadisticos(row):
    pts = 0
    pos = str(row['Posicion']).upper() 
    mins = row['Minutos_jugados']

    if mins == 0:
        return 0

    # --- 1. MINUTOS JUGADOS ---
    if mins >= 60: pts += 2
    elif mins > 0: pts += 1

    # --- 2. GOLES ---
    goles = row['Goles']
    if goles > 0:
        if pos in ['G', 'D']: pts += goles * 6
        elif pos == 'M': pts += goles * 5
        elif pos == 'F': pts += goles * 4
        else: pts += goles * 4

    # --- 3. ASISTENCIAS ---
    pts += row['Asistencias_de_gol'] * 3
    pts += row['Asistencias_sin_gol'] * 1 

    # --- 4. PORTERÍA A CERO (Usando Goles Reales del Equipo) ---
    gc = row.get('Goles_en_contra_Reales', row['Goles_en_contra']) # Respaldo por si falla el dinámico
    if mins >= 60 and gc == 0:
        if pos == 'G': pts += 4
        elif pos == 'D': pts += 3
        elif pos == 'M': pts += 2
        elif pos == 'F': pts += 1

    # --- 5. GOLES RECIBIDOS ---
    if pos in ['G', 'D']:
        pts += (gc // 2) * -2
    else: 
        pts += (gc // 2) * -1

    # --- 6. PARADAS Y DESPEJES ---
    if pos == 'G':
        pts += (row['Paradas'] // 2) * 1
        
    pts += (row['Despejes'] // 3) * 1
    pts += (row['Balones_recuperados'] // 5) * 1

    # --- 7. BONUS ATAQUE ---
    pts += (row['Tiros_a_puerta'] // 2) * 1
    pts += (row['Regates'] // 2) * 1
    pts += (row['Balones_al_area'] // 2) * 1

    # --- 8. PENALTIS, TARJETAS Y ERRORES ---
    pts += row['Penaltis_provocados'] * 2
    pts += row['Penaltis_cometidos'] * -2
    pts += row['Penaltis_parados'] * 5
    pts += row['Penaltis_fallados'] * -2
    pts += row['Goles_en_propia_puerta'] * -2
    pts += row['Amarillas'] * -1
    pts += row['Rojas'] * -3
    
    # --- 9. PÉRDIDAS DE BALÓN ---
    perdidas = row['Posesiones_perdidas']
    if pos in ['G', 'D']: pts += (perdidas // 8) * -1
    elif pos == 'M': pts += (perdidas // 10) * -1
    elif pos == 'F': pts += (perdidas // 12) * -1

    return pts

def procesar_jornada(temporada_str, jornada_num):
    """Carga los datos de una jornada, aplica cálculos y devuelve el DataFrame modificado."""
    jornada_str = f"J{jornada_num}"
    
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    dir_raiz = os.path.dirname(os.path.dirname(directorio_actual)) 
    
    ruta_cruzado = os.path.join(dir_raiz, "cruzado", "datasets", temporada_str, f"{jornada_str}_cruzado.csv")
    ruta_stats = os.path.join(dir_raiz, "scraping_stats", "datasets", temporada_str, f"{jornada_str}_stats.csv")
    
    if not os.path.exists(ruta_cruzado) or not os.path.exists(ruta_stats):
        return None

    df_cruzado = pd.read_csv(ruta_cruzado)
    df_stats = pd.read_csv(ruta_stats)
    
    # Cálculo Dinámico de Goles Recibidos por el Equipo
    goles_recibidos_equipo = {}
    for partido_id, grupo in df_stats.groupby('ID_Partido'):
        goles_locales = grupo[grupo['Equipo_Bando'] == 'Local']['Goles'].sum()
        goles_visitantes = grupo[grupo['Equipo_Bando'] == 'Visitante']['Goles'].sum()
        
        equipos_locales = grupo[grupo['Equipo_Bando'] == 'Local']['Equipo_Nombre'].unique()
        equipos_visitantes = grupo[grupo['Equipo_Bando'] == 'Visitante']['Equipo_Nombre'].unique()
        
        for eq in equipos_locales: goles_recibidos_equipo[eq] = goles_visitantes
        for eq in equipos_visitantes: goles_recibidos_equipo[eq] = goles_locales
            
    df_cruzado['Goles_en_contra_Reales'] = df_cruzado['Equipo'].map(goles_recibidos_equipo)
    
    # Cálculos
    df_cruzado['Stats_Reales'] = df_cruzado['Puntos'] - df_cruzado['Relevo']
    df_cruzado['Stats_Calculados'] = df_cruzado.apply(calcular_puntos_estadisticos, axis=1)
    df_cruzado['Discrepancia'] = df_cruzado['Stats_Reales'] - df_cruzado['Stats_Calculados']
    df_cruzado['Error_Absoluto'] = df_cruzado['Discrepancia'].abs()
    
    # Añadimos etiqueta de jornada para saber de dónde viene el error luego
    df_cruzado['Etiqueta_Jornada'] = f"{temporada_str} - {jornada_str}"
    
    return df_cruzado

def orquestar_auditoria(temporadas_dict):
    print("\n=======================================================")
    print(" 🕵️ INICIANDO AUDITORÍA GLOBAL DE PUNTOS FANTASY 🕵️")
    print("=======================================================")
    
    todos_los_dfs = []
    
    for temporada_cruda, config in temporadas_dict.items():
        temporada_str = f"T{temporada_cruda.replace('/', '-')}"
        inicio = config[0]
        fin = config[1]
        jornadas_saltar = config[2] if len(config) > 2 else []
        
        print(f"🔄 Procesando {temporada_str}...")
        
        for j in range(inicio, fin + 1):
            if j in jornadas_saltar: continue
            
            df_jornada = procesar_jornada(temporada_str, j)
            if df_jornada is not None:
                todos_los_dfs.append(df_jornada)
                
    if not todos_los_dfs:
        print("❌ No se encontró ningún archivo cruzado para auditar.")
        return
        
    # Unificamos todo en un único DataFrame masivo
    df_global = pd.concat(todos_los_dfs, ignore_index=True)
    total_jugadores = len(df_global)
    
    print("\n" + "="*60)
    print(f" 📊 RESULTADOS DEL ANÁLISIS GLOBAL")
    print("="*60)
    print(f" 🧑‍🤝‍🧑 Total de registros analizados: {total_jugadores}")
    
    print("\n 📈 DISTRIBUCIÓN DEL MARGEN DE ERROR (SOFASCORE vs OPTA):")
    conteo_errores = df_global['Error_Absoluto'].value_counts().sort_index()
    
    acumulado = 0
    for error_val, count in conteo_errores.items():
        pct = (count / total_jugadores) * 100
        acumulado += pct
        
        if error_val == 0:
            print(f"    ✅ Exactos (0 pts):   {count} jug. ({pct:.1f}%)")
        else:
            print(f"    ⚠️ Desfase de {int(error_val)} pts:  {count} jug. ({pct:.1f}%) -> Precisión Acumulada: {acumulado:.1f}%")
            
    fallos = total_jugadores - len(df_global[df_global['Error_Absoluto'] == 0])
    
    if fallos > 0:
        print("\n🔍 TOP 15 DISCREPANCIAS MÁS GRANDES A NIVEL HISTÓRICO:")
        print("-" * 60)
        df_errores = df_global[df_global['Error_Absoluto'] > 0].sort_values(by='Error_Absoluto', ascending=False).head(15)
        # Mostramos la etiqueta para saber en qué partido exacto patinó
        columnas_mostrar = ['Etiqueta_Jornada', 'Jugador', 'Posicion', 'Stats_Reales', 'Stats_Calculados', 'Discrepancia']
        print(df_errores[columnas_mostrar].to_string(index=False))

if __name__ == "__main__":
    # Formato: "Temporada": [Jornada_Inicio, Jornada_Fin, [Jornadas_a_saltar]]
    temporadas_a_auditar = {
        "23-24": [1, 38, []],
        "24-25": [1, 38, []],
        "25-26": [1, 27, []]
    }
    
    orquestar_auditoria(temporadas_a_auditar)
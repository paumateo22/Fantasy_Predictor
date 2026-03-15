import pandas as pd
import os
import difflib
import unicodedata
import re  # 🚨 NUEVO: Importamos regex para limpiar números

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_CRUZADO = os.path.dirname(DIRECTORIO_ACTUAL)
DIRECTORIO_DATASETS = os.path.join(DIRECTORIO_CRUZADO, "datasets")

os.makedirs(DIRECTORIO_DATASETS, exist_ok=True)
RUTA_DICCIONARIO = os.path.join(DIRECTORIO_DATASETS, "diccionario_alias.csv")

# --- SISTEMA DE MEMORIA MAESTRA (POR EQUIPOS) ---
def cargar_diccionario():
    diccionario_base = {}
    if os.path.exists(RUTA_DICCIONARIO):
        df_alias = pd.read_csv(RUTA_DICCIONARIO)
        for _, fila in df_alias.iterrows():
            if 'Equipo' in df_alias.columns and not pd.isna(fila['Equipo']):
                clave = f"{str(fila['Equipo']).strip()}_{str(fila['Fantasy']).strip()}"
            else:
                clave = str(fila['Fantasy']).strip()
            diccionario_base[clave] = str(fila['SofaScore']).strip()
    return diccionario_base

def guardar_alias(equipo, nom_fantasy, nom_sofascore):
    clave = f"{equipo}_{nom_fantasy}"
    if clave in ALIAS_JUGADORES and ALIAS_JUGADORES[clave] == nom_sofascore:
        return
        
    nuevo_alias = pd.DataFrame([{'Equipo': equipo, 'Fantasy': nom_fantasy, 'SofaScore': nom_sofascore}])
    if not os.path.exists(RUTA_DICCIONARIO):
        nuevo_alias.to_csv(RUTA_DICCIONARIO, index=False)
    else:
        nuevo_alias.to_csv(RUTA_DICCIONARIO, mode='a', header=False, index=False)
    
    ALIAS_JUGADORES[clave] = nom_sofascore

ALIAS_JUGADORES = cargar_diccionario()

ALIAS_GLOBALES = {
    "samu aghehowa": "samu omorodion",
    "nico williams": "williams jr",
    "inaki williams": "williams",
    "luis rioja": "rioja"
}

def limpiar_texto_crudo(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    
    # 🚨 NUEVO: Fulminamos los minutos jugados del final del nombre (ej: "lukebakio 14'" -> "lukebakio")
    texto = re.sub(r"\s*\d+(\+\d+)?'?$", "", texto)
    
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_texto(texto, equipo=""):
    texto_limpio = limpiar_texto_crudo(texto)
    clave_equipo = f"{equipo}_{texto_limpio}"
    
    if clave_equipo in ALIAS_JUGADORES:
        return ALIAS_JUGADORES[clave_equipo]
        
    for alias, nombre_real in ALIAS_GLOBALES.items():
        if alias == texto_limpio or alias in texto_limpio:
            return nombre_real
            
    return texto_limpio

def nombres_compatibles(nom_fantasy, nom_sofa):
    n1 = nom_fantasy.replace('.', '').strip()
    n2 = nom_sofa.replace('.', '').strip()

    if n1 == n2 or n1 in n2 or n2 in n1:
        return True

    if difflib.SequenceMatcher(None, n1, n2).ratio() > 0.65:
        return True

    partes1 = n1.split()
    partes2 = n2.split()

    if len(partes1) >= 2 and len(partes2) >= 2:
        if partes1[-1] == partes2[-1] and partes1[0][0] == partes2[0][0]:
            return True

    return False

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
        elif pos == 'F': pts += goles * 4
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

def cruzar_jornada(temporada_str, jornada_num):
    jornada_str = f"J{jornada_num}"
    dir_pasado = os.path.dirname(DIRECTORIO_CRUZADO)
    
    ruta_puntos = os.path.join(dir_pasado, "scraping_puntos", "datasets", temporada_str, f"{jornada_str}_puntos.csv")
    ruta_stats = os.path.join(dir_pasado, "scraping_stats", "datasets", temporada_str, f"{jornada_str}_stats.csv")
    dir_salida = os.path.join(DIRECTORIO_DATASETS, temporada_str)
    
    if not os.path.exists(ruta_puntos) or not os.path.exists(ruta_stats):
        return

    print(f"\n🔄 Cruzando datos de {temporada_str} - {jornada_str}...")
    df_puntos = pd.read_csv(ruta_puntos)
    df_stats = pd.read_csv(ruta_stats)
    
    df_stats['Puntos_Teoricos'] = df_stats.apply(calcular_puntos_objetivos, axis=1)
    df_puntos['Stats_Reales'] = df_puntos['Puntos'] - df_puntos['Relevo']

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
        
        # --- FASE 2: EMPAREJAMIENTO AUTOMÁTICO (Todos contra Todos) ---
        for i_p, row_p in df_p_equipo.iterrows():
            nom_p_original = str(row_p['Jugador'])
            nom_p_crudo = limpiar_texto_crudo(nom_p_original)
            nom_p = limpiar_texto(nom_p_original, equipo) 
            viene_del_diccionario = (nom_p != nom_p_crudo)
            
            pts_reales = row_p['Stats_Reales']
            pts_dazn = row_p['Relevo']
            
            pos_p = str(row_p.get('Posicion', 'M')).strip()
            mapa_pos = {'Portero': 'G', 'Defensa': 'D', 'Mediocampista': 'M', 'Delantero': 'F'}
            pos_p_traducida = mapa_pos.get(pos_p, 'M')
            
            for i_s, row_s in df_s_equipo.iterrows():
                nom_s_original = str(row_s['Jugador'])
                nom_s = limpiar_texto_crudo(nom_s_original)
                pts_teoricos = row_s['Puntos_Teoricos']
                nota_sofascore = row_s['Nota_SofaScore']
                pos_s = str(row_s.get('Posicion', 'M')).strip()
                
                if viene_del_diccionario and nom_p != nom_s:
                    continue
                
                son_compatibles = nombres_compatibles(nom_p, nom_s)
                similitud = difflib.SequenceMatcher(None, nom_p, nom_s).ratio()
                
                if nom_p in nom_s or nom_s in nom_p:
                    similitud += 0.3
                
                if not viene_del_diccionario and not son_compatibles and similitud < 0.75:
                    continue 
                
                if pos_p_traducida != pos_s:
                    similitud -= 0.2  
                
                delta_puntos = abs(pts_reales - pts_teoricos)
                delta_bonus = abs(pts_dazn - estimar_puntos_dazn(nota_sofascore))
                
                coste_match = (delta_puntos * 2) + (delta_bonus * 1) - (similitud * 15)
                
                posibles_matches.append({
                    'idx_puntos': i_p, 'idx_stats': i_s, 'nombre_sofa': nom_s_original,
                    'nombre_p_crudo': nom_p_crudo,
                    'similitud': similitud, 'delta_puntos': delta_puntos, 'coste_match': coste_match
                })
        
        posibles_matches.sort(key=lambda x: x['coste_match'])
        
        asignados_puntos = set()
        asignados_stats = set()
        
        for match in posibles_matches:
            if match['idx_puntos'] not in asignados_puntos and match['idx_stats'] not in asignados_stats:
                df_puntos.at[match['idx_puntos'], 'Jugador_SofaScore'] = match['nombre_sofa']
                asignados_puntos.add(match['idx_puntos'])
                asignados_stats.add(match['idx_stats'])
                
                clave_fantasy = match['nombre_p_crudo']
                clave_sofa = limpiar_texto_crudo(match['nombre_sofa'])
                guardar_alias(equipo, clave_fantasy, clave_sofa)

        # --- FASE 3: INTERACTIVA (SIN FILTRO DE BANQUILLO) ---
        pendientes = []
        for i_p in df_p_equipo.index:
            if i_p in asignados_puntos: continue
            
            pts_p = df_p_equipo.at[i_p, 'Stats_Reales']
            nom_p_limpio = limpiar_texto(df_p_equipo.at[i_p, 'Jugador'], equipo)
            
            if pts_p != 0:
                pendientes.append(i_p)
            else: # pts_p == 0
                for i_s in df_s_equipo.index:
                    if i_s in asignados_stats: continue
                    nom_s_limpio = limpiar_texto_crudo(df_s_equipo.at[i_s, 'Jugador'])
                    if nombres_compatibles(nom_p_limpio, nom_s_limpio):
                        pendientes.append(i_p)
                        break
        
        for i_p in pendientes:
            row_p = df_p_equipo.loc[i_p]
            nom_p_original = row_p['Jugador']
            nom_p_limpio = limpiar_texto_crudo(nom_p_original)
            pts_p = row_p['Stats_Reales']
            
            candidatos_libres = df_s_equipo.loc[~df_s_equipo.index.isin(asignados_stats)].copy()
            candidatos_libres['Similitud'] = candidatos_libres['Jugador'].apply(lambda x: difflib.SequenceMatcher(None, nom_p_limpio, limpiar_texto_crudo(x)).ratio())
            candidatos_mostrar = candidatos_libres.sort_values(by='Similitud', ascending=False)
            
            print(f"\n" + "="*60)
            print(f"❓ FANTASY REGISTRÓ A: {nom_p_original} ({equipo}) | {pts_p} pts Fantasy")
            print("="*60)
            print("0. ✍️  Descartar jugador (IGNORAR)")
            
            lista_opciones = []
            for idx, (_, row_s) in enumerate(candidatos_mostrar.iterrows(), 1):
                lista_opciones.append((row_s.name, row_s['Jugador']))
                minutos = row_s['Minutos_jugados']
                print(f"{idx}. {row_s['Jugador']} | {row_s['Posicion']} | {row_s['Puntos_Teoricos']} pts calc. | ⏱️ {minutos} mins")
            
            while True:
                opcion = input(f"\nElige una opción (0-{len(lista_opciones)}): ").strip()
                if opcion.isdigit() and 0 <= int(opcion) <= len(lista_opciones):
                    opcion = int(opcion)
                    break
                print("❌ Opción no válida.")
                
            if opcion == 0:
                print("🚫 Jugador ignorado.")
            else:
                idx_elegido, nombre_elegido = lista_opciones[opcion - 1]
                guardar_alias(equipo, nom_p_limpio, limpiar_texto_crudo(nombre_elegido))
                df_puntos.at[i_p, 'Jugador_SofaScore'] = nombre_elegido
                asignados_stats.add(idx_elegido)
                print(f"✅ Relación aprendida para siempre ({equipo}): {nom_p_original} -> {nombre_elegido}")

    # --- FUSIÓN Y GUARDADO ---
    df_puntos_con_match = df_puntos.dropna(subset=['Jugador_SofaScore']).copy()
    
    df_final = pd.merge(
        df_puntos_con_match, df_stats,
        left_on=['Jugador_SofaScore', 'Equipo_Comun'], right_on=['Jugador', 'Equipo_Nombre'],
        how='inner', suffixes=('_puntos', '_stats')
    )
    
    columnas_mantener = [
        'Temporada_puntos', 'Jornada_puntos', 'Equipo_Nombre', 
        'Jugador_puntos', 'Jugador_stats', 
        'Posicion_stats', 'Puntos', 'Relevo', 'Nota_SofaScore', 'Minutos_jugados', 'Goles', 'Asistencias_de_gol',
        'Asistencias_sin_gol', 'Balones_al_area', 'Tiros_a_puerta', 'Regates', 'Balones_recuperados',
        'Despejes', 'Paradas', 'Goles_en_contra', 'Penaltis_provocados', 'Penaltis_cometidos',
        'Penaltis_parados', 'Penaltis_fallados', 'Goles_en_propia_puerta', 'Amarillas', 'Rojas', 'Posesiones_perdidas'
    ]
    
    df_final = df_final[columnas_mantener].rename(columns={
        'Temporada_puntos': 'Temporada', 'Jornada_puntos': 'Jornada', 'Equipo_Nombre': 'Equipo',
        'Jugador_puntos': 'Jugador_Fantasy', 'Jugador_stats': 'Jugador_SofaScore', 
        'Posicion_stats': 'Posicion'
    })
    
    os.makedirs(dir_salida, exist_ok=True)
    ruta_salida = os.path.join(dir_salida, f"{jornada_str}_cruzado.csv")
    df_final.to_csv(ruta_salida, index=False, encoding='utf-8-sig')

def orquestar_cruce(temporadas_dict):
    print("\n=======================================================")
    print(" 🧬 INICIANDO MOTOR DE FUSIÓN HÍBRIDO (TABLA MAESTRA) 🧬")
    print("=======================================================")
    
    for temporada_cruda, config in temporadas_dict.items():
        temporada_str = f"T{temporada_cruda.replace('/', '-')}"
        inicio, fin = config[0], config[1]
        jornadas_saltar = config[2] if len(config) > 2 else [] 
        
        print(f"\n--- 📅 Temporada: {temporada_str} ---")
        
        for j in range(inicio, fin + 1):
            if j not in jornadas_saltar:
                cruzar_jornada(temporada_str, j)
            
    print("\n🏁 ¡FUSIÓN GLOBAL COMPLETADA! 🏁")
    print(f"Diccionario maestro actualizado con éxito en: {RUTA_DICCIONARIO}")
    print(f"Total de alias por equipo registrados: {len(ALIAS_JUGADORES)}")

if __name__ == "__main__":
    temporadas_a_cruzar = {
        "23-24": [1, 38, []],
        "24-25": [1, 38, []],
        "25-26": [1, 27, []]
    }
    
    orquestar_cruce(temporadas_a_cruzar)
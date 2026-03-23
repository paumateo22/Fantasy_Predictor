import pandas as pd
import os
import sys

# 1. Establecer rutas dinámicas de los directorios principales
dir_actual = os.path.dirname(os.path.abspath(__file__)) 
dir_cruzado = os.path.dirname(dir_actual)               
dir_pasado = os.path.dirname(dir_cruzado)               
dir_raiz = os.path.dirname(dir_pasado)                  

# 2. Añadir la raíz al path para poder importar nuestra función auxiliar
if dir_raiz not in sys.path:
    sys.path.append(dir_raiz)

from auxiliar.comprobar_archivo import obtener_nombre_archivo_unico

def cruzar_pasado_presente(temporada, jornada):
    jornada_str = f"J{jornada}"
    
    ruta_pasado = os.path.join(dir_cruzado, "datasets", temporada, f"{jornada_str}_cruzado.csv")
    ruta_jaj = os.path.join(dir_raiz, "datasets", "JaJ", temporada, jornada_str, "jugadores+mercado.csv")
    dir_salida = os.path.join(dir_raiz, "datasets", "Pasado", temporada)
    
    if not os.path.exists(ruta_pasado):
        print(f"⚠️ Saltando {temporada} - {jornada_str}: No se encuentra el CSV del pasado -> {ruta_pasado}")
        return
        
    if not os.path.exists(ruta_jaj):
        print(f"⚠️ Saltando {temporada} - {jornada_str}: No se encuentra el CSV del presente (JaJ) -> {ruta_jaj}")
        return

    print(f"\n🔄 Uniendo Pasado y Presente: {temporada} - {jornada_str}...")
    
    # 3. Cargar DataFrames
    df_pasado = pd.read_csv(ruta_pasado)
    df_jaj = pd.read_csv(ruta_jaj)
    
    if 'Jugador_Fantasy' in df_pasado.columns and 'Jugador_FutFantasy' not in df_pasado.columns:
        df_pasado = df_pasado.rename(columns={'Jugador_Fantasy': 'Jugador_FutFantasy'})
    if 'Jugador_Fantasy' in df_jaj.columns and 'Jugador_FutFantasy' not in df_jaj.columns:
        df_jaj = df_jaj.rename(columns={'Jugador_Fantasy': 'Jugador_FutFantasy'})

    mapa_posiciones = {'G': 'Portero', 'D': 'Defensa', 'M': 'Mediocampista', 'F': 'Delantero'}
    if 'Posicion' in df_pasado.columns:
        df_pasado['Posicion'] = df_pasado['Posicion'].map(mapa_posiciones).fillna(df_pasado['Posicion'])
        
    # 4. Cruzamos en modo estricto (INNER)
    df_final = pd.merge(df_pasado, df_jaj, on='Jugador_FutFantasy', how='inner', suffixes=('_pas', '_jaj'))
    
    # 5. Limpiar duplicados básicos de las llaves
    for col in ['Posicion', 'Equipo', 'Jornada', 'Temporada']:
        if f'{col}_jaj' in df_final.columns and f'{col}_pas' in df_final.columns:
            df_final[col] = df_final[f'{col}_jaj'].fillna(df_final[f'{col}_pas'])
            df_final = df_final.drop(columns=[f'{col}_jaj', f'{col}_pas'])

    # 🚨 6. RENOMBRAMOS COLUMNAS PARA DISTINGUIR "PARTIDO" DE "TEMPORADA"
    renombres = {
        'Goles_pas': 'Goles_Partido',
        'Goles_jaj': 'Goles_Temporada',
        'Asistencias_de_gol': 'Asistencias_Partido',
        'Asistencias': 'Asistencias_Temporada',
        'Amarillas': 'Amarillas_Partido',
        'Tarjetas_Amarillas': 'Amarillas_Temporada',
        'Rojas': 'Rojas_Partido',
        'Tarjetas_Rojas': 'Rojas_Temporada',
        'Penaltis_parados': 'Penaltis_Parados_Partido',
        'Penaltis_Parados': 'Penaltis_Parados_Temporada',
        'Penaltis_parados_pas': 'Penaltis_Parados_Partido',
        'Penaltis_Parados_jaj': 'Penaltis_Parados_Temporada'
    }
    
    renombres_reales = {k: v for k, v in renombres.items() if k in df_final.columns}
    df_final = df_final.rename(columns=renombres_reales)

    # 🚨 7. ORDEN LÓGICO Y ESTRUCTURADO EN 5 BLOQUES PARA IA
    orden_deseado = [
        # BLOQUE 1: Identificación y Contexto
        'Temporada', 'Jornada', 'ID_Partido', 'Equipo', 'Equipo_Rival', 'Es_Local', 
        'Jugador_FutFantasy', 'Jugador_Fantasy', 'Jugador_SofaScore', 
        'Posicion', 'Edad', 'Nacionalidad',
        
        # BLOQUE 2: Mercado y Disponibilidad (Pre-partido)
        'Precio_Fantastica', 'Probabilidad_Jugar', 'Estado_Medico', 'Estado_Forma',
        
        # BLOQUE 3: Histórico Acumulado (Pre-partido)
        'Partidos_Jugados', 'Puntos_Totales', 'Media_Puntos', 
        'Puntos_Ultima_Jornada', 'Puntos_Jornada_Ant_2', 'Puntos_Jornada_Ant_3',
        'Goles_Temporada', 'Asistencias_Temporada', 'Penaltis_Parados_Temporada', 
        'Amarillas_Temporada', 'Rojas_Temporada',
        
        # BLOQUE 4: Rendimiento Real (El partido)
        'Minutos_jugados', 'Nota_SofaScore', 'Goles_Partido', 'Asistencias_Partido', 
        'Asistencias_sin_gol', 'Tiros_a_puerta', 'Regates', 'Balones_al_area', 
        'Balones_recuperados', 'Posesiones_perdidas', 'Despejes', 'Paradas', 
        'Goles_en_contra', 'Penaltis_provocados', 'Penaltis_cometidos', 
        'Penaltis_Parados_Partido', 'Penaltis_fallados', 'Goles_en_propia_puerta', 
        'Amarillas_Partido', 'Rojas_Partido',
        
        # BLOQUE 5: Targets (Variables a predecir)
        'Puntos', 'Relevo'
    ]
    
    # Aplicar el orden (manteniendo al final las que no estuvieran previstas por si acaso)
    columnas_presentes = [c for c in orden_deseado if c in df_final.columns]
    columnas_sobrantes = [c for c in df_final.columns if c not in columnas_presentes]
    df_final = df_final[columnas_presentes + columnas_sobrantes]

    # 8. Guardar el archivo fusionado
    os.makedirs(dir_salida, exist_ok=True)
    ruta_base_salida = os.path.join(dir_salida, f"{jornada_str}_cruzado_total.csv")
    ruta_salida_final = obtener_nombre_archivo_unico(ruta_base_salida)
    
    df_final.to_csv(ruta_salida_final, index=False, encoding='utf-8-sig')
    
    print(f"✅ Completado. Jugadores totales: {len(df_final)} | Guardado en: {ruta_salida_final}")


def orquestar_cruce(temporadas_dict):
    print("\n===========================================================")
    print(" 🧬 INICIANDO CRUCE GLOBAL: PASADO + PRESENTE (MERCADO) 🧬")
    print("===========================================================")
    
    for temporada, config in temporadas_dict.items():
        inicio, fin = config[0], config[1]
        jornadas_saltar = config[2] if len(config) > 2 else []
        
        for j in range(inicio, fin + 1):
            if j not in jornadas_saltar:
                cruzar_pasado_presente(temporada, j)
                
    print("\n🏁 ¡PROCESO DE FUSIÓN FINALIZADO! 🏁")


if __name__ == "__main__":
    temporadas_a_procesar = {
        "T25-26": [29, 29, []]
    }
    
    orquestar_cruce(temporadas_a_procesar)
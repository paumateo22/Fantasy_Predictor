import pandas as pd
import os

def calcular_puntos_estadisticos(row):
    """
    Aplica la fórmula OFICIAL del Fantasy basada en las reglas proporcionadas.
    """
    pts = 0
    pos = str(row['Posicion']).upper() # G (Portero), D (Defensa), M (Medio), F (Delantero)
    mins = row['Minutos_jugados']

    # Si no jugó, 0 puntos directos
    if mins == 0:
        return 0

    # --- 1. MINUTOS JUGADOS ---
    if mins >= 60:
        pts += 2
    elif mins > 0:
        pts += 1

    # --- 2. GOLES (Depende de la posición) ---
    goles = row['Goles']
    if goles > 0:
        if pos in ['G', 'D']: pts += goles * 6
        elif pos == 'M': pts += goles * 5
        elif pos == 'F': pts += goles * 4
        else: pts += goles * 4

    # --- 3. ASISTENCIAS ---
    pts += row['Asistencias_de_gol'] * 3
    pts += row['Asistencias_sin_gol'] * 1 

    # --- 4. PORTERÍA A CERO ---
    # Solo aplica si ha jugado > 60 min
    gc = row['Goles_en_contra']
    if mins >= 60 and gc == 0:
        if pos == 'G': pts += 4
        elif pos == 'D': pts += 3
        elif pos == 'M': pts += 2
        elif pos == 'F': pts += 1

    # --- 5. GOLES RECIBIDOS ---
    if pos in ['G', 'D']:
        pts += (gc // 2) * -2
    else: # Medio / Delantero
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

def auditar_jornada(temporada_str, jornada_num):
    jornada_str = f"J{jornada_num}"
    
    # --- RUTAS ---
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    dir_raiz = os.path.dirname(os.path.dirname(directorio_actual)) 
    
    # Apuntamos al archivo cruzado
    ruta_cruzado = os.path.join(dir_raiz, "cruzado", "datasets", temporada_str, f"{jornada_str}_cruzado.csv")
    
    if not os.path.exists(ruta_cruzado):
        print(f"❌ No se encuentra el archivo cruzado en: {ruta_cruzado}")
        return

    df = pd.read_csv(ruta_cruzado)
    
    # --- CÁLCULOS ---
    # 1. Obtenemos los puntos estadísticos que dio la app en la vida real
    df['Stats_Reales'] = df['Puntos'] - df['Relevo']
    
    # 2. Aplicamos nuestra fórmula matemática basada en los datos de SofaScore
    df['Stats_Calculados'] = df.apply(calcular_puntos_estadisticos, axis=1)
    
    # 3. Calculamos la discrepancia (Lo ideal es que sea 0)
    df['Discrepancia'] = df['Stats_Reales'] - df['Stats_Calculados']
    
    # --- ANÁLISIS DE RESULTADOS ---
    total_jugadores = len(df)
    cuadrados = len(df[df['Discrepancia'] == 0])
    fallos = total_jugadores - cuadrados
    
    print("\n" + "="*60)
    print(f" 📊 AUDITORÍA DE PUNTOS: {temporada_str} - {jornada_str}")
    print("="*60)
    print(f" 🧑‍🤝‍🧑 Jugadores analizados: {total_jugadores}")
    print(f" ✅ Fórmulas exactas (Discrepancia 0): {cuadrados} ({(cuadrados/total_jugadores)*100:.1f}%)")
    print(f" ❌ Fórmulas con desfase: {fallos}")
    
    if fallos > 0:
        print("\n🔍 TOP 10 DISCREPANCIAS MÁS GRANDES PARA AJUSTAR LA FÓRMULA:")
        print("-" * 60)
        # Filtramos los que fallan, ordenamos por la magnitud del error
        df_errores = df[df['Discrepancia'] != 0].copy()
        df_errores['Error_Absoluto'] = df_errores['Discrepancia'].abs()
        df_errores = df_errores.sort_values(by='Error_Absoluto', ascending=False).head(10)
        
        columnas_mostrar = ['Jugador', 'Posicion', 'Stats_Reales', 'Stats_Calculados', 'Discrepancia']
        print(df_errores[columnas_mostrar].to_string(index=False))
        
        print("-" * 60)
        print("💡 CONSEJO: Revisa las estadísticas puras de estos jugadores en el CSV para ver qué regla del")
        print("   código te falta ajustar (ej: el divisor de despejes, tiros a puerta, etc).")

if __name__ == "__main__":
    # Prueba a auditar la jornada 1
    auditar_jornada("T25-26", 1)
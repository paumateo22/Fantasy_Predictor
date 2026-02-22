import pandas as pd
import unicodedata
import difflib
import os
import json

# --- FUNCIONES AUXILIARES ---
def normalizar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto

def limpiar_puntos(valor):
    try:
        return int(float(valor))
    except:
        return 0

def cargar_diccionario(ruta):
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Aviso: El diccionario JSON estaba vacío o corrupto. Se inicializará uno nuevo.")
            return {}
    return {}

def guardar_diccionario(dicc, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(dicc, f, indent=4, ensure_ascii=False)

# --- FUNCIÓN PRINCIPAL ---
def cruzar_datasets_inteligente(ruta_mercado, ruta_jugadores, ruta_diccionario, ruta_salida):
    print("======================================================")
    print("🧠 INICIANDO CRUCE (MEMORIA + EXACTO + IA + MANUAL + GLOBAL)")
    print("======================================================\n")

    try:
        df_mercado = pd.read_csv(ruta_mercado)
        df_jugadores = pd.read_csv(ruta_jugadores)
    except Exception as e:
        print(f"❌ Error al cargar los CSVs: {e}")
        return

    diccionario_alias = cargar_diccionario(ruta_diccionario)
    nuevas_relaciones = []
    
    # Lista donde guardaremos a los jugadores ya fusionados para el CSV final
    jugadores_fusionados = []

    df_mercado['Key_Nombre'] = df_mercado['Nombre'].apply(normalizar_texto)
    df_jugadores['Key_Nombre'] = df_jugadores['Nombre'].apply(normalizar_texto)

    equipos = sorted(df_jugadores['Equipo'].dropna().unique())
    
    # 🚨 BOLSA GLOBAL: Todos los jugadores del mercado disponibles
    mercado_disponible = df_mercado.to_dict('records')
    
    total_bd = len(df_jugadores)
    match_memoria = 0
    match_exactos = 0
    match_inteligentes = 0
    match_manuales = 0
    match_globales = 0

    for equipo in equipos:
        print(f"🛡️ --- {equipo.upper()} ---")
        bd_eq = df_jugadores[df_jugadores['Equipo'] == equipo].to_dict('records')
        
        if equipo not in diccionario_alias:
            diccionario_alias[equipo] = {}

        for j_bd in bd_eq:
            j_bd['matched'] = False
            nombre_original_bd = str(j_bd['Nombre'])
            pts_bd = limpiar_puntos(j_bd.get('Puntos_Totales', 0))

            # --- FASE 0: MEMORIA (Solo busca en su equipo del mercado) ---
            if nombre_original_bd in diccionario_alias[equipo]:
                alias_guardados = diccionario_alias[equipo][nombre_original_bd]
                if isinstance(alias_guardados, str):
                    alias_guardados = [alias_guardados]
                    diccionario_alias[equipo][nombre_original_bd] = alias_guardados

                match_dicc = next((m for m in mercado_disponible if m['Equipo'] == equipo and str(m['Nombre']) in alias_guardados), None)
                if match_dicc:
                    print(f"  [MEMORIA]     📖 {j_bd['Nombre']} emparejado con '{match_dicc['Nombre']}'")
                    j_bd['Precio_Fantastica'] = match_dicc.get('Precio_Fantastica')
                    j_bd['Puntos_PFSY'] = match_dicc.get('Puntos_PFSY')
                    mercado_disponible.remove(match_dicc)
                    j_bd['matched'] = True
                    match_memoria += 1

            # --- FASE 1: EXACTO (Solo busca en su equipo del mercado) ---
            if not j_bd['matched']:
                match_exacto = next((m for m in mercado_disponible if m['Equipo'] == equipo and m['Key_Nombre'] == j_bd['Key_Nombre']), None)
                if match_exacto:
                    print(f"  [EXACTO]      🎯 {j_bd['Nombre']}")
                    j_bd['Precio_Fantastica'] = match_exacto.get('Precio_Fantastica')
                    j_bd['Puntos_PFSY'] = match_exacto.get('Puntos_PFSY')
                    mercado_disponible.remove(match_exacto)
                    j_bd['matched'] = True
                    match_exactos += 1

            # --- FASE 2: IA (Mismos puntos dentro del equipo) ---
            if not j_bd['matched']:
                cand_equipo = [m for m in mercado_disponible if m['Equipo'] == equipo and limpiar_puntos(m.get('Puntos_PFSY', 0)) == pts_bd]
                if cand_equipo:
                    nombres_cand = [m['Key_Nombre'] for m in cand_equipo]
                    coincidencias = difflib.get_close_matches(j_bd['Key_Nombre'], nombres_cand, n=1, cutoff=0.4)
                    
                    if coincidencias:
                        match_fuzzy = next(m for m in cand_equipo if m['Key_Nombre'] == coincidencias[0])
                        print(f"  [APRENDIZAJE] 🤖 ¿Es {nombre_original_bd} -> '{match_fuzzy['Nombre']}'? (Pts: {pts_bd})")
                        if input("     ¿Guardar esta relación? (s/n): ").strip().lower() == 's':
                            if nombre_original_bd not in diccionario_alias[equipo]: diccionario_alias[equipo][nombre_original_bd] = []
                            if match_fuzzy['Nombre'] not in diccionario_alias[equipo][nombre_original_bd]:
                                diccionario_alias[equipo][nombre_original_bd].append(match_fuzzy['Nombre'])
                                nuevas_relaciones.append((equipo, nombre_original_bd, match_fuzzy['Nombre']))
                            
                            j_bd['Precio_Fantastica'] = match_fuzzy.get('Precio_Fantastica')
                            j_bd['Puntos_PFSY'] = match_fuzzy.get('Puntos_PFSY')
                            mercado_disponible.remove(match_fuzzy)
                            j_bd['matched'] = True
                            match_inteligentes += 1
                            print("     ✅ Guardado.")
                        else:
                            print("     ❌ Descartado.")

            # --- FASE 3: MANUAL EN EQUIPO ---
            if not j_bd['matched']:
                cand_equipo_todos = [m for m in mercado_disponible if m['Equipo'] == equipo]
                if cand_equipo_todos:
                    print(f"  [MANUAL]      🕵️ No encuentro a: {nombre_original_bd} (Pts: {pts_bd})")
                    print("     0. ⏭️  Ninguno (Pasar a búsqueda global)")
                    for idx, m in enumerate(cand_equipo_todos, 1):
                        print(f"     {idx}. {m['Nombre']} (Pts: {limpiar_puntos(m.get('Puntos_PFSY', 0))})")
                    
                    try: opcion = int(input("     Opcion: "))
                    except ValueError: opcion = 0
                    
                    if 1 <= opcion <= len(cand_equipo_todos):
                        match_manual = cand_equipo_todos[opcion - 1]
                        if nombre_original_bd not in diccionario_alias[equipo]: diccionario_alias[equipo][nombre_original_bd] = []
                        if match_manual['Nombre'] not in diccionario_alias[equipo][nombre_original_bd]:
                            diccionario_alias[equipo][nombre_original_bd].append(match_manual['Nombre'])
                            nuevas_relaciones.append((equipo, nombre_original_bd, match_manual['Nombre']))
                        
                        j_bd['Precio_Fantastica'] = match_manual.get('Precio_Fantastica')
                        j_bd['Puntos_PFSY'] = match_manual.get('Puntos_PFSY')
                        mercado_disponible.remove(match_manual)
                        j_bd['matched'] = True
                        match_manuales += 1
                        print("     ✅ Relación guardada.")

            # --- FASE 4: 🌍 BÚSQUEDA GLOBAL (Cualquier equipo, puntos similares +- 2) ---
            if not j_bd['matched']:
                cand_globales = [m for m in mercado_disponible if abs(limpiar_puntos(m.get('Puntos_PFSY', 0)) - pts_bd) <= 10]
                if cand_globales:
                    print(f"  [GLOBAL]      🌍 Buscando por toda la liga a: {nombre_original_bd} (Pts: {pts_bd})")
                    print("     0. ⏭️  Ninguno (Dejar huérfano)")
                    for idx, m in enumerate(cand_globales, 1):
                        print(f"     {idx}. {m['Nombre']} | Eq: {m['Equipo']} | (Pts: {limpiar_puntos(m.get('Puntos_PFSY', 0))})")
                    
                    try: opcion = int(input("     Opcion: "))
                    except ValueError: opcion = 0
                    
                    if 1 <= opcion <= len(cand_globales):
                        match_global = cand_globales[opcion - 1]
                        
                        # 🚨 SOBRESCRIBIMOS EL EQUIPO DE MERCADO CON EL DE LA BD
                        eq_antiguo = match_global['Equipo']
                        match_global['Equipo'] = equipo 
                        
                        if nombre_original_bd not in diccionario_alias[equipo]: diccionario_alias[equipo][nombre_original_bd] = []
                        if match_global['Nombre'] not in diccionario_alias[equipo][nombre_original_bd]:
                            diccionario_alias[equipo][nombre_original_bd].append(match_global['Nombre'])
                            nuevas_relaciones.append((equipo, nombre_original_bd, match_global['Nombre']))
                        
                        j_bd['Precio_Fantastica'] = match_global.get('Precio_Fantastica')
                        j_bd['Puntos_PFSY'] = match_global.get('Puntos_PFSY')
                        mercado_disponible.remove(match_global)
                        j_bd['matched'] = True
                        match_globales += 1
                        print(f"     ✅ ¡Cazado! Equipo corregido de {eq_antiguo} a {equipo}. Relación guardada.")

            # Al final de las 5 fases, si no hizo match, metemos NaN en el precio.
            # Lo añadimos a la lista final de jugadores fusionados en todos los casos.
            if not j_bd.get('Precio_Fantastica'):
                j_bd['Precio_Fantastica'] = None
                j_bd['Puntos_PFSY'] = None
            
            # Limpiamos variables temporales de cálculo antes de exportar
            j_bd.pop('matched', None)
            j_bd.pop('Key_Nombre', None)
            jugadores_fusionados.append(j_bd)

        # Imprimimos los huérfanos de este equipo
        faltantes = [j['Nombre'] for j in bd_eq if j.get('Precio_Fantastica') is None]
        if faltantes:
            print("  ❌ HUÉRFANOS (Sin datos de mercado):")
            for f in faltantes: print(f"     - {f}")
        print() 

    # --- GUARDAR MEMORIA Y GENERAR CSV ---
    if nuevas_relaciones:
        guardar_diccionario(diccionario_alias, ruta_diccionario)
        
    df_final = pd.DataFrame(jugadores_fusionados)
    df_final.to_csv(ruta_salida, index=False)

    # --- RESUMEN FINAL ---
    total_encontrados = match_memoria + match_exactos + match_inteligentes + match_manuales + match_globales
    print("======================================================")
    print("📊 RESUMEN FINAL DEL CRUCE")
    print(f"   -> Match Memoria (JSON): {match_memoria}")
    print(f"   -> Match Exacto:         {match_exactos}")
    print(f"   -> Match Aprendizaje:    {match_inteligentes}")
    print(f"   -> Match Manual Equipo:  {match_manuales}")
    print(f"   -> Match Global (🌍):    {match_globales}")
    print(f"   -> Total Cruzados:       {total_encontrados} / {total_bd} ({(total_encontrados/total_bd)*100:.1f}%)")
    print(f"\n💾 Archivo final generado con éxito en:\n   {ruta_salida}")
    print("======================================================")

if __name__ == "__main__":
    directorio_actual = os.path.dirname(os.path.abspath(__file__)) 
    carpeta_jaj = os.path.dirname(directorio_actual)               
    carpeta_raiz = os.path.dirname(carpeta_jaj)                    
    
    ARCHIVO_MERCADO = os.path.join(carpeta_raiz, "datasets", "JaJ", "T25-26", "J25", "mercado.csv")
    ARCHIVO_JUGADORES = os.path.join(carpeta_raiz, "datasets", "JaJ", "T25-26", "J25", "jugadores.csv")
    ARCHIVO_DICCIONARIO = os.path.join(carpeta_raiz, "recursos", "diccionario_jugadores.json")
    
    # 🚨 Nueva ruta para el CSV final fusionado
    ARCHIVO_SALIDA = os.path.join(carpeta_raiz, "datasets", "JaJ", "T25-26", "J25", "jugadores_con_mercado.csv")
    
    cruzar_datasets_inteligente(ARCHIVO_MERCADO, ARCHIVO_JUGADORES, ARCHIVO_DICCIONARIO, ARCHIVO_SALIDA)
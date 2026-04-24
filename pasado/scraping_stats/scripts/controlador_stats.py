import time
import os
import json
from crawler_sofascore import obtener_ids_jornada_sofascore
from sofascore_motor import procesar_lista_partidos

def ejecutar_scraping_jornada(temporada_str, id_temporada_sofa, jornada_num):
    """
    Controlador principal que orquesta la extracción de una jornada completa.
    Retorna True si fue un éxito, False si falló.
    """
    jornada_str = f"J{jornada_num}"
    
    print("=======================================================")
    print(f"  🚀 INICIANDO SCRAPING SOFASCORE: {temporada_str} - {jornada_str} ")
    print("=======================================================")

    try:
        # 1. El Crawler busca los IDs de la jornada
        lista_ids = obtener_ids_jornada_sofascore(id_temporada_sofa, jornada_num)

        if not lista_ids:
            print("⚠️ No se encontraron partidos para esta jornada o hubo error de red.")
            return False # Devolvemos False para registrar el fallo

        # 2. El Motor extrae todas las estadísticas y guarda el CSV
        procesar_lista_partidos(lista_ids, temporada_str, jornada_str)

        print("\n=======================================================")
        print(f"  🏁 EXTRACCIÓN DE LA {jornada_str} ({temporada_str}) FINALIZADA")
        print("=======================================================")
        return True # Éxito total

    except Exception as e:
        print(f"❌ Error crítico ejecutando la jornada: {e}")
        return False


if __name__ == "__main__":
    # --- 1. CARGAR EL DICCIONARIO DE IDs ---
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_json = os.path.join(directorio_actual, "codigos_temporadas.json")
    
    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            codigos_temporadas = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: No se encuentra el archivo {ruta_json}")
        exit()

    # --- 2. CONFIGURACIÓN DE SCRAPING ---
    scrapear = {
        "25-26": [33, 33, []]
    }

    # Aquí guardaremos las jornadas que vayan fallando: (temporada_str, id_sofa, jornada_num)
    jornadas_fallidas = []

    # --- 3. BUCLE MAESTRO (Primera pasada) ---
    for temporada, config in scrapear.items():
        jornada_inicio = config[0]
        jornada_fin = config[1]
        jornadas_saltar = config[2]
        
        id_sofa = codigos_temporadas.get(temporada)
        if not id_sofa:
            print(f"⚠️ Error: La temporada {temporada} no está en tu archivo JSON.")
            continue
            
        temporada_str = f"T{temporada.replace('/', '-')}"
        print(f"\n🏆 INICIANDO TEMPORADA {temporada_str} (ID SofaScore: {id_sofa})")
        
        for jornada_num in range(jornada_inicio, jornada_fin + 1):
            if jornada_num in jornadas_saltar:
                print(f"⏭️ Saltando la jornada {jornada_num} de {temporada_str}...")
                continue
                
            exito = ejecutar_scraping_jornada(temporada_str, id_sofa, jornada_num)
            
            # Si falla, la anotamos en la lista negra
            if not exito:
                jornadas_fallidas.append((temporada_str, id_sofa, jornada_num))
            
            print("\n☕ Pausa de 10 segundos para dejar respirar al servidor...")
            time.sleep(10)
            
            
    # --- 4. SISTEMA DE REINTENTOS MÁGICO ---
    intentos_realizados = 0
    max_reintentos = 2

    while jornadas_fallidas and intentos_realizados < max_reintentos:
        intentos_realizados += 1
        print("\n" + "!"*60)
        print(f" 🔄 INICIANDO RONDA DE REINTENTOS {intentos_realizados}/{max_reintentos}")
        print(f" Hay {len(jornadas_fallidas)} jornadas pendientes de recuperar.")
        print("!"*60 + "\n")
        
        # Copiamos la lista actual y la vaciamos. Solo volverán a entrar las que vuelvan a fallar.
        pendientes_actuales = list(jornadas_fallidas)
        jornadas_fallidas = []
        
        # Damos un respiro más largo antes de atacar de nuevo
        time.sleep(15) 
        
        for temp_str, id_sofa, j_num in pendientes_actuales:
            print(f"▶️ REINTENTANDO: {temp_str} - Jornada {j_num}")
            exito = ejecutar_scraping_jornada(temp_str, id_sofa, j_num)
            
            if not exito:
                jornadas_fallidas.append((temp_str, id_sofa, j_num))
                
            time.sleep(10)

    # --- 5. REPORTE FINAL Y GENERACIÓN DEL TXT ---
    print("\n=======================================================")
    if not jornadas_fallidas:
        print(" 🏆 ¡TODO EL PROCESO COMPLETADO CON ÉXITO! Cero fallos.")
    else:
        print(f" ⚠️ PROCESO TERMINADO. Quedaron {len(jornadas_fallidas)} jornadas imposibles de extraer.")
        
        # Generamos el TXT con los errores persistentes
        ruta_txt = os.path.join(directorio_actual, "errores_scraping_stats.txt")
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write("=== REGISTRO DE JORNADAS FALLIDAS (Tras reintentos) ===\n")
            for temp_str, _, j_num in jornadas_fallidas:
                f.write(f"- Temporada: {temp_str} | Jornada: {j_num}\n")
                
        print(f" 📝 Se ha generado un registro de fallos en: {ruta_txt}")
    print("=======================================================")


from pasado.scraping.controlador import ejecutar_temporada_completa

# --- EJECUCIÓN ---
'''jornadas_scrap = {
    "2023/24": [1, 38, []],
    "2024/25": [1, 38, []],
    "2025/26": [1, 24, []]
}'''
jornadas_scrap = {"2025/26": [24, 25, []]}

ejecutar_temporada_completa(jornadas_scrap)
EQUIPOS_ESTANDAR = [
    "Alavés", "Almería", "Athletic", "Atlético", "Barcelona", "Betis", "Cádiz", 
    "Celta", "Elche", "Espanyol", "Getafe", "Girona", "Granada", "Las Palmas", 
    "Leganés", "Levante", "Mallorca", "Osasuna", "Rayo", "Real Madrid", 
    "Real Oviedo", "Real Sociedad", "Sevilla", "Valencia", "Valladolid", "Villarreal"
]

MAPEO_ALIAS_EQUIPOS = {
    "fc barcelona": "Barcelona", "barca": "Barcelona",
    "atletico de madrid": "Atlético", "atletico": "Atlético", "atleti": "Atlético", "at madrid": "Atlético",
    "athletic club": "Athletic", "athletic": "Athletic",
    "real betis": "Betis", "betis": "Betis",
    "rayo vallecano": "Rayo", "rayo": "Rayo",
    "celta de vigo": "Celta", "celta": "Celta",
    "rcd espanyol": "Espanyol", "espanyol": "Espanyol",
    "real valladolid": "Valladolid", "valladolid": "Valladolid",
    "deportivo alaves": "Alavés", "alaves": "Alavés",
    "ca osasuna": "Osasuna", "osasuna": "Osasuna",
    "rcd mallorca": "Mallorca", "mallorca": "Mallorca",
    "valencia cf": "Valencia", "valencia": "Valencia",
    "villarreal cf": "Villarreal", "villarreal": "Villarreal",
    "getafe cf": "Getafe", "getafe": "Getafe",
    "girona fc": "Girona", "girona": "Girona",
    "sevilla fc": "Sevilla", "sevilla": "Sevilla",
    "ud las palmas": "Las Palmas", "las palmas": "Las Palmas",
    "cd leganes": "Leganés", "leganes": "Leganés",
    "levante ud": "Levante", "levante": "Levante",
    "real oviedo": "Real Oviedo", "oviedo": "Real Oviedo",
    "espanyol de b": "Espanyol", "espanyol": "Espanyol",
    "atletico de madrid": "Atlético", "atletico": "Atlético",
    "villarreal cf": "Villarreal", "villarreal": "Villarreal"
}

MAPEO_POSICIONES = {
    'POR': 'Portero', 'P0R': 'Portero', 'PQR': 'Portero',
    'DEF': 'Defensa', '0EF': 'Defensa', 'OEF': 'Defensa',
    'CEN': 'Mediocampista', 'MED': 'Mediocampista', 'MEO': 'Mediocampista',
    'DEL': 'Delantero', '0EL': 'Delantero', 'OEL': 'Delantero'
}

BASURA_NOMBRES = ["club", "clup", "real", "deportivo", "sociedad", "unión", "deportiva", "cf", "ud", "rcd", "sd", "hcd", "espanyor", "ae", "puk"]

EQUIPOS_MINUSCULA = [e.lower() for e in EQUIPOS_ESTANDAR]
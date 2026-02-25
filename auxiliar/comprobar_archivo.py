import os
def obtener_nombre_archivo_unico(ruta_archivo):
    """
    Comprueba si el archivo ya existe. Si es así, añade (1), (2)... al final del nombre.
    """
    if not os.path.exists(ruta_archivo):
        return ruta_archivo
    
    # Separamos la ruta en directorio y archivo, y el archivo en nombre y extensión
    directorio, nombre_con_ext = os.path.split(ruta_archivo)
    nombre, extension = os.path.splitext(nombre_con_ext)
    
    contador = 1
    nueva_ruta = os.path.join(directorio, f"{nombre}({contador}){extension}")
    
    # Bucle hasta encontrar un número que esté libre
    while os.path.exists(nueva_ruta):
        contador += 1
        nueva_ruta = os.path.join(directorio, f"{nombre}({contador}){extension}")
        
    return nueva_ruta
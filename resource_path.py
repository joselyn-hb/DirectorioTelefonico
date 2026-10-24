# Este archivo ayuda a localizar recursos de la aplicación, como imágenes o archivos
# que están dentro de la carpeta del proyecto o dentro de un ejecutable generado.
# Es útil porque en algunos casos Python se ejecuta desde una ruta distinta.

import os
import sys


# Esta función recibe una ruta relativa y devuelve la ruta completa correcta.
# Ejemplo: si el programa está empaquetado, la imagen puede estar en una carpeta temporal.
def resource_path(relative_path):
    """
    Devuelve la ruta absoluta de un archivo o carpeta.

    ¿Para qué sirve?
    - Cuando se ejecuta directamente desde Python, usamos la carpeta actual.
    - Cuando la app está empaquetada con PyInstaller, el archivo real puede estar
      guardado en una carpeta temporal llamada sys._MEIPASS.
    """
    try:
        # PyInstaller crea archivos temporales en una carpeta que se guarda en esta variable.
        base_path = sys._MEIPASS
    except Exception:
        # Si no existe esa carpeta temporal, estamos ejecutando la app en desarrollo.
        base_path = os.path.abspath(".")

    # Unimos la carpeta base con la ruta relativa del recurso solicitado.
    return os.path.join(base_path, relative_path)
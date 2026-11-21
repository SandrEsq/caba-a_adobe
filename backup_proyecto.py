"""
backup_proyecto.py — Copia todo el proyecto a la carpeta SS del Escritorio.

Uso:
    python backup_proyecto.py
Copia todos los archivos (código, HTML, base de datos, etc.) a:
    C:\\Users\\najan\\OneDrive\\Imágenes\\Escritorio\\SS
Ignora __pycache__, .git y archivos temporales. Sobrescribe versiones anteriores.
"""

import os
import sys
import shutil

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DST_DIR = r"C:\Users\najan\OneDrive\Imágenes\Escritorio\SS"

def ignorar(directorio, contenidos):
    ignorados = []
    for item in contenidos:
        if item in ("__pycache__", ".git", ".venv", "venv"):
            ignorados.append(item)
        elif item.endswith((".pyc", ".pyo", ".tmp")):
            ignorados.append(item)
    return ignorados

def main():
    if not os.path.exists(DST_DIR):
        os.makedirs(DST_DIR)
    shutil.copytree(SRC_DIR, DST_DIR, dirs_exist_ok=True, ignore=ignorar)
    print("✅ Proyecto copiado exitosamente a: " + DST_DIR)

if __name__ == "__main__":
    main()

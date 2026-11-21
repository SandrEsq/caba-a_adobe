"""
crear_zip.py — Respaldo automático del proyecto "La Cabaña de Adobe".

Uso:
    python crear_zip.py
Genera el archivo LaCabana_Backup.zip en la misma carpeta,
ignorando __pycache__ y archivos temporales.
"""

import os
import sys
import zipfile

# Evitar error de codificación en consolas de Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_NAME = "LaCabana_Backup.zip"
ZIP_PATH = os.path.join(BASE_DIR, ZIP_NAME)

# Carpetas/archivos a ignorar
IGNORAR_CARPETAS = {"__pycache__", ".git", ".venv", "venv"}
IGNORAR_EXTENSIONES = {".pyc", ".pyo", ".tmp"}

def main():
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            # Evitar carpetas ignoradas
            dirs[:] = [d for d in dirs if d not in IGNORAR_CARPETAS]
            for filename in files:
                if filename == ZIP_NAME:
                    continue
                if os.path.splitext(filename)[1].lower() in IGNORAR_EXTENSIONES:
                    continue
                ruta_completa = os.path.join(root, filename)
                ruta_relativa = os.path.relpath(ruta_completa, BASE_DIR)
                zf.write(ruta_completa, ruta_relativa)
    print("✅ Backup creado exitosamente: " + ZIP_NAME)

if __name__ == "__main__":
    main()

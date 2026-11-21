"""
sincronizar_todo.py — Respaldo local + subida automatica a GitHub.

Uso:
    python sincronizar_todo.py
"""

import os
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DST_DIR = r"C:\Users\najan\OneDrive\Imágenes\Escritorio\SS"

# Asegurar salida UTF-8 en Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def ignorar(directorio, contenidos):
    ignorados = []
    for item in contenidos:
        if item in ("__pycache__", ".git", ".venv", "venv"):
            ignorados.append(item)
        elif item.endswith((".pyc", ".pyo", ".tmp")):
            ignorados.append(item)
    return ignorados


def paso_respaldo_local():
    print("Copiando archivos a la carpeta de respaldo...")
    if not os.path.exists(DST_DIR):
        os.makedirs(DST_DIR)
    shutil.copytree(BASE_DIR, DST_DIR, dirs_exist_ok=True, ignore=ignorar)
    print("Respaldo local completado: " + DST_DIR)


def ejecutar_git(args):
    return subprocess.run(
        ["git"] + args,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def paso_github():
    print("Subiendo cambios a GitHub...")

    # git add .
    r = ejecutar_git(["add", "."])
    if r.returncode != 0:
        print("Error en git add:")
        print(r.stderr)
        return

    # git commit
    r = ejecutar_git(["commit", "-m", "Actualizacion automatica del POS"])
    if r.returncode != 0:
        salida = (r.stdout + r.stderr).lower()
        if "nothing to commit" in salida or "no changes added" in salida:
            print("No hay cambios nuevos para subir a GitHub.")
        else:
            print("Error en git commit:")
            print(r.stderr)
            return
    else:
        print("Commit realizado.")

    # git push
    r = ejecutar_git(["push", "origin", "main"])
    if r.returncode != 0:
        # Intentar con la rama actual
        rama = ejecutar_git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        r = ejecutar_git(["push", "origin", rama])
        if r.returncode != 0:
            print("Error en git push:")
            print(r.stderr)
            return
    print("Cambios subidos a GitHub correctamente.")


def main():
    paso_respaldo_local()
    paso_github()
    print("Proceso finalizado.")


if __name__ == "__main__":
    main()

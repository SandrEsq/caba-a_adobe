LA CABAÑA DE ADOBE - POS (Prototipo)

Requisitos: Python 3.10+ instalado.

Pasos para correr:
1. Abrir una terminal en esta carpeta.
2. Instalar Flask:  pip install -r requirements.txt
3. Crear la base de datos:  python init_db.py
4. Arrancar el servidor:  python app.py
5. Abrir en el navegador:
   - Mesero: http://localhost:5000/   (token 4512 o 7845)
   - Cocina: http://localhost:5000/cocina
   - Admin:  http://localhost:5000/admin  (token 9999)

Notas:
- Si marcaste platillos como agotados y quieres empezar limpio, vuelve a ejecutar: python init_db.py
- Para ver/editar la base de datos, usa DB Browser for SQLite sobre el archivo cabana_final.db

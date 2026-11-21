"""
init_db.py — Base de datos SQLite para el POS "La Cabaña de Adobe" (FastAPI).

Uso:
    python init_db.py
Genera `cabana_final.db` en el mismo directorio.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cabana_final.db")

def crear_bd():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Meseros / usuarios
    cur.execute("""
        CREATE TABLE meseros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'MESERO',
            activo INTEGER NOT NULL DEFAULT 1
        );
    """)

    # Menú por categorías (con menú del día)
    cur.execute("""
        CREATE TABLE menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            categoria TEXT NOT NULL,
            emoji TEXT NOT NULL,
            disponible INTEGER NOT NULL DEFAULT 1,
            es_menu_dia INTEGER NOT NULL DEFAULT 0
        );
    """)

    # Extras
    cur.execute("""
        CREATE TABLE extras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL
        );
    """)

    # Pedidos
    cur.execute("""
        CREATE TABLE pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mesa INTEGER NOT NULL,
            zona TEXT NOT NULL,
            mesero_id INTEGER NOT NULL,
            estado TEXT NOT NULL DEFAULT 'PENDIENTE',
            total REAL NOT NULL DEFAULT 0,
            fecha TEXT NOT NULL,
            FOREIGN KEY (mesero_id) REFERENCES meseros(id)
        );
    """)

    # Detalle de pedido (con nota y surtido para checklist de cocina)
    cur.execute("""
        CREATE TABLE detalle_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            menu_id INTEGER,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL,
            nombre_personalizado TEXT,
            nota TEXT,
            surtido INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
            FOREIGN KEY (menu_id) REFERENCES menu(id)
        );
    """)

    # Pagos
    cur.execute("""
        CREATE TABLE pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            metodo_pago TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        );
    """)

    # Mesas por zona (configurables por admin)
    cur.execute("""
        CREATE TABLE mesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zona TEXT NOT NULL,
            numero_mesa INTEGER NOT NULL,
            activa INTEGER NOT NULL DEFAULT 1,
            UNIQUE(zona, numero_mesa)
        );
    """)
    for zona in ("Salón", "Terraza", "Jardín"):
        for n in range(1, 11):
            cur.execute("INSERT INTO mesas (zona, numero_mesa, activa) VALUES (?,?,1);", (zona, n))

    # Meseros de prueba
    cur.execute("INSERT INTO meseros (token, nombre, rol, activo) VALUES ('4512','Carlos','MESERO',1);")
    cur.execute("INSERT INTO meseros (token, nombre, rol, activo) VALUES ('7845','Ana','MESERO',1);")
    cur.execute("INSERT INTO meseros (token, nombre, rol, activo) VALUES ('9999','Administrador','ADMIN',1);")

    # Menú real completo
    menu = [
        ("Plato de Birria", 160, "Platillos Fuertes", "🍽️", 1),
        ("Plato de Pancita", 150, "Platillos Fuertes", "🍽️", 0),
        ("Mixiote de Carnero", 155, "Platillos Fuertes", "🍽️", 0),
        ("Parrillada 2 personas", 370, "Parrilladas", "🍽️", 1),
        ("Parrillada 4 personas", 685, "Parrilladas", "🍽️", 0),
        ("Parrillada 6 personas", 875, "Parrilladas", "🍽️", 0),
        ("Quesabirria", 65, "Parrilladas", "🍽️", 0),
        ("Suadero", 40, "Tacos", "🍽️", 0),
        ("Longaniza", 40, "Tacos", "🍽️", 0),
        ("Enchilada", 40, "Tacos", "🍽️", 0),
        ("Pechuga", 40, "Tacos", "🍽️", 0),
        ("Arrachera", 65, "Tacos", "🍽️", 1),
        ("Chistorra", 45, "Tacos", "🍽️", 0),
        ("Chorizo Arg", 45, "Tacos", "🍽️", 0),
        ("Cecina", 55, "Tacos", "🍽️", 0),
        ("Birria", 50, "Tacos", "🍽️", 0),
        ("Costilla", 55, "Tacos", "🍽️", 0),
        ("Guacamole c/chicharrón", 75, "Complementos", "🍽️", 0),
        ("Frijoles refritos c/totopos", 35, "Complementos", "🍽️", 0),
        ("Papas asadas", 45, "Complementos", "🍽️", 0),
        ("Orden de nopales", 45, "Complementos", "🍽️", 0),
        ("Orden de cebollitas", 45, "Complementos", "🍽️", 0),
        ("Aguacate 1 pza", 35, "Complementos", "🍽️", 0),
        ("Quesadillas 3 pzas", 65, "Complementos", "🍽️", 0),
        ("Sopecitos 3 pzas", 65, "Complementos", "🍽️", 0),
        ("Consomé de Birria", 20, "Complementos", "🍽️", 0),
        ("Quesadillas", 35, "Antojitos", "🍽️", 0),
        ("Huarache", 140, "Antojitos", "🍽️", 0),
        ("Choriqueso", 120, "Antojitos", "🍽️", 0),
        ("Jarra 2 L", 90, "Agua de Fruta", "🍽️", 0),
        ("Jarra 1 L", 65, "Agua de Fruta", "🍽️", 0),
        ("Vaso 500 ml", 35, "Agua de Fruta", "🍽️", 0),
        ("Heineken", 55, "Cervezas", "🍽️", 0),
        ("Indio", 45, "Cervezas", "🍽️", 0),
        ("Victoria", 45, "Cervezas", "🍽️", 0),
        ("Carta Blanca", 40, "Cervezas", "🍽️", 0),
        ("Modelo", 55, "Cervezas", "🍽️", 0),
        ("XX Lager", 45, "Cervezas", "🍽️", 0),
        ("Heineken ", 95, "Caguamas", "🍽️", 0),
        ("Indio ", 95, "Caguamas", "🍽️", 0),
        ("Victoria ", 95, "Caguamas", "🍽️", 0),
        ("Modelo ", 95, "Caguamas", "🍽️", 0),
        ("Vaso escarchado", 15, "Caguamas", "🍽️", 0),
        ("Vaso Michelada", 30, "Caguamas", "🍽️", 0),
        ("Coca Cola 600ml", 39, "Refrescos", "🍽️", 0),
        ("Coca Cola Lata", 35, "Refrescos", "🍽️", 0),
        ("Sangría 600ml", 35, "Refrescos", "🍽️", 0),
        ("Boing 500ml", 35, "Refrescos", "🍽️", 0),
        ("Agua Mineral 500ml", 35, "Refrescos", "🍽️", 0),
        ("Agua embotellada", 30, "Refrescos", "🍽️", 0),
        ("Cantarito", 75, "Refrescos", "🍽️", 0),
        ("Caballito Tequila", 70, "Refrescos", "🍽️", 0),
        ("Caballito Mezcal", 85, "Refrescos", "🍽️", 0),
        ("Café de olla", 35, "Bebidas Calientes/Postres", "🍽️", 0),
        ("Té", 35, "Bebidas Calientes/Postres", "🍽️", 0),
        ("Atole", 35, "Bebidas Calientes/Postres", "🍽️", 0),
        ("Ponche", 35, "Bebidas Calientes/Postres", "🍽️", 0),
        ("Cocol", 10, "Bebidas Calientes/Postres", "🍽️", 0),
        ("Pastel de Chocolate", 50, "Bebidas Calientes/Postres", "🍽️", 0),
    ]
    cur.executemany("INSERT INTO menu (nombre, precio, categoria, emoji, disponible, es_menu_dia) VALUES (?,?,?,?,1,?);", menu)

    # Extras
    extras = [("Limones", 10), ("Salsas", 10), ("Cebollitas", 15), ("Tortillas", 15), ("Queso extra", 20)]
    cur.executemany("INSERT INTO extras (nombre, precio) VALUES (?,?);", extras)

    conn.commit()
    conn.close()
    print("Base de datos creada en: " + DB_PATH)

if __name__ == "__main__":
    crear_bd()

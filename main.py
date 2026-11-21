"""
main.py — Backend FastAPI para el POS "La Cabaña de Adobe".

Ejecutar:
    python main.py
o:
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
import sqlite3
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "cabana_final.db")

app = FastAPI(title="La Cabaña de Adobe POS")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_db(sql, args=(), one=False):
    conn = get_db()
    cur = conn.execute(sql, args)
    rows = cur.fetchall()
    conn.close()
    return (rows[0] if rows else None) if one else rows


# ---------- Vistas ----------
@app.get("/")
def vista_mesero():
    return FileResponse(os.path.join(BASE_DIR, "mesero.html"))


@app.get("/cocina")
def vista_cocina():
    return FileResponse(os.path.join(BASE_DIR, "cocina.html"))


@app.get("/admin")
def vista_admin():
    return FileResponse(os.path.join(BASE_DIR, "admin.html"))


# ---------- API: Login ----------
@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    token = (data.get("token") or "").strip()
    if len(token) != 4 or not token.isdigit():
        raise HTTPException(status_code=400, detail="Token debe ser de 4 dígitos")
    row = query_db("SELECT id, token, nombre, rol, activo FROM meseros WHERE token = ?", (token,), one=True)
    if not row:
        raise HTTPException(status_code=401, detail="Token inválido")
    if not row["activo"]:
        raise HTTPException(status_code=403, detail="Usuario dado de baja")
    return {"ok": True, "id": row["id"], "token": row["token"],
            "nombre": row["nombre"], "rol": row["rol"]}


# ---------- API: Menú ----------
@app.get("/api/menu")
def menu():
    rows = query_db("SELECT id, nombre, precio, categoria, emoji, disponible, es_menu_dia FROM menu ORDER BY es_menu_dia DESC, categoria, id")
    return [dict(r) for r in rows]


# ---------- API: Extras ----------
@app.get("/api/extras")
def extras():
    rows = query_db("SELECT id, nombre, precio FROM extras ORDER BY id")
    return [dict(r) for r in rows]


# ---------- API: Crear pedido ----------
@app.post("/api/crear_pedido")
async def crear_pedido(request: Request):
    data = await request.json()
    token = data.get("token")
    mesa = data.get("mesa")
    zona = data.get("zona")
    items = data.get("items", [])

    if not token or not mesa or not zona or not items:
        raise HTTPException(status_code=400, detail="Datos incompletos")

    mesero = query_db("SELECT id, nombre FROM meseros WHERE token = ? AND activo = 1", (token,), one=True)
    if not mesero:
        raise HTTPException(status_code=401, detail="Token inválido")

    conn = get_db()
    cur = conn.cursor()
    total = 0.0
    # Calcular total primero (validando disponibilidad)
    for it in items:
        qty = int(it.get("cantidad", 1))
        if "menu_id" in it:
            m = conn.execute("SELECT precio, disponible FROM menu WHERE id = ?", (it["menu_id"],)).fetchone()
            if not m:
                conn.close()
                raise HTTPException(status_code=400, detail="Platillo no existe")
            if not m["disponible"]:
                conn.close()
                raise HTTPException(status_code=400, detail="Platillo agotado")
            price = m["precio"]
        elif "extra_id" in it:
            e = conn.execute("SELECT nombre, precio FROM extras WHERE id = ?", (it["extra_id"],)).fetchone()
            if not e:
                conn.close()
                raise HTTPException(status_code=400, detail="Extra no existe")
            price = e["precio"]
        else:
            price = float(it.get("precio", 0) or 0)
        total += price * qty

    # Crear pedido
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO pedidos (mesa, zona, mesero_id, estado, total, fecha) VALUES (?,?,?,?,?,?)",
        (mesa, zona, mesero["id"], "PENDIENTE", round(total, 2), fecha),
    )
    pedido_id = cur.lastrowid

    # Insertar detalles
    for it in items:
        qty = int(it.get("cantidad", 1))
        if "menu_id" in it:
            m = conn.execute("SELECT precio FROM menu WHERE id = ?", (it["menu_id"],)).fetchone()
            price = m["precio"]
            menu_id = it["menu_id"]
            nombre_pers = None
            nota = it.get("nota")
        elif "extra_id" in it:
            e = conn.execute("SELECT nombre, precio FROM extras WHERE id = ?", (it["extra_id"],)).fetchone()
            price = e["precio"]
            menu_id = None
            nombre_pers = e["nombre"]
            nota = it.get("nota")
        else:
            nombre_pers = (it.get("nombre") or "Personalizado").strip()
            price = float(it.get("precio", 0) or 0)
            menu_id = None
            nota = it.get("nota")
        cur.execute(
            """INSERT INTO detalle_pedido (pedido_id, menu_id, cantidad, precio_unitario, nombre_personalizado, nota)
               VALUES (?,?,?,?,?,?)""",
            (pedido_id, menu_id, qty, price, nombre_pers, nota),
        )

    conn.commit()
    conn.close()
    return {"ok": True, "pedido_id": pedido_id, "total": round(total, 2), "estado": "PENDIENTE"}


# ---------- API: Pedidos cocina ----------
@app.get("/api/pedidos_cocina")
def pedidos_cocina():
    rows = query_db(
        """SELECT p.id, p.mesa, p.zona, p.estado, p.total, p.fecha, m.nombre AS mesero_nombre
           FROM pedidos p JOIN meseros m ON m.id = p.mesero_id
           WHERE p.estado IN ('PENDIENTE','EN_PREPARACION') ORDER BY p.id ASC"""
    )
    resultado = []
    for r in rows:
        detalles = query_db(
            """SELECT dp.id, dp.menu_id, dp.cantidad, dp.nombre_personalizado, dp.nota, dp.precio_unitario, dp.surtido,
                      mn.nombre, mn.emoji
               FROM detalle_pedido dp LEFT JOIN menu mn ON mn.id = dp.menu_id
               WHERE dp.pedido_id = ?""",
            (r["id"],),
        )
        det_list = []
        for d in detalles:
            nombre = d["nombre"] if d["nombre"] else d["nombre_personalizado"]
            emoji = d["emoji"] if d["emoji"] else "📝"
            det_list.append({
                "detalle_id": d["id"],
                "menu_id": d["menu_id"],
                "cantidad": d["cantidad"],
                "nombre": nombre,
                "emoji": emoji,
                "nota": d["nota"],
                "precio": d["precio_unitario"],
                "surtido": bool(d["surtido"]),
            })
        resultado.append({
            "id": r["id"], "mesa": r["mesa"], "zona": r["zona"],
            "mesero_nombre": r["mesero_nombre"], "estado": r["estado"],
            "total": r["total"], "fecha": r["fecha"],
            "detalles": det_list,
        })
    return resultado


# ---------- API: Cambiar estado ----------
@app.post("/api/cambiar_estado")
async def cambiar_estado(request: Request):
    data = await request.json()
    pedido_id = data.get("pedido_id")
    estado = data.get("estado")
    validos = {"PENDIENTE", "EN_PREPARACION", "LISTO", "PAGADO", "CANCELADO"}
    if estado not in validos:
        raise HTTPException(status_code=400, detail="Estado inválido")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE pedidos SET estado = ? WHERE id = ?", (estado, pedido_id))
    conn.commit()
    afectados = cur.rowcount
    conn.close()
    if afectados == 0:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return {"ok": True, "pedido_id": pedido_id, "estado": estado}


# ---------- API: Cancelar pedido ----------
@app.post("/api/cancelar_pedido/{pedido_id}")
def cancelar_pedido(pedido_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE pedidos SET estado = 'CANCELADO' WHERE id = ?", (pedido_id,))
    conn.commit()
    afectados = cur.rowcount
    conn.close()
    if afectados == 0:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return {"ok": True, "pedido_id": pedido_id, "estado": "CANCELADO"}


# ---------- API: Editar pedido ----------
@app.put("/api/editar_pedido/{pedido_id}")
async def editar_pedido(pedido_id: int, request: Request):
    data = await request.json()
    items = data.get("items", [])

    row = query_db("SELECT estado, mesero_id FROM pedidos WHERE id = ?", (pedido_id,), one=True)
    if not row:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if row["estado"] in ("PAGADO", "CANCELADO"):
        raise HTTPException(status_code=400, detail="No se puede editar este pedido")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM detalle_pedido WHERE pedido_id = ?", (pedido_id,))

    total = 0.0
    for it in items:
        qty = int(it.get("cantidad", 1))
        if "menu_id" in it and it.get("menu_id"):
            m = conn.execute("SELECT precio, disponible FROM menu WHERE id = ?", (it["menu_id"],)).fetchone()
            if not m:
                conn.close()
                raise HTTPException(status_code=400, detail="Platillo no existe")
            if not m["disponible"]:
                conn.close()
                raise HTTPException(status_code=400, detail="Platillo agotado")
            price = m["precio"]
            menu_id = it["menu_id"]
            nombre_pers = None
        elif "extra_id" in it and it.get("extra_id"):
            e = conn.execute("SELECT nombre, precio FROM extras WHERE id = ?", (it["extra_id"],)).fetchone()
            if not e:
                conn.close()
                raise HTTPException(status_code=400, detail="Extra no existe")
            price = e["precio"]
            menu_id = None
            nombre_pers = e["nombre"]
        else:
            nombre_pers = (it.get("nombre") or "Personalizado").strip()
            price = float(it.get("precio", 0) or 0)
            menu_id = None

        nota = it.get("nota")
        cur.execute(
            """INSERT INTO detalle_pedido (pedido_id, menu_id, cantidad, precio_unitario, nombre_personalizado, nota)
               VALUES (?,?,?,?,?,?)""",
            (pedido_id, menu_id, qty, price, nombre_pers, nota),
        )
        total += price * qty

    new_estado = "PENDIENTE" if row["estado"] == "EN_PREPARACION" else row["estado"]
    cur.execute("UPDATE pedidos SET total = ?, estado = ? WHERE id = ?", (round(total, 2), new_estado, pedido_id))
    conn.commit()
    conn.close()
    return {"ok": True, "pedido_id": pedido_id, "total": round(total, 2), "estado": new_estado}


# ---------- API: Toggle disponibilidad ----------
@app.post("/api/toggle_disponibilidad")
async def toggle_disponibilidad(request: Request):
    data = await request.json()
    menu_id = data.get("menu_id")
    disponible = data.get("disponible")
    if disponible not in (0, 1):
        raise HTTPException(status_code=400, detail="Valor inválido")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE menu SET disponible = ? WHERE id = ?", (disponible, menu_id))
    conn.commit()
    afectados = cur.rowcount
    conn.close()
    if afectados == 0:
        raise HTTPException(status_code=404, detail="Platillo no encontrado")
    return {"ok": True, "menu_id": menu_id, "disponible": disponible}


# ---------- API: Mis pedidos activos ----------
@app.get("/api/mis_pedidos/{token_mesero}")
def mis_pedidos(token_mesero: str):
    mesero = query_db("SELECT id FROM meseros WHERE token = ? AND activo = 1", (token_mesero,), one=True)
    if not mesero:
        raise HTTPException(status_code=401, detail="Token inválido")
    rows = query_db(
        """SELECT id, mesa, zona, estado, total, fecha
           FROM pedidos
           WHERE mesero_id = ? AND estado NOT IN ('PAGADO','CANCELADO')
           ORDER BY id DESC""",
        (mesero["id"],),
    )
    resultado = []
    for r in rows:
        detalles = query_db(
            """SELECT dp.id, dp.menu_id, dp.cantidad, dp.nombre_personalizado, dp.nota, dp.precio_unitario, dp.surtido,
                      mn.nombre, mn.emoji
               FROM detalle_pedido dp LEFT JOIN menu mn ON mn.id = dp.menu_id
               WHERE dp.pedido_id = ?""",
            (r["id"],),
        )
        det_list = []
        for d in detalles:
            nombre = d["nombre"] if d["nombre"] else d["nombre_personalizado"]
            emoji = d["emoji"] if d["emoji"] else "📝"
            det_list.append({
                "detalle_id": d["id"],
                "menu_id": d["menu_id"],
                "cantidad": d["cantidad"],
                "nombre": nombre,
                "emoji": emoji,
                "nota": d["nota"],
                "precio": d["precio_unitario"],
                "surtido": bool(d["surtido"]),
            })
        resultado.append({
            "id": r["id"], "mesa": r["mesa"], "zona": r["zona"],
            "estado": r["estado"], "total": r["total"], "fecha": r["fecha"],
            "detalles": det_list,
        })
    return {"ok": True, "pedidos": resultado}


# ---------- API: Procesar pago ----------
@app.post("/api/procesar_pago")
async def procesar_pago(request: Request):
    data = await request.json()
    pedido_id = data.get("pedido_id")
    metodo = data.get("metodo_pago")
    if metodo not in ("Efectivo", "Tarjeta", "Transferencia"):
        raise HTTPException(status_code=400, detail="Método de pago inválido")
    row = query_db("SELECT total FROM pedidos WHERE id = ?", (pedido_id,), one=True)
    if not row:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    conn = get_db()
    cur = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO pagos (pedido_id, metodo_pago, monto, fecha) VALUES (?,?,?,?)",
                (pedido_id, metodo, row["total"], fecha))
    cur.execute("UPDATE pedidos SET estado = 'PAGADO' WHERE id = ?", (pedido_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "pedido_id": pedido_id, "metodo_pago": metodo, "monto": row["total"]}


# ---------- API: Admin reportes ----------
@app.get("/api/admin/reportes")
def admin_reportes():
    hoy = datetime.now().strftime("%Y-%m-%d")
    por_metodo = query_db(
        """SELECT metodo_pago, COUNT(*) AS num, SUM(monto) AS total
           FROM pagos WHERE fecha LIKE ? GROUP BY metodo_pago""",
        (hoy + "%",),
    )
    por_mesero = query_db(
        """SELECT m.nombre, m.token, COUNT(p.id) AS num_pedidos, SUM(p.total) AS total_vendido
           FROM pedidos p JOIN meseros m ON m.id = p.mesero_id
           WHERE p.estado = 'PAGADO' AND p.fecha LIKE ?
           GROUP BY m.id ORDER BY total_vendido DESC""",
        (hoy + "%",),
    )
    total_hoy = query_db(
        "SELECT COALESCE(SUM(monto),0) AS t FROM pagos WHERE fecha LIKE ?",
        (hoy + "%",), one=True,
    )
    return {
        "fecha": hoy,
        "total_hoy": total_hoy["t"],
        "por_metodo": [dict(r) for r in por_metodo],
        "por_mesero": [dict(r) for r in por_mesero],
    }


# ---------- API: Admin meseros ----------
@app.get("/api/admin/meseros")
def admin_listar_meseros():
    rows = query_db("SELECT id, token, nombre, rol, activo FROM meseros ORDER BY id")
    return [dict(r) for r in rows]


@app.post("/api/admin/meseros")
async def admin_crear_mesero(request: Request):
    data = await request.json()
    token = (data.get("token") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    rol = data.get("rol", "MESERO")
    if len(token) != 4 or not token.isdigit() or not nombre:
        raise HTTPException(status_code=400, detail="Datos inválidos")
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO meseros (token, nombre, rol, activo) VALUES (?,?,?,1)", (token, nombre, rol))
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Token ya existe")
    conn.close()
    return {"ok": True, "id": new_id}


@app.post("/api/admin/meseros/{mid}/toggle")
async def admin_toggle_mesero(mid: int, request: Request):
    data = await request.json()
    activo = data.get("activo")
    if activo not in (0, 1):
        raise HTTPException(status_code=400, detail="Valor inválido")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE meseros SET activo = ? WHERE id = ?", (activo, mid))
    conn.commit()
    afectados = cur.rowcount
    conn.close()
    if afectados == 0:
        raise HTTPException(status_code=404, detail="Mesero no encontrado")
    return {"ok": True, "id": mid, "activo": activo}


# ---------- API: Admin menú ----------
@app.get("/api/admin/menu")
def admin_listar_menu():
    rows = query_db("SELECT id, nombre, precio, categoria, emoji, disponible, es_menu_dia FROM menu ORDER BY categoria, id")
    return [dict(r) for r in rows]


@app.post("/api/admin/menu")
async def admin_crear_platillo(request: Request):
    data = await request.json()
    nombre = (data.get("nombre") or "").strip()
    precio = data.get("precio")
    categoria = (data.get("categoria") or "").strip()
    emoji = (data.get("emoji") or "🍽️").strip()
    if not nombre or precio is None or not categoria:
        raise HTTPException(status_code=400, detail="Datos incompletos")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO menu (nombre, precio, categoria, emoji, disponible) VALUES (?,?,?,?,1)",
                (nombre, float(precio), categoria, emoji))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"ok": True, "id": new_id}


@app.put("/api/admin/menu/{pid}")
async def admin_editar_platillo(pid: int, request: Request):
    data = await request.json()
    nombre = data.get("nombre")
    precio = data.get("precio")
    categoria = data.get("categoria")
    emoji = data.get("emoji")
    disponible = data.get("disponible")
    conn = get_db()
    cur = conn.cursor()
    if nombre is not None:
        cur.execute("UPDATE menu SET nombre = ? WHERE id = ?", (nombre, pid))
    if precio is not None:
        cur.execute("UPDATE menu SET precio = ? WHERE id = ?", (float(precio), pid))
    if categoria is not None:
        cur.execute("UPDATE menu SET categoria = ? WHERE id = ?", (categoria, pid))
    if emoji is not None:
        cur.execute("UPDATE menu SET emoji = ? WHERE id = ?", (emoji, pid))
    if disponible is not None:
        cur.execute("UPDATE menu SET disponible = ? WHERE id = ?", (int(disponible), pid))
    conn.commit()
    afectados = cur.rowcount
    conn.close()
    if afectados == 0:
        raise HTTPException(status_code=404, detail="Platillo no encontrado")
    return {"ok": True, "id": pid}


@app.delete("/api/admin/menu/{pid}")
def admin_eliminar_platillo(pid: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM menu WHERE id = ?", (pid,))
    conn.commit()
    afectados = cur.rowcount
    conn.close()
    if afectados == 0:
        raise HTTPException(status_code=404, detail="Platillo no encontrado")
    return {"ok": True, "id": pid}


# ---------- API: Surtir platillo (checklist cocina) ----------
@app.put("/api/surtir_platillo/{detalle_id}")
async def surtir_platillo(detalle_id: int, request: Request):
    data = await request.json()
    surtido = data.get("surtido")
    if surtido not in (0, 1):
        raise HTTPException(status_code=400, detail="Valor inválido")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE detalle_pedido SET surtido = ? WHERE id = ?", (int(surtido), detalle_id))
    conn.commit()
    # Obtener pedido_id
    row = conn.execute("SELECT pedido_id FROM detalle_pedido WHERE id = ?", (detalle_id,)).fetchone()
    afectados = cur.rowcount
    conn.close()
    if afectados == 0:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
    # Recalcular estado del pedido
    if row:
        pedido_id = row["pedido_id"]
        detalles = query_db("SELECT surtido FROM detalle_pedido WHERE pedido_id = ?", (pedido_id,))
        todos = all(bool(d["surtido"]) for d in detalles) if detalles else False
        alguno = any(bool(d["surtido"]) for d in detalles) if detalles else False
        if todos:
            conn = get_db()
            conn.execute("UPDATE pedidos SET estado = 'LISTO' WHERE id = ?", (pedido_id,))
            conn.commit()
            conn.close()
        elif alguno:
            conn = get_db()
            conn.execute("UPDATE pedidos SET estado = 'EN_PREPARACION' WHERE id = ? AND estado = 'PENDIENTE'", (pedido_id,))
            conn.commit()
            conn.close()
    return {"ok": True, "detalle_id": detalle_id, "surtido": bool(surtido)}


# ---------- API: Mesas (para mesero) ----------
@app.get("/api/mesas")
def listar_mesas(zona: str | None = None):
    if zona:
        rows = query_db("SELECT id, zona, numero_mesa, activa FROM mesas WHERE zona = ? AND activa = 1 ORDER BY numero_mesa", (zona,))
    else:
        rows = query_db("SELECT id, zona, numero_mesa, activa FROM mesas WHERE activa = 1 ORDER BY zona, numero_mesa")
    return [dict(r) for r in rows]


# ---------- API: Admin mesas ----------
@app.get("/api/admin/mesas")
def admin_listar_mesas():
    rows = query_db("SELECT id, zona, numero_mesa, activa FROM mesas ORDER BY zona, numero_mesa")
    return [dict(r) for r in rows]


@app.post("/api/admin/mesas")
async def admin_crear_mesa(request: Request):
    data = await request.json()
    zona = (data.get("zona") or "").strip()
    numero = data.get("numero_mesa")
    if not zona or numero is None:
        raise HTTPException(status_code=400, detail="Datos incompletos")
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO mesas (zona, numero_mesa, activa) VALUES (?,?,1)", (zona, int(numero)))
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Esa mesa ya existe en esa zona")
    conn.close()
    return {"ok": True, "id": new_id}


@app.put("/api/admin/mesas/{mesa_id}/toggle")
async def admin_toggle_mesa(mesa_id: int, request: Request):
    data = await request.json()
    activa = data.get("activa")
    if activa not in (0, 1):
        raise HTTPException(status_code=400, detail="Valor inválido")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE mesas SET activa = ? WHERE id = ?", (int(activa), mesa_id))
    conn.commit()
    afectados = cur.rowcount
    conn.close()
    if afectados == 0:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    return {"ok": True, "id": mesa_id, "activa": activa}


# ---------- API: Admin menú del día ----------
@app.put("/api/admin/menu_del_dia/{platillo_id}")
async def admin_menu_del_dia(platillo_id: int, request: Request):
    data = await request.json()
    valor = data.get("es_menu_dia")
    if valor not in (0, 1):
        raise HTTPException(status_code=400, detail="Valor inválido")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE menu SET es_menu_dia = ? WHERE id = ?", (int(valor), platillo_id))
    conn.commit()
    afectados = cur.rowcount
    conn.close()
    if afectados == 0:
        raise HTTPException(status_code=404, detail="Platillo no encontrado")
    return {"ok": True, "id": platillo_id, "es_menu_dia": bool(valor)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

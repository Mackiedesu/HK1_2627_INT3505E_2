import os
import sqlite3
from flask import Flask, jsonify, request, make_response, g

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "app_bt1.db")
DUMP_PATH = os.path.join(os.path.dirname(__file__), "database.sql")

DEFAULT_SIZE, MAX_SIZE = 20, 100

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def dump_db():
    """Xuất toàn bộ schema và dữ liệu trong SQLite ra file database.sql."""
    with sqlite3.connect(DB_PATH) as conn:
        with open(DUMP_PATH, "w", encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")

def init_db():
    """Khởi tạo cấu trúc bảng và dữ liệu mẫu nếu chưa tồn tại."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 1. Bảng orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'pending',
                items TEXT,
                total_price REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Bảng books
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                isbn TEXT,
                price REAL DEFAULT 0.0
            )
        """)
        conn.commit()

        # Seed data orders nếu rỗng
        cursor.execute("SELECT COUNT(*) FROM orders")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO orders (id, status, items, total_price)
                VALUES (?, ?, ?, ?)
            """, [
                (1, "pending", "Clean Code (1x)", 29.99),
                (2, "shipped", "Clean Architecture (1x)", 34.99),
                (3, "delivered", "1984 (2x)", 25.98)
            ])
            conn.commit()

        # Seed data books nếu rỗng
        cursor.execute("SELECT COUNT(*) FROM books")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO books (id, title, author, isbn, price)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (1, "Clean Code", "Robert Martin", "978-0132350884", 29.99),
                (2, "Clean Architecture", "Robert Martin", "978-0134494166", 34.99),
                (3, "1984", "George Orwell", "978-0451524935", 12.99),
                (4, "Animal Farm", "George Orwell", "978-0451526342", 9.99)
            ])
            conn.commit()

    # Xuất dump file ban đầu
    dump_db()

# Khởi tạo DB khi load module
init_db()

# ==========================================
# NHÓM API: /orders (Refactor sang SQLite)
# ==========================================

# ─── GET /orders ─── Lấy danh sách orders
@app.get("/orders")
def list_orders():
    db = get_db()
    rows = db.execute("SELECT * FROM orders ORDER BY id ASC").fetchall()
    orders = [dict(row) for row in rows]
    return jsonify({"data": orders, "total": len(orders)}), 200

# ─── GET /orders/<oid> ─── Bổ sung theo đề bài trang 26
@app.get("/orders/<int:oid>")
def get_order(oid):
    db = get_db()
    row = db.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
    if row is None:
        return jsonify(error="order not found"), 404

    order_dict = dict(row)
    links = {
        "self": {"href": f"/orders/{oid}"}
    }
    # HATEOAS: Nếu trạng thái là pending thì có thể cancel/xóa
    if order_dict["status"] == "pending":
        links["cancel"] = {"href": f"/orders/{oid}", "method": "DELETE"}

    order_dict["_links"] = links
    return jsonify(order_dict), 200

# ─── POST /orders ─── Tạo đơn hàng mới
@app.post("/orders")
def create_order():
    if not request.is_json:
        return jsonify(error="expected JSON"), 415

    payload = request.get_json() or {}
    items = payload.get("items", "Custom Order")
    price = float(payload.get("total_price", 0.0))
    status = payload.get("status", "pending")

    db = get_db()
    cursor = db.execute(
        "INSERT INTO orders (status, items, total_price) VALUES (?, ?, ?)",
        (status, items, price)
    )
    db.commit()
    dump_db()

    oid = cursor.lastrowid
    row = db.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
    resp = make_response(jsonify(dict(row)), 201)
    resp.headers["Location"] = f"/orders/{oid}"
    return resp

# ─── DELETE /orders/<oid> ─── Hợp đồng xoá với 404, 409, 204
@app.delete("/orders/<int:oid>")
def delete_order(oid):
    db = get_db()
    row = db.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
    if row is None:
        return jsonify(error="order not found"), 404

    # 409 Conflict: Không cho phép xoá nếu đơn hàng đã shipped hoặc delivered
    if row["status"] in ("shipped", "delivered"):
        return jsonify(error="cannot delete order in current state"), 409

    db.execute("DELETE FROM orders WHERE id = ?", (oid,))
    db.commit()
    dump_db()
    return "", 204

# ==========================================
# NHÓM API: /books (Refactor sang SQLite)
# ==========================================

# ─── GET /books ─── Phân trang + Lọc + HATEOAS + Cache-Control
@app.get("/books")
def list_books():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", DEFAULT_SIZE))
    except ValueError:
        return jsonify(error="page and size must be int"), 400

    page = max(page, 1)
    size = max(min(size, MAX_SIZE), 1)

    author = request.args.get("author")
    q = request.args.get("q")

    query = "SELECT * FROM books WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM books WHERE 1=1"
    params = []

    if author:
        query += " AND (LOWER(author) = LOWER(?) OR LOWER(author) LIKE LOWER(?))"
        count_query += " AND (LOWER(author) = LOWER(?) OR LOWER(author) LIKE LOWER(?))"
        params.extend([author, f"%{author}%"])
    if q:
        query += " AND LOWER(title) LIKE LOWER(?)"
        count_query += " AND LOWER(title) LIKE LOWER(?)"
        params.append(f"%{q}%")

    db = get_db()
    total = db.execute(count_query, params).fetchone()[0]

    offset = (page - 1) * size
    query += " ORDER BY id ASC LIMIT ? OFFSET ?"
    query_params = params + [size, offset]
    rows = db.execute(query, query_params).fetchall()
    items = [dict(row) for row in rows]
    last = (total + size - 1) // size if total > 0 else 1

    def u(p):
        base = f"/books?page={p}&size={size}"
        if author:
            base += f"&author={author}"
        if q:
            base += f"&q={q}"
        return base

    links = {
        "self": {"href": u(page)},
        "first": {"href": u(1)},
        "last": {"href": u(max(last, 1))}
    }
    if page > 1:
        links["prev"] = {"href": u(page - 1)}
    if offset + len(items) < total:
        links["next"] = {"href": u(page + 1)}

    body = {
        "data": items,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": last
        },
        "_links": links
    }
    resp = make_response(jsonify(body), 200)
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp

# ─── GET /books/<id> ─── Chi tiết sách + Cache 60s
@app.get("/books/<int:bid>")
def get_book(bid):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
    if row is None:
        return jsonify(error="not found"), 404

    resp = make_response(jsonify(dict(row)), 200)
    resp.headers["Cache-Control"] = "max-age=60"
    return resp

# ─── POST /books ─── Tạo sách mới
@app.post("/books")
def create_book():
    if not request.is_json:
        return jsonify(error="expected JSON"), 415

    payload = request.get_json() or {}
    title = (payload.get("title") or "").strip()
    author = (payload.get("author") or "").strip()

    if not title or not author:
        return jsonify(error="title and author required"), 422

    isbn = payload.get("isbn")
    price = payload.get("price", 0.0)

    db = get_db()
    cursor = db.execute(
        "INSERT INTO books (title, author, isbn, price) VALUES (?, ?, ?, ?)",
        (title, author, isbn, price)
    )
    db.commit()
    dump_db()

    bid = cursor.lastrowid
    row = db.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
    resp = make_response(jsonify(dict(row)), 201)
    resp.headers["Location"] = f"/books/{bid}"
    return resp

# ─── PUT /books/<id> ─── Thay toàn bộ thông tin sách
@app.put("/books/<int:bid>")
def put_book(bid):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
    if row is None:
        return jsonify(error="not found"), 404

    payload = request.get_json() or {}
    title = (payload.get("title") or "").strip()
    author = (payload.get("author") or "").strip()
    if not title or not author:
        return jsonify(error="need title+author"), 422

    isbn = payload.get("isbn")
    price = payload.get("price")

    db.execute(
        "UPDATE books SET title = ?, author = ?, isbn = ?, price = ? WHERE id = ?",
        (title, author, isbn, price, bid)
    )
    db.commit()
    dump_db()

    updated = db.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
    return jsonify(dict(updated)), 200

# ─── PATCH /books/<id> ─── Cập nhật từng field
@app.patch("/books/<int:bid>")
def patch_book(bid):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
    if row is None:
        return jsonify(error="not found"), 404

    payload = request.get_json() or {}
    if "price" in payload and payload["price"] < 0:
        return jsonify(error="price must be positive"), 422

    fields = []
    values = []
    for field in ["title", "author", "isbn", "price"]:
        if field in payload:
            fields.append(f"{field} = ?")
            values.append(payload[field])

    if fields:
        values.append(bid)
        db.execute(f"UPDATE books SET {', '.join(fields)} WHERE id = ?", values)
        db.commit()
        dump_db()

    updated = db.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
    return jsonify(dict(updated)), 200

# ─── DELETE /books/<id> ─── Xoá sách
@app.delete("/books/<int:bid>")
def delete_book(bid):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
    if row is None:
        return jsonify(error="not found"), 404

    db.execute("DELETE FROM books WHERE id = ?", (bid,))
    db.commit()
    dump_db()
    return "", 204

if __name__ == "__main__":
    app.run(debug=True)

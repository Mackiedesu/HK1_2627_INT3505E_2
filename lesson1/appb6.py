from flask import Flask, jsonify, request

app = Flask(__name__)

_next_id = 2
BOOKS = [
    {"id": 1, "title": "Clean Code", "author": "R. Martin"}
]

def find_book(bid):
    return next((b for b in BOOKS if b["id"] == bid), None)

# 1. LIST - GET /books
@app.route("/books", methods=["GET"])
def list_books():
    limit = int(request.args.get("limit", 100))
    return jsonify(BOOKS[:limit]), 200

# 2. DETAIL - GET /books/<int:bid>
@app.route("/books/<int:bid>", methods=["GET"])
def get_book(bid):
    book = find_book(bid)
    if not book:
        return jsonify({"error": "not found"}), 404
    return jsonify(book), 200

# 3. CREATE - POST /books
@app.route("/books", methods=["POST"])
def create_book():
    global _next_id
    body = request.get_json(silent=True) or {}
    title = body.get("title")
    author = body.get("author")

    if not title or not author:
        return jsonify({"error": "title and author are required"}), 400

    book = {"id": _next_id, "title": title, "author": author}
    _next_id += 1
    BOOKS.append(book)
    return jsonify(book), 201, {"Location": f"/books/{book['id']}"}

# 4 & 5. UPDATE (PUT) & DELETE - /books/<int:bid>
@app.route("/books/<int:bid>", methods=["PUT", "DELETE"])
def modify_book(bid):
    book = find_book(bid)
    if not book:
        return jsonify({"error": "not found"}), 404

    if request.method == "PUT":
        body = request.get_json(silent=True) or {}
        book.update(body)
        return jsonify(book), 200

    # request.method == "DELETE"
    BOOKS.remove(book)
    return "", 204

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
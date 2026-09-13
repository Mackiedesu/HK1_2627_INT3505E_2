from flask import Flask, jsonify, request

app = Flask(__name__)

BOOKS = [
    {"id": 1, "title": "Clean Code", "author": "R. Martin"},
    {"id": 2, "title": "Pragmatic Programmer", "author": "Andy Hunt"},
]

# Query params: GET /books?limit=10&q=code
@app.route("/books", methods=["GET"])
def list_books():
    limit = int(request.args.get("limit", 20))
    q = request.args.get("q", "").strip().lower()
    
    items = [b for b in BOOKS if q in b["title"].lower()]
    return jsonify({"items": items[:limit]}), 200

# Path params: GET /books/<int:book_id>
@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    book = next((b for b in BOOKS if b["id"] == book_id), None)
    if book is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(book), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
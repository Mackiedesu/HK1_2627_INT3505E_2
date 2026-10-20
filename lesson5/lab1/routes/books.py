import json
import os
from flask import Blueprint, request, jsonify, abort
from jsonschema import validate, ValidationError
from sqlalchemy import select, func
from models import db, Book, Author, BookAuthor, Review, User

books_bp = Blueprint("books", __name__)

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas", "book.json")
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA = json.load(f)


@books_bp.get("")
@books_bp.get("/")
def list_books():
    """List books with offset/limit pagination, filtering, and field selection (Slide 20, 26, 27)."""
    offset = request.args.get("offset", 0, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    q = select(Book)
    count_q = select(func.count(Book.id))

    # Filters
    category = request.args.get("category", type=int) or request.args.get("category_id", type=int)
    if category is not None:
        q = q.filter(Book.category_id == category)
        count_q = count_q.filter(Book.category_id == category)

    in_stock = request.args.get("in_stock")
    if in_stock is not None:
        if in_stock.lower() in ("true", "1", "yes"):
            q = q.filter(Book.stock > 0)
            count_q = count_q.filter(Book.stock > 0)
        elif in_stock.lower() in ("false", "0", "no"):
            q = q.filter(Book.stock == 0)
            count_q = count_q.filter(Book.stock == 0)

    price_min = request.args.get("price_min", type=int)
    if price_min is not None:
        q = q.filter(Book.price_vnd >= price_min)
        count_q = count_q.filter(Book.price_vnd >= price_min)

    price_max = request.args.get("price_max", type=int)
    if price_max is not None:
        q = q.filter(Book.price_vnd <= price_max)
        count_q = count_q.filter(Book.price_vnd <= price_max)

    total = db.session.scalar(count_q)
    rows = db.session.scalars(q.order_by(Book.id).offset(offset).limit(limit)).all()

    # Field selection (sparse fieldsets)
    fields_raw = request.args.get("fields")
    fields = [f.strip() for f in fields_raw.split(",") if f.strip()] if fields_raw else None

    return jsonify({
        "data": [b.to_dict(fields=fields) for b in rows],
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_next": (offset + limit) < total
        }
    }), 200


@books_bp.post("")
@books_bp.post("/")
def create_book():
    """Create a new book with JSON Schema validation (Slide 15)."""
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "message": "Request body must be valid JSON"}), 400

    try:
        validate(payload, SCHEMA)
    except ValidationError as e:
        return jsonify({
            "error": "validation_failed",
            "field": list(e.path),
            "message": e.message
        }), 400

    book = Book.from_payload(payload)
    db.session.add(book)
    db.session.flush()

    # Associate authors if provided
    if "authors" in payload and isinstance(payload["authors"], list):
        for a_item in payload["authors"]:
            aid = a_item.get("id")
            if aid and db.session.get(Author, aid):
                ba = BookAuthor(
                    book_id=book.id,
                    author_id=aid,
                    role=a_item.get("role", "co")
                )
                db.session.add(ba)

    db.session.commit()
    return jsonify(book.to_dict()), 201


@books_bp.get("/<int:bid>")
def get_book(bid):
    """Retrieve details for a single book by ID."""
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    fields_raw = request.args.get("fields")
    fields = [f.strip() for f in fields_raw.split(",") if f.strip()] if fields_raw else None
    return jsonify(book.to_dict(fields=fields)), 200


@books_bp.put("/<int:bid>")
def update_book(bid):
    """Update book information."""
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    payload = request.get_json(silent=True) or {}
    if "title" in payload:
        book.title = payload["title"]
    if "isbn" in payload:
        book.isbn = payload["isbn"]
    if "price" in payload:
        pval = payload["price"]
        if isinstance(pval, dict):
            book.price_vnd = pval.get("amount", book.price_vnd)
        elif isinstance(pval, (int, float)):
            book.price_vnd = int(pval)
    elif "price_vnd" in payload:
        book.price_vnd = payload["price_vnd"]

    if "stock" in payload:
        book.stock = payload["stock"]
    if "category_id" in payload:
        book.category_id = payload["category_id"]
    if "publishedAt" in payload or "published_at" in payload:
        book.published_at = payload.get("publishedAt") or payload.get("published_at")

    db.session.commit()
    return jsonify(book.to_dict()), 200


@books_bp.delete("/<int:bid>")
def delete_book(bid):
    """Delete a book by ID."""
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    db.session.delete(book)
    db.session.commit()
    return "", 204


# --- N:M Association: Nested + pair ID (Slide 11) ---

@books_bp.post("/<int:bid>/authors")
def add_author(bid):
    """Add author to book with role metadata (Slide 11)."""
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    req = request.get_json(silent=True) or {}
    if "author_id" not in req:
        abort(400, description="author_id is required")

    author_id = req["author_id"]
    author = db.session.get(Author, author_id)
    if not author:
        return jsonify({"error": "not_found", "message": f"Author with id {author_id} not found"}), 404

    existing = db.session.query(BookAuthor).filter_by(book_id=bid, author_id=author_id).first()
    if existing:
        existing.role = req.get("role", existing.role)
        db.session.commit()
        return jsonify(existing.to_dict()), 200

    p = BookAuthor(
        book_id=bid,
        author_id=author_id,
        role=req.get("role", "co")
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@books_bp.get("/<int:bid>/authors")
def list_authors(bid):
    """List authors for a book with role (Slide 11)."""
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    rows = (
        db.session.query(Author, BookAuthor.role)
        .join(Author, Author.id == BookAuthor.author_id)
        .filter(BookAuthor.book_id == bid)
        .all()
    )
    return jsonify([
        {"id": a.id, "name": a.name, "role": r}
        for a, r in rows
    ]), 200


@books_bp.delete("/<int:bid>/authors/<int:aid>")
def remove_author(bid, aid):
    """Remove an author from a book (Slide 11)."""
    deleted = db.session.query(BookAuthor).filter_by(book_id=bid, author_id=aid).delete()
    if not deleted:
        return jsonify({"error": "not_found", "message": "Author association not found"}), 404
    db.session.commit()
    return "", 204


# --- 1:N Sub-resource: Reviews (Slide 9 & 12) ---

@books_bp.get("/<int:bid>/reviews")
def list_book_reviews(bid):
    """List reviews for a book (Slide 9 - Pattern A)."""
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    reviews = db.session.query(Review).filter_by(book_id=bid).order_by(Review.id.desc()).all()
    return jsonify([r.to_dict() for r in reviews]), 200


@books_bp.post("/<int:bid>/reviews")
def create_book_review(bid):
    """Create review for a book (Slide 9 - Pattern A)."""
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    req = request.get_json(silent=True) or {}
    rating = req.get("rating")
    user_id = req.get("user_id")

    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "validation_failed", "message": "rating must be an integer between 1 and 5"}), 400

    if not user_id:
        return jsonify({"error": "validation_failed", "message": "user_id is required"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "not_found", "message": f"User with id {user_id} not found"}), 404

    review = Review(
        rating=rating,
        comment=req.get("comment", ""),
        book_id=bid,
        user_id=user_id
    )
    db.session.add(review)
    db.session.commit()
    return jsonify(review.to_dict()), 201

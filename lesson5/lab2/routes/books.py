import base64
import json
import os
from flask import Blueprint, request, jsonify, abort
from jsonschema import validate, ValidationError
from sqlalchemy import select, func, tuple_, or_
from models import db, Book, Author, BookAuthor, Category, Review, User

books_bp = Blueprint("books", __name__)

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas", "book.json")
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA = json.load(f)

# Whitelist sort columns to prevent SQL Injection (Slide 23 & 26)
SORT = {
    "id": Book.id,
    "price": Book.price_vnd,
    "title": Book.title,
    "stock": Book.stock
}


# =====================================================================
# Phase 1 & 2 Helpers for Cursor Pagination (Slide 23 & 24)
# =====================================================================

def _enc(s: dict) -> str:
    """Base64 urlsafe encode JSON payload without padding (Slide 24)."""
    return base64.urlsafe_b64encode(
        json.dumps(s).encode("utf-8")
    ).decode("utf-8").rstrip("=")


def _dec(raw: str) -> dict:
    """Base64 urlsafe decode cursor string with padding restoration."""
    pad = "=" * (-len(raw) % 4)
    return json.loads(
        base64.urlsafe_b64decode((raw + pad).encode("utf-8"))
    )


def parse_sort(raw: str):
    """
    Parse sort parameter against whitelist (Slide 23 & 29).
    Supports single key ('price', '-price', '-id') and multi-key ('-price,id').
    Returns: (primary_col, order_by_cols, desc_bool) or (None, 'bad_sort', 400).
    """
    if not raw:
        raw = "-id"

    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return None, "bad_sort", 400

    cols = []
    primary_p = None
    primary_desc = False

    for idx, part in enumerate(parts):
        desc = part.startswith("-")
        key = part.lstrip("-")
        if key not in SORT:
            return None, "bad_sort", 400

        col_attr = SORT[key]
        if idx == 0:
            primary_p = col_attr
            primary_desc = desc

        cols.append(col_attr.desc() if desc else col_attr.asc())

    # Ensure tie-break by Book.id is present
    has_id_col = any(c.element is Book.id for c in cols if hasattr(c, "element"))
    if not has_id_col:
        cols.append(Book.id.desc() if primary_desc else Book.id.asc())

    return primary_p, cols, primary_desc


def apply_cursor(q, raw: str, sort: str, p, desc: bool):
    """
    Validate and apply cursor filtering with composite key (Slide 24).
    WHERE (sort_col, id) < (val, id) when desc else > (val, id).
    """
    if not raw:
        return q, None, 200

    try:
        c = _dec(raw)
    except Exception:
        return None, "bad_cursor", 400

    if not isinstance(c, dict) or "s" not in c or "v" not in c or "i" not in c:
        return None, "bad_cursor", 400

    # Ensure cursor matches the requested sort
    if c.get("s") != sort:
        return None, "sort_chg", 400

    v, i = c["v"], c["i"]
    op = "<" if desc else ">"

    # Composite comparison: (sort_col, id) op (v, i)
    condition = tuple_(p, Book.id).op(op)((v, i))
    return q.filter(condition), None, 200


def build_response(items, lim: int, sort: str, p, more: bool, fields=None):
    """Format cursor pagination response (Slide 24)."""
    nxt = None
    if items and more:
        last = items[-1]
        nxt = _enc({
            "s": sort,
            "v": getattr(last, p.key),
            "i": last.id
        })

    return jsonify({
        "data": [b.to_dict(fields=fields) for b in items],
        "page": {
            "next": nxt,
            "more": more
        }
    }), 200


# =====================================================================
# Books Routes (Slide 20, 25, 29)
# =====================================================================

@books_bp.get("")
@books_bp.get("/")
def list_books():
    """
    List books endpoint supporting:
    - ?strategy=cursor (default) or ?strategy=offset (Slide 29)
    - Filter by ?category=..., ?genre=..., ?in_stock=..., ?price_min=..., ?price_max=...
    - Sort whitelist: ?sort=-price, ?sort=price, ?sort=-id
    - Sparse fieldsets: ?fields=id,title,price
    """
    strategy = request.args.get("strategy")
    raw_cursor = request.args.get("cursor")
    if not strategy:
        strategy = "cursor"

    # Common query & filtering
    q = select(Book)
    count_q = select(func.count(Book.id))

    # Filter: Category ID
    cat_id = request.args.get("category", type=int) or request.args.get("category_id", type=int)
    if cat_id is not None:
        q = q.filter(Book.category_id == cat_id)
        count_q = count_q.filter(Book.category_id == cat_id)

    # Filter: Genre (Category name or slug) - Slide 29
    genre = request.args.get("genre")
    if genre:
        q = q.join(Category).filter(
            or_(Category.slug == genre.lower(), Category.name.ilike(genre))
        )
        count_q = count_q.join(Category).filter(
            or_(Category.slug == genre.lower(), Category.name.ilike(genre))
        )

    # Filter: in_stock
    in_stock = request.args.get("in_stock")
    if in_stock is not None:
        if in_stock.lower() in ("true", "1", "yes"):
            q = q.filter(Book.stock > 0)
            count_q = count_q.filter(Book.stock > 0)
        elif in_stock.lower() in ("false", "0", "no"):
            q = q.filter(Book.stock == 0)
            count_q = count_q.filter(Book.stock == 0)

    # Filter: price range
    p_min = request.args.get("price_min", type=int)
    if p_min is not None:
        q = q.filter(Book.price_vnd >= p_min)
        count_q = count_q.filter(Book.price_vnd >= p_min)

    p_max = request.args.get("price_max", type=int)
    if p_max is not None:
        q = q.filter(Book.price_vnd <= p_max)
        count_q = count_q.filter(Book.price_vnd <= p_max)

    # Field selection
    fields_raw = request.args.get("fields")
    fields = [f.strip() for f in fields_raw.split(",") if f.strip()] if fields_raw else None

    # Limit
    lim = min(request.args.get("limit", 20, type=int), 100)

    # Strategy 1: Offset / Limit Pagination (Slide 20)
    if strategy == "offset":
        offset = request.args.get("offset", 0, type=int)
        sort_raw = request.args.get("sort", "-id")
        p, cols, _ = parse_sort(sort_raw)
        if p is None:
            return jsonify({"error": "bad_sort", "message": f"Invalid sort key '{sort_raw}'"}), 400

        total = db.session.scalar(count_q)
        rows = db.session.scalars(q.order_by(*cols).offset(offset).limit(lim)).all()

        return jsonify({
            "data": [b.to_dict(fields=fields) for b in rows],
            "pagination": {
                "offset": offset,
                "limit": lim,
                "total": total,
                "has_next": (offset + lim) < total
            }
        }), 200

    # Strategy 2: Cursor Pagination (Slide 23, 24, 25)
    sort_raw = request.args.get("sort", "-id")
    p, cols, desc = parse_sort(sort_raw)
    if p is None:
        return jsonify({"error": "bad_sort", "message": f"Invalid sort key '{sort_raw}'"}), 400

    q = q.order_by(*cols)

    # Apply cursor
    q, err, code = apply_cursor(q, raw_cursor, sort_raw, p, desc)
    if err:
        return jsonify({"error": err, "message": f"Cursor error: {err}"}), code

    # +1 trick to check if there is a next page
    rows = db.session.scalars(q.limit(lim + 1)).all()
    has_more = len(rows) > lim
    page_items = rows[:lim]

    return build_response(page_items, lim, sort_raw, p, has_more, fields=fields)


@books_bp.post("")
@books_bp.post("/")
def create_book():
    """Create book with JSON Schema validation (Slide 15)."""
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
    """Retrieve book by ID."""
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    fields_raw = request.args.get("fields")
    fields = [f.strip() for f in fields_raw.split(",") if f.strip()] if fields_raw else None
    return jsonify(book.to_dict(fields=fields)), 200


@books_bp.put("/<int:bid>")
def update_book(bid):
    """Update book by ID."""
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
    """Delete book by ID."""
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    db.session.delete(book)
    db.session.commit()
    return "", 204


# --- N:M Association: Nested + pair (Slide 11) ---

@books_bp.post("/<int:bid>/authors")
def add_author(bid):
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
    deleted = db.session.query(BookAuthor).filter_by(book_id=bid, author_id=aid).delete()
    if not deleted:
        return jsonify({"error": "not_found", "message": "Author association not found"}), 404
    db.session.commit()
    return "", 204


# --- 1:N Sub-resource: Reviews (Slide 9 & 12) ---

@books_bp.get("/<int:bid>/reviews")
def list_book_reviews(bid):
    book = db.session.get(Book, bid)
    if not book:
        return jsonify({"error": "not_found", "message": f"Book with id {bid} not found"}), 404

    reviews = db.session.query(Review).filter_by(book_id=bid).order_by(Review.id.desc()).all()
    return jsonify([r.to_dict() for r in reviews]), 200


@books_bp.post("/<int:bid>/reviews")
def create_book_review(bid):
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

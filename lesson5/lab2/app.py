import os
import sys
from flask import Flask, jsonify, request
from sqlalchemy import select, func

# Ensure local module imports work regardless of execution directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models import db, Book, Author, BookAuthor, Category, Review, User, Order, OrderItem
from routes.books import books_bp


def create_app():
    app = Flask(__name__)
    db_path = os.path.join(BASE_DIR, "bookstore.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.json.sort_keys = False

    db.init_app(app)

    # Register Blueprint for Books API
    app.register_blueprint(books_bp, url_prefix="/api/v1/books")

    @app.get("/")
    def index():
        return jsonify({
            "message": "Welcome to Bookstore API - Lab 2 (Cursor & Offset Pagination)",
            "documentation": {
                "books": "/api/v1/books",
                "authors": "/api/v1/authors",
                "categories": "/api/v1/categories",
                "reviews": "/api/v1/reviews",
                "users": "/api/v1/users"
            },
            "pagination_examples": {
                "cursor_default": "/api/v1/books?limit=3",
                "cursor_sort_price_desc": "/api/v1/books?sort=-price&limit=3",
                "cursor_sort_price_asc": "/api/v1/books?sort=price&limit=3",
                "filter_genre": "/api/v1/books?genre=tech&limit=3",
                "offset_strategy": "/api/v1/books?strategy=offset&offset=0&limit=3"
            }
        })

    # Extra helper endpoints
    @app.get("/api/v1/categories")
    def list_categories():
        categories = db.session.scalars(select(Category)).all()
        return jsonify([c.to_dict() for c in categories])

    @app.post("/api/v1/categories")
    def create_category():
        data = request.get_json(silent=True) or {}
        if not data.get("name") or not data.get("slug"):
            return jsonify({"error": "validation_failed", "message": "name and slug are required"}), 400
        cat = Category(name=data["name"], slug=data["slug"])
        db.session.add(cat)
        db.session.commit()
        return jsonify(cat.to_dict()), 201

    @app.get("/api/v1/authors")
    def list_all_authors():
        authors = db.session.scalars(select(Author)).all()
        return jsonify([a.to_dict() for a in authors])

    @app.post("/api/v1/authors")
    def create_author():
        data = request.get_json(silent=True) or {}
        if not data.get("name"):
            return jsonify({"error": "validation_failed", "message": "name is required"}), 400
        author = Author(name=data["name"], bio=data.get("bio", ""))
        db.session.add(author)
        db.session.commit()
        return jsonify(author.to_dict()), 201

    @app.get("/api/v1/authors/<int:aid>/books")
    def list_books_by_author(aid):
        author = db.session.get(Author, aid)
        if not author:
            return jsonify({"error": "not_found", "message": f"Author {aid} not found"}), 404
        book_ids = [ba.book_id for ba in author.book_authors]
        books = db.session.scalars(select(Book).filter(Book.id.in_(book_ids))).all() if book_ids else []
        return jsonify([b.to_dict() for b in books])

    @app.get("/api/v1/reviews")
    def list_all_reviews():
        book_id = request.args.get("book_id", type=int)
        user_id = request.args.get("user_id", type=int)
        rating = request.args.get("rating", type=int)

        q = select(Review)
        if book_id is not None:
            q = q.filter(Review.book_id == book_id)
        if user_id is not None:
            q = q.filter(Review.user_id == user_id)
        if rating is not None:
            q = q.filter(Review.rating == rating)

        reviews = db.session.scalars(q).all()
        return jsonify([r.to_dict() for r in reviews])

    @app.get("/api/v1/users")
    def list_users():
        users = db.session.scalars(select(User)).all()
        return jsonify([u.to_dict() for u in users])

    @app.post("/api/v1/users")
    def create_user():
        data = request.get_json(silent=True) or {}
        if not data.get("email") or not data.get("display_name"):
            return jsonify({"error": "validation_failed", "message": "email and display_name are required"}), 400
        user = User(
            email=data["email"],
            display_name=data["display_name"],
            password_hash="hashed_secret_example"
        )
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201

    return app


def init_database(app):
    """Create tables and seed initial rich dataset for pagination testing."""
    with app.app_context():
        db.create_all()

        if db.session.scalar(select(func.count(Category.id))) == 0:
            tech = Category(name="Technology", slug="tech")
            scifi = Category(name="Science Fiction", slug="sci-fi")
            lit = Category(name="Literature", slug="literature")
            db.session.add_all([tech, scifi, lit])
            db.session.commit()

            a1 = Author(name="Robert C. Martin", bio="Author of Clean Code")
            a2 = Author(name="Martin Fowler", bio="Author of Refactoring")
            a3 = Author(name="Martin Kleppmann", bio="Author of Designing Data-Intensive Applications")
            a4 = Author(name="Frank Herbert", bio="Author of Dune")
            a5 = Author(name="George Orwell", bio="Author of 1984")
            db.session.add_all([a1, a2, a3, a4, a5])
            db.session.commit()

            u1 = User(email="an.nguyen@example.com", display_name="An Nguyen", password_hash="secret_hash_1")
            u2 = User(email="binh.tran@example.com", display_name="Binh Tran", password_hash="secret_hash_2")
            db.session.add_all([u1, u2])
            db.session.commit()

            books = [
                Book(title="Clean Code", isbn="9780132350884", price_vnd=450000, stock=14, category_id=tech.id, published_at="2008-08-01"),
                Book(title="Refactoring", isbn="9780201485677", price_vnd=520000, stock=8, category_id=tech.id, published_at="2018-11-20"),
                Book(title="Designing Data-Intensive Applications", isbn="9781449373320", price_vnd=650000, stock=20, category_id=tech.id, published_at="2017-03-16"),
                Book(title="The Pragmatic Programmer", isbn="9780201616224", price_vnd=480000, stock=12, category_id=tech.id, published_at="1999-10-30"),
                Book(title="Dune", isbn="9780441172719", price_vnd=320000, stock=25, category_id=scifi.id, published_at="1965-08-01"),
                Book(title="Neuromancer", isbn="9780441569595", price_vnd=280000, stock=5, category_id=scifi.id, published_at="1984-07-01"),
                Book(title="Foundation", isbn="9780553293357", price_vnd=310000, stock=15, category_id=scifi.id, published_at="1951-05-01"),
                Book(title="1984", isbn="9780451524935", price_vnd=210000, stock=30, category_id=lit.id, published_at="1949-06-08"),
                Book(title="To Kill a Mockingbird", isbn="9780061120084", price_vnd=190000, stock=18, category_id=lit.id, published_at="1960-07-11"),
                Book(title="The Great Gatsby", isbn="9780743273565", price_vnd=180000, stock=0, category_id=lit.id, published_at="1925-04-10")
            ]
            db.session.add_all(books)
            db.session.commit()

            # Associations
            pairs = [
                (books[0].id, a1.id, "lead"),
                (books[1].id, a2.id, "lead"),
                (books[2].id, a3.id, "lead"),
                (books[4].id, a4.id, "lead"),
                (books[7].id, a5.id, "lead")
            ]
            for bid, aid, role in pairs:
                db.session.add(BookAuthor(book_id=bid, author_id=aid, role=role))
            db.session.commit()

            # Reviews
            r1 = Review(rating=5, comment="A classic for craftsmen", book_id=books[0].id, user_id=u1.id)
            r2 = Review(rating=4, comment="Fundamental concepts", book_id=books[1].id, user_id=u2.id)
            db.session.add_all([r1, r2])
            db.session.commit()


app = create_app()
init_database(app)

if __name__ == "__main__":
    app.run(debug=True, port=5000)

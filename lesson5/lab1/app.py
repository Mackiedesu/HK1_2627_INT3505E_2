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

    # Register Blueprint for Books
    app.register_blueprint(books_bp, url_prefix="/api/v1/books")

    # API Index
    @app.get("/")
    def index():
        return jsonify({
            "message": "Welcome to Bookstore API (Lesson 5 - Lab 1)",
            "documentation": {
                "books": "/api/v1/books",
                "authors": "/api/v1/authors",
                "categories": "/api/v1/categories",
                "reviews": "/api/v1/reviews",
                "users": "/api/v1/users"
            }
        })

    # Extra helper endpoints for complete entity management
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
        # Pattern B: Top-level with filter (Slide 9)
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
            password_hash="hashed_secret_example"  # In production: hash password
        )
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201

    return app


def init_database(app):
    """Create tables and seed initial demo data if empty."""
    with app.app_context():
        db.create_all()

        # Seed data if empty
        if db.session.scalar(select(func.count(Category.id))) == 0:
            tech_cat = Category(name="Technology", slug="tech")
            scifi_cat = Category(name="Science Fiction", slug="sci-fi")
            lit_cat = Category(name="Literature", slug="literature")
            db.session.add_all([tech_cat, scifi_cat, lit_cat])
            db.session.commit()

            author1 = Author(name="R.C. Martin", bio="Software engineer, author of Clean Code")
            author2 = Author(name="Martin Fowler", bio="Chief Scientist at ThoughtWorks, author of Refactoring")
            db.session.add_all([author1, author2])
            db.session.commit()

            user1 = User(
                email="an.nguyen@example.com",
                display_name="An Nguyen",
                password_hash="argon2_hashed_secret"
            )
            db.session.add(user1)
            db.session.commit()

            book1 = Book(
                title="Clean Code",
                isbn="9780132350884",
                price_vnd=450000,
                stock=14,
                category_id=tech_cat.id,
                published_at="2008-08-01"
            )
            book2 = Book(
                title="Refactoring",
                isbn="9780201485677",
                price_vnd=520000,
                stock=8,
                category_id=tech_cat.id,
                published_at="2018-11-20"
            )
            db.session.add_all([book1, book2])
            db.session.commit()

            ba1 = BookAuthor(book_id=book1.id, author_id=author1.id, role="lead")
            ba2 = BookAuthor(book_id=book2.id, author_id=author2.id, role="lead")
            db.session.add_all([ba1, ba2])
            db.session.commit()

            rev1 = Review(
                rating=5,
                comment="A timeless classic for all software developers.",
                book_id=book1.id,
                user_id=user1.id
            )
            db.session.add(rev1)
            db.session.commit()


app = create_app()
init_database(app)

if __name__ == "__main__":
    app.run(debug=True, port=5000)

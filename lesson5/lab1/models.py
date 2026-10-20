from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import mapped_column, relationship

db = SQLAlchemy()


class Book(db.Model):
    __tablename__ = "books"

    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(String(200), nullable=False)
    isbn = mapped_column(String(13), unique=True, nullable=True)
    price_vnd = mapped_column(Integer, nullable=False, default=0)
    stock = mapped_column(Integer, default=0)
    category_id = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    published_at = mapped_column(String(50), nullable=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    category = relationship("Category", back_populates="books")
    book_authors = relationship("BookAuthor", back_populates="book", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="book", cascade="all, delete-orphan")

    def __init__(
        self,
        title=None,
        isbn=None,
        price_vnd=0,
        stock=0,
        category_id=None,
        published_at=None,
        **kwargs
    ):
        self.title = title
        self.isbn = isbn
        self.price_vnd = price_vnd
        self.stock = stock
        self.category_id = category_id
        self.published_at = published_at
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def from_payload(cls, payload):
        """Construct a Book model instance from API payload."""
        price_val = payload.get("price")
        if isinstance(price_val, dict):
            price_amount = price_val.get("amount", 0)
        elif isinstance(price_val, (int, float)):
            price_amount = int(price_val)
        else:
            price_amount = payload.get("price_vnd", 0)

        return cls(
            title=payload.get("title"),
            isbn=payload.get("isbn"),
            price_vnd=price_amount,
            stock=payload.get("stock", 0),
            category_id=payload.get("category_id"),
            published_at=payload.get("publishedAt") or payload.get("published_at")
        )

    def to_dict(self, fields=None):
        """Convert Book instance to API presentation format (Slide 13)."""
        authors_data = []
        for ba in self.book_authors:
            if ba.author:
                authors_data.append({
                    "id": ba.author.id,
                    "name": ba.author.name,
                    "role": ba.role
                })

        category_data = None
        if self.category:
            category_data = {
                "id": self.category.id,
                "name": self.category.name,
                "slug": self.category.slug
            }

        created_at_str = None
        if self.created_at:
            created_at_str = self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        full = {
            "id": f"book_{self.id}",
            "title": self.title,
            "isbn": self.isbn,
            "category": category_data,
            "authors": authors_data,
            "price": {
                "amount": self.price_vnd,
                "currency": "VND"
            },
            "inStock": self.stock > 0,
            "stock": self.stock,
            "publishedAt": self.published_at,
            "createdAt": created_at_str
        }

        if fields is None:
            return full
        return {k: v for k, v in full.items() if k in fields}


class Author(db.Model):
    __tablename__ = "authors"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(100), nullable=False)
    bio = mapped_column(Text, nullable=True)

    book_authors = relationship("BookAuthor", back_populates="author", cascade="all, delete-orphan")

    def __init__(self, name=None, bio=None, **kwargs):
        self.name = name
        self.bio = bio
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bio": self.bio
        }


class BookAuthor(db.Model):
    __tablename__ = "book_authors"

    id = mapped_column(Integer, primary_key=True)
    book_id = mapped_column(Integer, ForeignKey("books.id"), nullable=False)
    author_id = mapped_column(Integer, ForeignKey("authors.id"), nullable=False)
    role = mapped_column(String(50), default="co")  # lead, co, ed

    book = relationship("Book", back_populates="book_authors")
    author = relationship("Author", back_populates="book_authors")

    def __init__(self, book_id=None, author_id=None, role="co", **kwargs):
        self.book_id = book_id
        self.author_id = author_id
        self.role = role
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return {
            "id": self.id,
            "book_id": self.book_id,
            "author_id": self.author_id,
            "role": self.role
        }


class Category(db.Model):
    __tablename__ = "categories"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(100), nullable=False)
    slug = mapped_column(String(100), unique=True, nullable=False)

    books = relationship("Book", back_populates="category")

    def __init__(self, name=None, slug=None, **kwargs):
        self.name = name
        self.slug = slug
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug
        }


class Review(db.Model):
    __tablename__ = "reviews"

    id = mapped_column(Integer, primary_key=True)
    rating = mapped_column(Integer, nullable=False)  # 1 - 5 sao
    comment = mapped_column(Text, nullable=True)
    book_id = mapped_column(Integer, ForeignKey("books.id"), nullable=False)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    book = relationship("Book", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

    def __init__(self, rating=None, comment=None, book_id=None, user_id=None, **kwargs):
        self.rating = rating
        self.comment = comment
        self.book_id = book_id
        self.user_id = user_id
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        created_at_str = None
        if self.created_at:
            created_at_str = self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "id": self.id,
            "rating": self.rating,
            "comment": self.comment,
            "book_id": f"book_{self.book_id}",
            "user_id": f"user_{self.user_id}",
            "user_name": self.user.display_name if self.user else None,
            "createdAt": created_at_str
        }


class User(db.Model):
    __tablename__ = "users"

    id = mapped_column(Integer, primary_key=True)
    email = mapped_column(String(255), unique=True, nullable=False)
    display_name = mapped_column(String(120), nullable=False)
    password_hash = mapped_column(String(255), nullable=True)  # Không expose ra API!
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    reviews = relationship("Review", back_populates="user")
    orders = relationship("Order", back_populates="user")

    def __init__(self, email=None, display_name=None, password_hash=None, **kwargs):
        self.email = email
        self.display_name = display_name
        self.password_hash = password_hash
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        created_at_str = None
        if self.created_at:
            created_at_str = self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "id": f"user_{self.id}",
            "email": self.email,
            "display_name": self.display_name,
            "createdAt": created_at_str
        }


class Order(db.Model):
    __tablename__ = "orders"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = mapped_column(Integer, default=0)
    status = mapped_column(String(50), default="pending")
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __init__(self, user_id=None, total_amount=0, status="pending", **kwargs):
        self.user_id = user_id
        self.total_amount = total_amount
        self.status = status
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        created_at_str = None
        if self.created_at:
            created_at_str = self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "id": f"ord_{self.id}",
            "user_id": f"user_{self.user_id}",
            "total_amount": self.total_amount,
            "status": self.status,
            "createdAt": created_at_str,
            "items": [item.to_dict() for item in self.items]
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = mapped_column(Integer, primary_key=True)
    order_id = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    book_id = mapped_column(Integer, ForeignKey("books.id"), nullable=False)
    quantity = mapped_column(Integer, default=1)
    unit_price = mapped_column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    book = relationship("Book")

    def __init__(self, order_id=None, book_id=None, quantity=1, unit_price=0, **kwargs):
        self.order_id = order_id
        self.book_id = book_id
        self.quantity = quantity
        self.unit_price = unit_price
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return {
            "id": self.id,
            "book_id": f"book_{self.book_id}",
            "quantity": self.quantity,
            "unit_price": self.unit_price
        }

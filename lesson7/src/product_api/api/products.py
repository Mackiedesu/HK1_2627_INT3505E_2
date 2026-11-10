"""Blueprint Resource handling all 6 Product CRUD and stock reservation endpoints."""

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from ..errors import BadRequest, Conflict, NotFound, OutOfStock
from ..extensions import db
from ..models import Product
from .schemas import ProductIn, ProductOut, ProductPatch, ReserveIn

products_bp = Blueprint("products", __name__, url_prefix="/api/v1/products")


def _get_active_product_or_404(product_id: int) -> Product:
    """Fetch a non-archived Product by primary key or raise NotFound (404)."""
    product = db.session.get(Product, product_id)
    if product is None or product.archived:
        raise NotFound(message=f"Product {product_id} not found")
    return product


def _get_json_body() -> dict:
    """Parse JSON request body or raise BadRequest (400)."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest(message="Request body must be a valid JSON object")
    return data


@products_bp.get("")
def list_products():
    """GET /api/v1/products - List non-archived products with pagination."""
    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(100, max(1, int(request.args.get("size", 20))))
    except ValueError as exc:
        raise BadRequest(message="Pagination parameters page and size must be integers") from exc

    base = db.select(Product).where(Product.archived.is_(False))
    rows = (
        db.session.execute(
            base.order_by(Product.id).offset((page - 1) * size).limit(size)
        )
        .scalars()
        .all()
    )
    total = db.session.scalar(
        db.select(db.func.count())
        .select_from(Product)
        .where(Product.archived.is_(False))
    )
    return (
        jsonify(
            {
                "items": [ProductOut().dump(p) for p in rows],
                "page": page,
                "size": size,
                "total": total or 0,
            }
        ),
        200,
    )


@products_bp.get("/<int:id>")
def get_product(id: int):
    """GET /api/v1/products/<int:id> - Retrieve a single active product by ID."""
    product = _get_active_product_or_404(id)
    return jsonify(ProductOut().dump(product)), 200


@products_bp.post("")
def create_product():
    """POST /api/v1/products - Create a new product; return 409 if SKU already exists."""
    body = ProductIn().load(_get_json_body())
    product = Product(**body)
    db.session.add(product)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise Conflict(message="sku already exists") from exc
    return jsonify(ProductOut().dump(product)), 201


@products_bp.post("/<int:id>/reserve")
def reserve_product(id: int):
    """POST /api/v1/products/<int:id>/reserve - Decrement stock; return 409 if out of stock."""
    body = ReserveIn().load(_get_json_body())
    product = _get_active_product_or_404(id)
    qty = body["qty"]

    if product.qty_in_stock < qty:
        raise OutOfStock(message=f"only {product.qty_in_stock} left")

    product.qty_in_stock -= qty
    db.session.commit()
    return jsonify(ProductOut().dump(product)), 200


@products_bp.patch("/<int:id>")
def patch_product(id: int):
    """PATCH /api/v1/products/<int:id> - Partially update fields present in the request body."""
    body = ProductPatch().load(_get_json_body(), partial=True)
    product = _get_active_product_or_404(id)

    for key, value in body.items():
        setattr(product, key, value)

    db.session.commit()
    return jsonify(ProductOut().dump(product)), 200


@products_bp.delete("/<int:id>")
def delete_product(id: int):
    """DELETE /api/v1/products/<int:id> - Soft-delete product by marking archived=True."""
    product = _get_active_product_or_404(id)
    product.archived = True
    db.session.commit()
    return "", 204

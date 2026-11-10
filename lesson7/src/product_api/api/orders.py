"""Blueprint Resource for /api/v1/orders linking Order and Product via OrderItem."""

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload, selectinload
from ..errors import BadRequest, NotFound, OutOfStock
from ..extensions import db
from ..models import Order, OrderItem, Product
from .schemas import OrderIn, OrderOut

orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")


def _get_json_body() -> dict:
    """Parse JSON request body or raise BadRequest (400)."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest(message="Request body must be a valid JSON object")
    return data


@orders_bp.get("")
def list_orders():
    """
    GET /api/v1/orders - List orders with eager loading to prevent N+1 queries.
    Uses selectinload for Order.items (1-to-N) and joinedload for OrderItem.product (N-to-1).
    """
    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(100, max(1, int(request.args.get("size", 20))))
    except ValueError as exc:
        raise BadRequest(message="Pagination parameters page and size must be integers") from exc

    stmt = (
        db.select(Order)
        .options(selectinload(Order.items).joinedload(OrderItem.product))
        .order_by(Order.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    orders = db.session.execute(stmt).scalars().all()
    total = db.session.scalar(db.select(db.func.count()).select_from(Order))

    return (
        jsonify(
            {
                "items": [OrderOut().dump(o) for o in orders],
                "page": page,
                "size": size,
                "total": total or 0,
            }
        ),
        200,
    )


@orders_bp.get("/<int:id>")
def get_order(id: int):
    """
    GET /api/v1/orders/<int:id> - Retrieve a single order with eager-loaded items and products.
    """
    stmt = (
        db.select(Order)
        .where(Order.id == id)
        .options(selectinload(Order.items).joinedload(OrderItem.product))
    )
    order = db.session.execute(stmt).scalars().first()
    if order is None:
        raise NotFound(message=f"Order {id} not found")
    return jsonify(OrderOut().dump(order)), 200


@orders_bp.post("")
def create_order():
    """
    POST /api/v1/orders - Create an Order with multiple OrderItem entries linking Products.
    Validates stock availability and deducts ordered quantities in a single transaction.
    """
    body = OrderIn().load(_get_json_body())

    # Batch-fetch all requested non-archived products in a single query
    requested_ids = list({item["product_id"] for item in body["items"]})
    products = (
        db.session.execute(
            db.select(Product).where(
                Product.id.in_(requested_ids),
                Product.archived.is_(False),
            )
        )
        .scalars()
        .all()
    )
    product_map = {p.id: p for p in products}

    # Verify all products exist before mutating stock
    for item_data in body["items"]:
        pid = item_data["product_id"]
        if pid not in product_map:
            raise NotFound(message=f"Product {pid} not found")

    # Aggregate requested quantities per product to validate available stock
    required_qty_by_pid: dict[int, int] = {}
    for item_data in body["items"]:
        pid = item_data["product_id"]
        required_qty_by_pid[pid] = required_qty_by_pid.get(pid, 0) + item_data["qty"]

    for pid, total_qty in required_qty_by_pid.items():
        product = product_map[pid]
        if product.qty_in_stock < total_qty:
            raise OutOfStock(
                message=f"Product {product.sku} has only {product.qty_in_stock} left"
            )

    # Create Order and associated OrderItem records
    order = Order(customer_name=body["customer_name"], status="created", total_cents=0)
    total_cents = 0

    for item_data in body["items"]:
        product = product_map[item_data["product_id"]]
        qty = item_data["qty"]
        product.qty_in_stock -= qty
        line_total = product.price_cents * qty
        total_cents += line_total

        order_item = OrderItem(
            product=product,
            qty=qty,
            unit_price_cents=product.price_cents,
        )
        order.items.append(order_item)

    order.total_cents = total_cents
    db.session.add(order)
    db.session.commit()

    return jsonify(OrderOut().dump(order)), 201

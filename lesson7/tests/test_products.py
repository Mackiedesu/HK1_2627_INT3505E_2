"""Automated pytest suite for Product CRUD, OrderItem/Order resources, Health checks, and N+1 prevention."""


# ===========================================================================
# 1. Health Check Endpoints (/healthz and /ready)
# ===========================================================================
def test_healthz_liveness_probe(client):
    """Verify /healthz returns 200 OK without touching the database."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_ready_readiness_probe(client):
    """Verify /ready checks database connectivity and returns 200 OK."""
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["checks"]["db"] == "ok"


# ===========================================================================
# 2. Lab 1 — Product CRUD & Stock Reservation Endpoints (/api/v1/products)
# ===========================================================================
def test_create_and_get_product(client):
    """Test POST /api/v1/products and GET /api/v1/products/<id>."""
    payload = {
        "sku": "IPHONE-15-PRO",
        "name": "iPhone 15 Pro 256GB",
        "description": "Titaniumスマートフォン",
        "price_cents": 99900,
        "qty_in_stock": 15,
    }
    post_resp = client.post("/api/v1/products", json=payload)
    assert post_resp.status_code == 201
    created = post_resp.get_json()
    assert created["id"] > 0
    assert created["sku"] == "IPHONE-15-PRO"
    assert created["qty_in_stock"] == 15
    assert created["archived"] is False

    # Retrieve single product by ID
    get_resp = client.get(f"/api/v1/products/{created['id']}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["sku"] == "IPHONE-15-PRO"


def test_create_product_duplicate_sku_returns_409(client):
    """Test POST /api/v1/products returns 409 Conflict when SKU already exists."""
    payload = {"sku": "DUP-SKU-01", "name": "First Item", "price_cents": 1000}
    resp1 = client.post("/api/v1/products", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/products", json=payload)
    assert resp2.status_code == 409
    err = resp2.get_json()
    assert err["error"] == "conflict"
    assert "sku already exists" in err["detail"]


def test_create_product_validation_error_returns_422(client):
    """Test POST /api/v1/products returns 422 when input fails Marshmallow validation."""
    invalid_payload = {
        "sku": "AB",  # Too short (min=3)
        "name": "",  # Empty name
        "price_cents": -50,  # Negative price
    }
    resp = client.post("/api/v1/products", json=invalid_payload)
    assert resp.status_code == 422
    err = resp.get_json()
    assert err["error"] == "validation_error"
    assert "sku" in err["detail"]


def test_list_products_pagination_and_soft_delete(client):
    """Test GET /api/v1/products pagination and DELETE soft-delete exclusion."""
    # Create 3 products
    ids = []
    for idx in range(1, 4):
        r = client.post(
            "/api/v1/products",
            json={"sku": f"PROD-00{idx}", "name": f"Product {idx}", "price_cents": idx * 500},
        )
        assert r.status_code == 201
        ids.append(r.get_json()["id"])

    # Soft-delete the second product
    del_resp = client.delete(f"/api/v1/products/{ids[1]}")
    assert del_resp.status_code == 204

    # Deleted product should return 404 on direct GET
    get_deleted = client.get(f"/api/v1/products/{ids[1]}")
    assert get_deleted.status_code == 404

    # List products should only include non-archived items
    list_resp = client.get("/api/v1/products?page=1&size=20")
    assert list_resp.status_code == 200
    body = list_resp.get_json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["size"] == 20
    returned_skus = [item["sku"] for item in body["items"]]
    assert returned_skus == ["PROD-001", "PROD-003"]


def test_patch_product_partial_update(client):
    """Test PATCH /api/v1/products/<id> updates only provided fields."""
    post_resp = client.post(
        "/api/v1/products",
        json={"sku": "PATCH-ME", "name": "Old Name", "price_cents": 1000, "qty_in_stock": 5},
    )
    pid = post_resp.get_json()["id"]

    patch_resp = client.patch(f"/api/v1/products/{pid}", json={"price_cents": 1500})
    assert patch_resp.status_code == 200
    updated = patch_resp.get_json()
    assert updated["name"] == "Old Name"
    assert updated["price_cents"] == 1500
    assert updated["qty_in_stock"] == 5


def test_reserve_product_stock_and_out_of_stock_409(client):
    """Test POST /api/v1/products/<id>/reserve decrements stock and rejects excess reservation."""
    post_resp = client.post(
        "/api/v1/products",
        json={"sku": "RES-SKU-01", "name": "Limited Stock", "price_cents": 2500, "qty_in_stock": 3},
    )
    pid = post_resp.get_json()["id"]

    # Valid reservation of 2 units
    res_ok = client.post(f"/api/v1/products/{pid}/reserve", json={"qty": 2})
    assert res_ok.status_code == 200
    assert res_ok.get_json()["qty_in_stock"] == 1

    # Excess reservation of 2 units when only 1 remains -> 409 OutOfStock
    res_fail = client.post(f"/api/v1/products/{pid}/reserve", json={"qty": 2})
    assert res_fail.status_code == 409
    err = res_fail.get_json()
    assert err["code"] == "out_of_stock"
    assert "only 1 left" in err["detail"]


# ===========================================================================
# 3. Homework Task 2 & 5 — Order & OrderItem Endpoints + Eager Loading (N+1 Check)
# ===========================================================================
def test_create_order_with_multiple_order_items(client):
    """Test POST /api/v1/orders creates Order with multiple OrderItem entries and deducts stock."""
    p1 = client.post(
        "/api/v1/products",
        json={"sku": "KB-MECH", "name": "Mechanical Keyboard", "price_cents": 8000, "qty_in_stock": 10},
    ).get_json()
    p2 = client.post(
        "/api/v1/products",
        json={"sku": "MOUSE-PRO", "name": "Wireless Mouse", "price_cents": 4000, "qty_in_stock": 8},
    ).get_json()

    order_payload = {
        "customer_name": "Nguyen Van A",
        "items": [
            {"product_id": p1["id"], "qty": 2},
            {"product_id": p2["id"], "qty": 3},
        ],
    }
    resp = client.post("/api/v1/orders", json=order_payload)
    assert resp.status_code == 201
    order = resp.get_json()
    assert order["customer_name"] == "Nguyen Van A"
    assert order["total_cents"] == (2 * 8000) + (3 * 4000)
    assert len(order["items"]) == 2
    assert order["items"][0]["product"]["sku"] in {"KB-MECH", "MOUSE-PRO"}

    # Verify product stock was decremented in database
    p1_after = client.get(f"/api/v1/products/{p1['id']}").get_json()
    p2_after = client.get(f"/api/v1/products/{p2['id']}").get_json()
    assert p1_after["qty_in_stock"] == 8
    assert p2_after["qty_in_stock"] == 5


def test_list_orders_eager_loading_prevents_n_plus_1(client, count_queries):
    """
    Test GET /api/v1/orders uses eager loading (selectinload + joinedload)
    so query count stays constant regardless of the number of orders and items.
    """
    # Seed 3 products
    products = []
    for i in range(1, 4):
        p = client.post(
            "/api/v1/products",
            json={
                "sku": f"EAGER-SKU-{i}",
                "name": f"Eager Product {i}",
                "price_cents": 1000 * i,
                "qty_in_stock": 100,
            },
        ).get_json()
        products.append(p)

    # Create 10 orders, each containing 3 OrderItem records
    for order_idx in range(10):
        resp = client.post(
            "/api/v1/orders",
            json={
                "customer_name": f"Customer {order_idx}",
                "items": [
                    {"product_id": products[0]["id"], "qty": 1},
                    {"product_id": products[1]["id"], "qty": 2},
                    {"product_id": products[2]["id"], "qty": 1},
                ],
            },
        )
        assert resp.status_code == 201

    # Measure SQL queries executed during GET /api/v1/orders
    # Expected queries with eager loading:
    # 1. SELECT orders ... LIMIT 20 OFFSET 0
    # 2. SELECT order_items JOIN products WHERE order_items.order_id IN (...)
    # 3. SELECT count(*) FROM orders
    # Without eager loading (N+1), 10 orders * 3 items would trigger > 10-40 queries!
    with count_queries() as executed_sql:
        get_resp = client.get("/api/v1/orders")

    assert get_resp.status_code == 200
    data = get_resp.get_json()
    assert data["total"] == 10
    assert len(data["items"]) == 10
    assert len(data["items"][0]["items"]) == 3
    assert data["items"][0]["items"][0]["product"]["sku"] == "EAGER-SKU-1"

    # Assert constant query count (<= 3 SELECT statements, strictly preventing N+1)
    select_queries = [q for q in executed_sql if q.lstrip().upper().startswith("SELECT")]
    assert len(select_queries) <= 3, f"N+1 detected! Executed {len(select_queries)} SELECTs: {select_queries}"

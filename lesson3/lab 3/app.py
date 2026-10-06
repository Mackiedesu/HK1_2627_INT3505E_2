import base64
import json
from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.sort_keys = False
app.json.compact = False

ALLOWED_FIELDS = {"id", "customer_id", "status", "total", "created_at"}
SORTABLE_FIELDS = {"id", "customer_id", "status", "total", "created_at"}

ORDERS = [
    {"id": 1, "customer_id": 101, "status": "paid", "total": 150.0, "created_at": "2026-10-01T08:00:00Z"},
    {"id": 2, "customer_id": 102, "status": "pending", "total": 45.5, "created_at": "2026-10-01T09:30:00Z"},
    {"id": 3, "customer_id": 101, "status": "paid", "total": 200.0, "created_at": "2026-10-01T11:15:00Z"},
    {"id": 4, "customer_id": 103, "status": "shipped", "total": 89.9, "created_at": "2026-10-01T14:00:00Z"},
    {"id": 5, "customer_id": 104, "status": "paid", "total": 35.0, "created_at": "2026-10-02T10:00:00Z"},
    {"id": 6, "customer_id": 102, "status": "paid", "total": 510.0, "created_at": "2026-10-02T12:45:00Z"},
    {"id": 7, "customer_id": 105, "status": "pending", "total": 75.0, "created_at": "2026-10-02T15:20:00Z"},
]


def error_response(status, title, detail):
    return jsonify({
        "type": f"https://api.example.com/probs/{title.lower().replace(' ', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.path
    }), status, {"Content-Type": "application/problem+json"}


def encode_cursor(item, sort_key):
    payload = {
        "id": item["id"],
        "val": item[sort_key]
    }
    raw = json.dumps(payload)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor_str):
    try:
        raw = base64.urlsafe_b64decode(cursor_str.encode("utf-8")).decode("utf-8")
        data = json.loads(raw)
        if "id" not in data or "val" not in data:
            return None
        return data
    except Exception:
        return None


@app.get("/orders")
def get_orders():
    limit_str = request.args.get("limit", "10")
    try:
        limit = int(limit_str)
        if limit <= 0 or limit > 100:
            return error_response(400, "Invalid Parameter", "Limit must be between 1 and 100")
    except ValueError:
        return error_response(400, "Invalid Parameter", "Limit must be an integer")

    status_filter = request.args.get("status")
    customer_id_filter = request.args.get("customer_id")
    if customer_id_filter:
        try:
            customer_id_filter = int(customer_id_filter)
        except ValueError:
            return error_response(400, "Invalid Parameter", "customer_id must be an integer")

    sort_param = request.args.get("sort", "id")
    direction_param = request.args.get("direction")
    desc = False
    if sort_param.startswith("-"):
        sort_key = sort_param[1:]
        desc = True
    elif direction_param:
        sort_key = sort_param
        desc = direction_param.lower() == "desc"
    else:
        sort_key = sort_param

    if sort_key not in SORTABLE_FIELDS:
        return error_response(400, "Invalid Sort Field", f"Field '{sort_key}' is not sortable")

    fields_param = request.args.get("fields")
    requested_fields = None
    if fields_param:
        requested_fields = [f.strip() for f in fields_param.split(",") if f.strip()]
        for f in requested_fields:
            if f not in ALLOWED_FIELDS:
                return error_response(400, "Invalid Field", f"Field '{f}' does not exist")

    cursor_param = request.args.get("cursor")
    cursor_data = None
    if cursor_param:
        cursor_data = decode_cursor(cursor_param)
        if not cursor_data:
            return error_response(400, "Invalid Cursor", "The provided cursor is invalid")

    filtered = ORDERS
    if status_filter:
        filtered = [o for o in filtered if o["status"] == status_filter]
    if customer_id_filter:
        filtered = [o for o in filtered if o["customer_id"] == customer_id_filter]

    filtered = sorted(
        filtered,
        key=lambda o: (o[sort_key], o["id"]),
        reverse=desc
    )

    if cursor_data:
        last_id = cursor_data["id"]
        last_val = cursor_data["val"]

        def is_after(o):
            val = o[sort_key]
            if desc:
                return (val < last_val) or (val == last_val and o["id"] < last_id)
            else:
                return (val > last_val) or (val == last_val and o["id"] > last_id)

        filtered = [o for o in filtered if is_after(o)]

    page_items = filtered[:limit]
    has_more = len(filtered) > limit
    next_cursor = encode_cursor(page_items[-1], sort_key) if has_more and page_items else None

    if requested_fields:
        result_items = []
        for o in page_items:
            result_items.append({k: o[k] for k in requested_fields})
    else:
        result_items = page_items

    return jsonify({
        "data": result_items,
        "next_cursor": next_cursor,
        "has_more": has_more
    }), 200


if __name__ == "__main__":
    app.run(debug=True)

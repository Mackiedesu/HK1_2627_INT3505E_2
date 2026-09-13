from flask import Flask, jsonify

app = Flask(__name__)

ORDERS = {
    "1": {"id": "1", "status": "pending"},
    "2": {"id": "2", "status": "shipped"},
}

@app.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    order = ORDERS.get(order_id)
    
    # 404: Không tìm thấy order
    if order is None:
        return jsonify({"error": "not found"}), 404

    # 409 Conflict: Vi phạm logic nghiệp vụ
    if order["status"] in ("shipped", "delivered"):
        return jsonify({"error": "cannot delete order in current state"}), 409

    ORDERS.pop(order_id, None)
    # 204 No Content: Thành công, không trả nội dung body
    return "", 204

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
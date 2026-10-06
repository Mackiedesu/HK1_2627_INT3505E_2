import logging
from flask import Flask, jsonify, request, make_response
from errors import ApiProblem, ProblemError, register_error_handlers

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = False
app.json.sort_keys = False
app.json.compact = False

register_error_handlers(app)

USERS = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"},
]
_next_user_id = 3

RESOURCES = {
    1: {"id": 1, "name": "Server Cluster Alpha", "status": "active"},
    2: {"id": 2, "name": "Storage Volume Beta", "status": "maintenance"},
}


@app.get("/users")
def get_users():
    return jsonify({
        "data": USERS,
        "total": len(USERS)
    }), 200


@app.get("/users/<int:user_id>")
def get_user(user_id):
    user = next((u for u in USERS if u["id"] == user_id), None)
    if not user:
        raise ApiProblem(
            status=404,
            title="User not found",
            type_path="user-not-found",
            resource_id=user_id,
        )
    return jsonify(user), 200


@app.post("/users")
def create_user():
    global _next_user_id
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    email = payload.get("email")

    missing_fields = []
    if not name:
        missing_fields.append("name")
    if not email:
        missing_fields.append("email")

    if missing_fields:
        raise ApiProblem(
            status=422,
            title="Unprocessable Entity",
            detail=f"Missing or invalid required fields: {', '.join(missing_fields)}",
            type_path="validation-error",
            invalid_fields=missing_fields
        )

    if any(u["email"] == email for u in USERS):
        raise ApiProblem(
            status=409,
            title="Conflict",
            detail=f"Email '{email}' is already registered",
            type_path="email-already-exists",
            conflicting_email=email
        )

    new_user = {
        "id": _next_user_id,
        "name": name,
        "email": email
    }
    USERS.append(new_user)
    _next_user_id += 1

    resp = make_response(jsonify(new_user), 201)
    resp.headers["Location"] = f"/users/{new_user['id']}"
    return resp


@app.get("/resources/<int:id>")
def get_resource(id):
    resource = RESOURCES.get(id)
    if not resource:
        raise ProblemError(
            status=404,
            title="Resource Not Found",
            detail=f"Resource {id} does not exist.",
            type_path="resource-not-found",
            resource_id=id,
        )
    return jsonify(resource), 200


@app.get("/account/credit")
def check_credit():
    raise ApiProblem(
        status=403,
        title="You do not have enough credit.",
        detail="Your current balance is 30, but that costs 50.",
        type_path="out-of-credit",
        balance=30,
        accounts=["/account/12345", "/account/67890"]
    )


@app.get("/trigger-500")
def trigger_500():
    raise RuntimeError("Simulated unexpected server error")


if __name__ == "__main__":
    app.run(debug=True)



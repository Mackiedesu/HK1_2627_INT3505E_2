from flask import Flask, jsonify, request
from uuid import uuid4

app = Flask(__name__)
app.json.ensure_ascii = False
STUDENTS = []

@app.route("/students", methods=["POST"])
def create_student():
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    
    # Validation lỗi client -> 400 Bad Request
    if not name:
        return jsonify({"error": "name là bắt buộc"}), 400

    student = {
        "id": str(uuid4()),
        "name": name,
        "gpa": body.get("gpa", 0.0),
    }
    STUDENTS.append(student)
    
    # 201 Created kèm header Location
    return jsonify(student), 201, {"Location": f"/students/{student['id']}"}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
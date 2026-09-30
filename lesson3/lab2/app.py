from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# 1. Định nghĩa custom exception ProblemError
class ProblemError(Exception):
    def __init__(self, status=400, title="Bad Request", detail=None, type="about:blank"):
        self.status = status
        self.title = title
        self.detail = detail
        self.type = type

# Hàm phụ trợ tạo response chuẩn application/problem+json (tránh lặp code)
def problem_response(status, title, detail, type="about:blank"):
    return jsonify({
        "type": type,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.path
    }), status, {"Content-Type": "application/problem+json"}

# 2. Handler cho ProblemError
@app.errorhandler(ProblemError)
def handle_problem_error(e):
    return problem_response(e.status, e.title, e.detail, e.type)

# 3. Handler fallback cho các HTTPException chuẩn của Flask (404, 405,...)
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return problem_response(e.code, e.name, e.description)

# 4. Handler fallback cho lỗi không lường trước (500)
@app.errorhandler(Exception)
def handle_exception(e):
    # Ghi log kèm stack trace ở server-side, không trả chi tiết ra client
    app.logger.error("Internal Server Error: %s", e, exc_info=True)
    return problem_response(500, "Internal Server Error", "An unexpected error occurred.")

# ==========================================
# Routes kiểm thử
# ==========================================

# Test route theo yêu cầu: /resources/<id> trả về 404
@app.get("/resources/<int:id>")
def get_resource(id):
    raise ProblemError(
        status=404, 
        title="Resource Not Found", 
        detail=f"Resource {id} does not exist."
    )

# Test route giả lập lỗi 500
@app.get("/trigger-500")
def trigger_500():
    return 1 / 0

if __name__ == "__main__":
    app.run(debug=True)

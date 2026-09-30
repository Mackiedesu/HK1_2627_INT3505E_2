from flask import Flask, jsonify, request, make_response

app = Flask(__name__)

# Mock database ban đầu cho posts
POSTS = [
    {
        "id": 1,
        "title": "RESTful API Design",
        "content": "Huong dan thiet ke resource chuan RESTful...",
        "author": "Alice",
        "tags": ["api", "rest"]
    },
    {
        "id": 2,
        "title": "Flask Basics",
        "content": "Cach tao routes co ban trong Flask...",
        "author": "Bob",
        "tags": ["flask", "python"]
    }
]
_next_id = 3


# 1. GET /api/v1/posts - Danh sách bài viết
@app.get("/api/v1/posts")
def list_posts():
    return jsonify({
        "data": POSTS,
        "total": len(POSTS)
    }), 200


# 2. POST /api/v1/posts - Tạo bài viết mới
@app.post("/api/v1/posts")
def create_post():
    global _next_id
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()
    author = (payload.get("author") or "").strip()

    if not title or not content or not author:
        return jsonify(error="title, content, author are required"), 422

    new_post = {
        "id": _next_id,
        "title": title,
        "content": content,
        "author": author,
        "tags": payload.get("tags", [])
    }
    POSTS.append(new_post)
    _next_id += 1

    resp = make_response(jsonify(new_post), 201)
    resp.headers["Location"] = f"/api/v1/posts/{new_post['id']}"
    return resp


# 3. GET /api/v1/posts/<id> - Xem chi tiết bài viết
@app.get("/api/v1/posts/<int:post_id>")
def get_post(post_id):
    post = next((p for p in POSTS if p["id"] == post_id), None)
    if not post:
        return jsonify(error="Post not found"), 404
    return jsonify(post), 200


# 4. PUT /api/v1/posts/<id> - Cập nhật bài viết
@app.put("/api/v1/posts/<int:post_id>")
def update_post(post_id):
    post = next((p for p in POSTS if p["id"] == post_id), None)
    if not post:
        return jsonify(error="Post not found"), 404

    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()

    if not title or not content:
        return jsonify(error="title and content are required"), 422

    post["title"] = title
    post["content"] = content
    post["tags"] = payload.get("tags", post.get("tags", []))
    return jsonify(post), 200


# 5. DELETE /api/v1/posts/<id> - Xóa bài viết
@app.delete("/api/v1/posts/<int:post_id>")
def delete_post(post_id):
    global POSTS
    post = next((p for p in POSTS if p["id"] == post_id), None)
    if not post:
        return jsonify(error="Post not found"), 404

    POSTS = [p for p in POSTS if p["id"] != post_id]
    return "", 204


# 6. GET /api/v1/posts/<id>/tags - Danh sách thẻ của một bài viết
@app.get("/api/v1/posts/<int:post_id>/tags")
def get_post_tags(post_id):
    post = next((p for p in POSTS if p["id"] == post_id), None)
    if not post:
        return jsonify(error="Post not found"), 404
    return jsonify(post.get("tags", [])), 200


# 7. POST /api/v1/posts/<id>/tags - Gắn thêm thẻ vào bài viết
@app.post("/api/v1/posts/<int:post_id>/tags")
def add_post_tag(post_id):
    post = next((p for p in POSTS if p["id"] == post_id), None)
    if not post:
        return jsonify(error="Post not found"), 404

    payload = request.get_json(silent=True) or {}
    tag = (payload.get("tag") or "").strip().lower()

    if not tag:
        return jsonify(error="tag is required"), 422

    tags = post.get("tags", [])
    if tag not in tags:
        tags.append(tag)
        post["tags"] = tags

    return jsonify(post["tags"]), 201


# 8. GET /api/v1/tags - Toàn bộ danh mục thẻ trong hệ thống
@app.get("/api/v1/tags")
def get_all_tags():
    all_tags = set()
    for p in POSTS:
        for t in p.get("tags", []):
            all_tags.add(t)
    return jsonify(list(all_tags)), 200


if __name__ == "__main__":
    app.run(debug=True)

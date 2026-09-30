# Lab 1: Thiết Kế Resource Cho Blog API

## 1. Xác định Resources Trong Miền
Hệ thống blog gồm các resources chính:
- **`users`**: Người dùng / tác giả (hồ sơ, theo dõi).
- **`posts`**: Bài viết (tiêu đề, nội dung, tác giả).
- **`comments`**: Bình luận thuộc về một bài viết.
- **`tags`**: Thẻ phân loại gắn vào bài viết.

---

## 2. Phân Loại Resource
| Loại Resource | Endpoint Pattern | Ví dụ |
| :--- | :--- | :--- |
| **Collection** | `/{resources}` | `/posts`, `/users`, `/tags` |
| **Item** | `/{resources}/{id}` | `/posts/1`, `/users/2`, `/tags/1` |
| **Sub-resource** | `/{parent}/{id}/{sub-resources}` | `/posts/1/comments`, `/posts/1/tags`, `/users/1/following` |

---

## 3. Sơ Đồ Cây Endpoint & Quyết Định Version Segment
* **Quyết định Version Segment:** Sử dụng **URI Path Versioning** (`/api/v1`) vì trực quan, dễ quản lý và dễ debug.

```text
/api/v1
├── /posts
│   ├── GET /posts                          # Danh sách bài viết (hỗ trợ lọc ?tag=)
│   ├── POST /posts                         # Tạo bài viết mới
│   └── /{id}
│       ├── GET /posts/{id}                 # Chi tiết bài viết
│       ├── PUT /posts/{id}                 # Cập nhật bài viết
│       ├── DELETE /posts/{id}              # Xóa bài viết
│       ├── /comments
│       │   ├── GET /posts/{id}/comments    # Bình luận của bài viết
│       │   └── POST /posts/{id}/comments   # Thêm bình luận
│       └── /tags
│           ├── GET /posts/{id}/tags        # Danh sách thẻ gắn trên bài viết
│           └── POST /posts/{id}/tags       # Gắn thêm thẻ vào bài viết
│
├── /users
│   ├── GET /users                          # Danh sách người dùng
│   └── /{id}
│       ├── GET /users/{id}                 # Xem hồ sơ
│       └── /following
│           ├── GET /users/{id}/following   # Danh sách đang theo dõi
│           └── POST /users/{id}/following  # Theo dõi tác giả
│
└── /tags
    └── GET /tags                           # Toàn bộ danh mục thẻ trong hệ thống
```

---

## 4. Triển Khai Flask Routes Cho Collection `/posts` (`app.py`)

Tệp `app.py` triển khai đầy đủ các thao tác CRUD cơ bản cho collection `/posts`:

| Method | Endpoint | Mô tả | Request Body mẫu | Status |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/posts` | Lấy danh sách bài viết | Không có | `200 OK` |
| `POST` | `/api/v1/posts` | Tạo bài viết mới | `{"title":"REST API","content":"Noi dung","author":"Alice","tags":["api"]}` | `201 Created` |
| `GET` | `/api/v1/posts/<id>` | Xem chi tiết bài viết | Không có | `200 OK` / `404` |
| `PUT` | `/api/v1/posts/<id>` | Cập nhật bài viết | `{"title":"Tieu de moi","content":"Noi dung moi"}` | `200 OK` / `422` |
| `DELETE` | `/api/v1/posts/<id>` | Xóa bài viết | Không có | `204 No Content` |

---

## 5. Hướng Dẫn Chạy & Test Nhanh (cURL)

1. **Khởi động server:**
```bash
python "lesson3/lab 1/app.py"
```

2. **Test các API:**
```bash
# Lấy danh sách bài viết
curl -i http://127.0.0.1:5000/api/v1/posts

# Tạo bài viết mới
curl -i -X POST http://127.0.0.1:5000/api/v1/posts \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Bai viet moi\",\"content\":\"Noi dung bai viet\",\"author\":\"Nam\"}"

# Xem chi tiết bài viết id=1
curl -i http://127.0.0.1:5000/api/v1/posts/1

# Cập nhật bài viết id=1
curl -i -X PUT http://127.0.0.1:5000/api/v1/posts/1 \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Tieu de da sua\",\"content\":\"Noi dung da sua\"}"

# Xóa bài viết id=1
curl -i -X DELETE http://127.0.0.1:5000/api/v1/posts/1
```

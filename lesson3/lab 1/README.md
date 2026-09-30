# Lab 1: Thiết Kế Resource Cho Blog API

## 1. Xác định Resources Trong Miền
- **`users`**
- **`posts`**
- **`comments`**
- **`tags`**

---

## 2. Phân Loại Resource
| Loại Resource | Endpoint Pattern | Ví dụ |
| :--- | :--- | :--- |
| **Collection** | `/{resources}` | `/posts`, `/users`, `/tags` |
| **Item** | `/{resources}/{id}` | `/posts/1`, `/users/2`, `/tags/1` |
| **Sub-resource** | `/{parent}/{id}/{sub-resources}` | `/posts/1/comments`, `/posts/1/tags`, `/users/1/following` |

---

## 3. Sơ Đồ Cây Endpoint & Quyết Định Version Segment

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

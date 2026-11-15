# Lab 4 — Phân tích kết quả

## Bảng tổng hợp số liệu đo thực tế từ Locust

| Kịch bản | Users | Spawn rate | Duration | Tổng Requests | p50 (ms) | p95 (ms) | p99 (ms) | Failure rate | RPS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **A (Baseline)** | 10 | 2 /s | 30s | 142 | 4 | **17** | 26 | 0.00% (0/142) | 4.86 |
| **B (Load test)** | 50 | 5 /s | 60s | 1,389 | 6 | **21** | 36 | 0.43% (6/1,389) | 23.51 |
| **C (Spike test)** | 200 | 50 /s | 30s | 2,824 | 10 | **120** | 200 | 0.18% (5/2,824) | 96.79 |

### Chi tiết theo từng Endpoint ở Kịch bản C (200 Users, Spike Test)

| Method | Endpoint | # Reqs | # Fails | Median (p50) | p95 (ms) | p99 (ms) | Max (ms) | RPS |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `GET` | `/books` | 1,064 | 0 (0.00%) | 9 ms | 130 ms | 200 ms | 264 ms | 36.47 |
| `GET` | `/books/{id}` | 669 | 0 (0.00%) | 8 ms | 83 ms | 180 ms | 237 ms | 22.93 |
| `GET` | `/books?year={year}` | 741 | 5 (0.67%) | 9 ms | 100 ms | 190 ms | 256 ms | 25.40 |
| `POST` | `/books` | 350 | 0 (0.00%) | 22 ms | 160 ms | 240 ms | 299 ms | 12.00 |
| **Tổng** | **Aggregated** | **2,824** | **5 (0.18%)** | **10 ms** | **120 ms** | **200 ms** | **299 ms** | **96.79** |

---

## Trả lời các câu hỏi phân tích

### 1. Kịch bản có p95 cao nhất là gì? Dùng số liệu quan sát để giải thích.
- **Kịch bản C (Spike test — 200 users, spawn rate 50 users/s)** có độ trễ **p95 cao nhất đạt `120 ms`** (tăng gấp **7 lần** so với Kịch bản A là `17 ms` và gấp **5.7 lần** so với Kịch bản B là `21 ms`). Độ trễ p99 cũng vọt từ `26 ms` (A) và `36 ms` (B) lên `200 ms` (C), cực đại đạt `299 ms` ở `POST /books`.
- **Nguyên nhân tăng phi tuyến sau ngưỡng tải:**
  1. **Database Write Lock của SQLite:** Endpoint `POST /books` (`p95 = 160 ms`) thực hiện ghi và `db.session.commit()` xuống file SQLite (`instance/books.db`). SQLite khóa mức file/database khi có transaction ghi, khiến các request đọc/ghi đồng thời ở tốc độ `96.79 RPS` phải xếp hàng đợi I/O.
  2. **Full Table Scan chưa có Index trên cột `year`:** Endpoint `GET /books?year={year}` (`p95 = 100 ms`) lọc theo `year` nhưng trong `models.py` cột `year` không khai báo `index=True`. Khi `POST /books` liên tục chèn thêm hàng trăm bản ghi mới qua các kịch bản, truy vấn lọc phải quét nhiều dữ liệu hơn.
  3. **Queueing tại Werkzeug Development Server:** Khi 200 user ảo được bơm dồn dập trong 4 giây (`-r 50`), hàng đợi socket và GIL của tiến trình Python đơn lẻ bị tranh chấp mạnh, làm phần đuôi phân phối (p95, p99) dãn rộng nhanh hơn nhiều so với trung vị (`p50` chỉ tăng từ `4 ms` lên `10 ms`).

---

### 2. Endpoint nào tăng failure rate? Phân biệt lỗi HTTP thực và lỗi đánh dấu trong Locust.
- **Endpoint có ghi nhận lỗi trong báo cáo:** `GET /books?year={year}` với:
  - Kịch bản A: `0/37` lỗi (`0.00%` — mẫu nhỏ 37 requests với xác suất 1% nên chưa rơi vào trường hợp lỗi).
  - Kịch bản B: `6/325` lỗi (`1.85%` trên riêng endpoint, tương ứng `0.43%` toàn cục).
  - Kịch bản C: `5/741` lỗi (`0.67%` trên riêng endpoint, tương ứng `0.18%` toàn cục).
- **Phân biệt rõ bản chất lỗi:**
  1. **Lỗi đánh dấu phía Client trong Locust (`response.failure()`):** Toàn bộ 11 lỗi ghi nhận trên `GET /books?year={year}` ở Kịch bản B và C đều là **lỗi giả lập phía client** do đoạn code `if random.random() < 0.01: response.failure("Simulated 500 Internal Server Error (1% client-side injected)")` trong `locustfile.py` tạo ra. Thực tế Flask server vẫn trả về `HTTP 200 OK`.
  2. **HTTP 404 hợp lệ được xử lý bằng `response.success()`:** Trên `GET /books/{id}` (với `id` ngẫu nhiên `1..50`), khi ID chưa tồn tại server trả về `HTTP 404`. Vì đây là hành vi nghiệp vụ đúng, `catch_response=True` kết hợp `if response.status_code in (200, 404): response.success()` đã giúp Locust không tính nhầm 404 là lỗi vận hành (`0%` failure).
  3. **Khi tải vượt ngưỡng chịu đựng thực tế (nếu tăng user cao hơn nữa hoặc thêm unique `isbn` trùng lặp):** `POST /books` trong code hiện tại không gửi `isbn` nên không bị `409 CONFLICT`; tuy nhiên nếu tăng lên hàng nghìn concurrent users trên SQLite, lỗi **HTTP 500 thực sự từ server** (`sqlite3.OperationalError: database is locked`) hoặc `ConnectionError / ReadTimeout` sẽ xuất hiện ở `POST /books` trước tiên.

---

### 3. Với SLO giả định p95 < 300 ms, kịch bản nào đạt? Nêu giới hạn của phép đo và đề xuất baseline cho CI gate.
- **Kết quả đối chiếu ngưỡng `p95 < 300 ms`:**
  - Về mặt con số thuần túy, cả 3 kịch bản **A (`17 ms`)**, **B (`21 ms`)** và **C (`120 ms`)** đều có `p95 < 300 ms` (ngay cả endpoint chậm nhất ở Kịch bản C là `POST /books` có `p95 = 160 ms`, `p99 = 240 ms`, `max = 299 ms`).
  - Nếu tính kèm điều kiện **Error Rate SLO** (ví dụ error rate thực tế = `0%` hoặc tổng failure rate < `0.5%`), Kịch bản A và B/C đều nằm trong biên độ của lỗi giả lập 1% trên task `search_by_year` (chiếm 2/8 = 25% tổng trọng số request, kỳ vọng lỗi tổng thể ~`0.25%`).
- **Giới hạn của phép đo (Tại sao không dùng kết quả này để cam kết SLO Production):**
  1. **Chạy trên Loopback (`127.0.0.1`):** Load generator (`locust`) và Flask server dùng chung CPU/RAM trên cùng một máy cá nhân, độ trễ mạng vật lý (network RTT, TLS handshake, reverse proxy/load balancer) bằng `0 ms`.
  2. **Flask Development Server + SQLite cục bộ:** Chưa qua WSGI production server (Gunicorn/uWSGI) và RDBMS thực thụ (PostgreSQL) với network I/O riêng.
  3. **Thời gian đo ngắn (30s–60s) và dữ liệu nhỏ:** Chưa phản ánh hiện tượng đầy connection pool, phân mảnh bảng, hay rò rỉ bộ nhớ (cần Soak test nhiều giờ).
- **Đề xuất Baseline cho CI Gate:**
  - Trong pipeline CI (GitHub Actions), chạy kịch bản tương đương **Kịch bản B rút gọn** (`-u 30 -r 5 -t 30s --headless`) làm smoke performance gate với ngưỡng chặn build:
    - `Aggregated p95 < 150 ms`
    - `Server 5xx / Unexpected failure rate == 0%`

---

### 4. Câu hỏi Bonus: Nếu connection pool bị giới hạn ở 5 (`pool_size=5, max_overflow=0`), điều gì xảy ra khi 200 user truy cập đồng thời? Làm thế nào để xác nhận bằng Locust?
- **Hiện tượng xảy ra khi `pool_size=5` dưới tải 200 concurrent users:**
  1. **Nghẽn cổ chai hàng đợi kết nối (Connection Pool Exhaustion):** Tại mọi thời điểm chỉ tối đa **5 request** được mượn kết nối DB để thực thi truy vấn; **195 request còn lại** bị chặn tại tầng SQLAlchemy `QueuePool` chờ kết nối được trả về.
  2. **Độ trễ đuôi (p95, p99) tăng vọt:** Thời gian đáp ứng của request sẽ bằng `thời gian chờ mượn connection trong pool + thời gian chạy SQL`. Đường biểu diễn `p95`/`p99` tăng dựng đứng dù CPU của DB có thể chưa đầy.
  3. **Bùng nổ lỗi `TimeoutError` → HTTP 500:** Nếu một request chờ quá ngưỡng `pool_timeout` (mặc định 30s trong SQLAlchemy, hoặc thấp hơn nếu cấu hình chặt), SQLAlchemy sẽ quăng `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 0 reached, connection timed out`. Flask nếu không bắt riêng sẽ trả về **HTTP 500 Internal Server Error**, kéo cột `# fails` tăng mạnh.
- **Cách kiểm chứng và xác nhận bằng Locust:**
  1. **Cấu hình App:** Thiết lập `SQLALCHEMY_ENGINE_OPTIONS = {"pool_size": 5, "max_overflow": 0, "pool_timeout": 2}` trên kết nối DB hỗ trợ pooling (như PostgreSQL hoặc SQLAlchemy QueuePool) và giảm `wait_time` trong Locust xuống `between(0.1, 0.5)` để ép 200 requests đồng thời giữ kết nối.
  2. **Chạy Locust Spike Test (`-u 200 -r 50 -t 30s`):**
     - Quan sát bảng **Response Time Percentiles**: khoảng cách giữa `p50` và `p95`/`p99` dãn ra rất lớn (ví dụ `p50 = 20 ms` nhưng `p95 > 2000 ms`), đồng thời **RPS bão hòa (đi ngang)** không tăng thêm dù số user tăng từ 20 lên 200.
     - Quan sát bảng **Error Report** của Locust: xuất hiện hàng loạt lỗi `HTTPError('500 Server Error')` ngay sau mốc `pool_timeout` (2 giây), khớp với stack trace `QueuePool limit of size 5 overflow 0 reached` trên log của Flask server.

# Bếp thông minh – tìm món theo nguyên liệu, tính dinh dưỡng, AI tạo công thức

Web tìm món từ 31.183 công thức (`data/recipes_clean.xlsx`). Người dùng nhập nguyên liệu, số khẩu phần, bữa ăn và các bộ lọc; hệ thống trả về món phù hợp, tính lại lượng nguyên liệu theo khẩu phần, hiển thị dinh dưỡng, nhờ AI viết công thức và có chatbot giải thích thành phần, dinh dưỡng.

## Chức năng (giao diện theo mẫu HealthyMeal: 7 khối đánh số; Favorites và History lưu bằng localStorage của trình duyệt; có đăng ký, đăng nhập và đăng xuất bằng SQLite ở server)
1. **Nguyên liệu:** nhập tiếng Anh giống ngôn ngữ của dataset (`chicken, carrot, potato`), đối chiếu với tên nguyên liệu `ingredients.food`; có ô "Match all ingredients" và các từ gợi ý bấm được.
2. **Số khẩu phần:** lấy món có khẩu phần gốc trong [n-2, n+2]; khi mở món, lượng nguyên liệu và dinh dưỡng được nhân hệ số n / khẩu phần gốc.
3. **Bữa ăn, chế độ ăn, ẩm thực, loại món:** lựa chọn lấy từ dữ liệu (`meal_type`, `diet_labels`, `cuisine_type`, `dish_type`).
4. **Sắp xếp calo:** tăng dần hoặc giảm dần theo tổng calo công thức gốc.
5. **Kết quả:** tên món, ảnh (`image_url`), calo, độ khớp nguyên liệu; chi tiết gồm nguyên liệu đã nhân hệ số, bảng 29 chất dinh dưỡng từ `total_nutrients` (mỗi khẩu phần và cả món).
6. **AI tạo công thức:** Gemini viết công thức tiếng Việt từ danh sách nguyên liệu của món, không dùng `url`.
7. **Chatbot:** chỉ giải thích thành phần và dinh dưỡng của món đang xem, không tìm hay gợi ý món khác.

## Cài đặt và chạy
```bash
pip install -r requirements.txt
python scripts/build_data.py                 # tạo web/data/recipes.json.gz (đã có sẵn, chạy lại khi đổi dữ liệu)
export GEMINI_API_KEY="khoa_cua_ban"         # Windows PowerShell: $env:GEMINI_API_KEY="khoa_cua_ban"
uvicorn api.main:app --port 8000             # chạy từ thư mục gốc dự án
```
Mở http://localhost:8000. Khóa lấy tại Google AI Studio và chỉ nằm ở server (không đưa lên git). Nếu **không đặt khóa**, tìm kiếm và dinh dưỡng vẫn chạy, phần "AI recipe" và "Ask about this dish" tự ẩn. Có thể đổi model bằng biến `GEMINI_MODEL` (mặc định `gemini-2.5-flash`).

Kiểm thử (khi server đang chạy): `python scripts/test_api.py` – 10 trường hợp hợp lệ và không hợp lệ; mã 503 chấp nhận được khi chưa có khóa.

## Cấu trúc
```
api/main.py            FastAPI: /api/health, /api/generate (gọi Gemini), phục vụ thư mục web/
data/recipes_clean.xlsx
scripts/build_data.py  xlsx -> web/data/recipes.json.gz     scripts/test_api.py  kiểm thử API
web/index.html, css/style.css, js/app.js, data/recipes.json.gz, assets/images/
requirements.txt  README.md
```

## Hạn chế (nên nêu trong báo cáo)
- Toàn bộ giao diện, tên món, nguyên liệu, nhãn và câu trả lời AI dùng tiếng Anh để cùng ngôn ngữ với dataset; nguyên liệu phải nhập bằng tiếng Anh.
- Ảnh là link ngoài trong `image_url`, có thể hết hạn; khi lỗi, giao diện hiển thị biểu tượng theo loại món.
- Công thức và lời giải thích do AI tạo, có thể sai; giao diện đã ghi chú nhưng cần kiểm tra lại. Thông tin dinh dưỡng chỉ mang tính tham khảo, không thay lời khuyên của bác sĩ hoặc chuyên gia dinh dưỡng.
- Calo và dinh dưỡng là số liệu của cả công thức theo khẩu phần gốc; mỗi khẩu phần = tổng chia số khẩu phần gốc.
- Dữ liệu nén khoảng 8 MB được tải và giải nén ở trình duyệt (cần Chrome, Edge, Safari 16.4 trở lên hoặc Firefox mới), lần mở đầu hơi chậm.
- Chưa có model học máy tự huấn luyện; hệ thống dựa trên lọc dữ liệu và AI có sẵn.


## Đăng ký / đăng nhập
- Bấm **Đăng ký** trên góc phải để tạo tài khoản.
- Tài khoản được lưu trong `users.db` bằng SQLite.
- Mật khẩu không lưu dạng văn bản mà được băm bằng PBKDF2-HMAC-SHA256.
- Sau khi đăng ký/đăng nhập, phiên đăng nhập được giữ bằng cookie HTTP-only trong 7 ngày.
- Bấm **Đăng xuất** để kết thúc phiên.
- Chức năng Favorites/History hiện vẫn lưu ở trình duyệt bằng `localStorage`; đăng nhập chưa đồng bộ các dữ liệu này lên server.

## Phân trang món ăn
- Nút **Show more** đã được bỏ.
- Mỗi trang hiển thị **10 món ăn**.
- Có nút trang trước, trang sau và số trang.
- Khi tìm kiếm hoặc thay đổi bộ lọc, danh sách tự quay về trang 1.


## Giao diện chi tiết và phân trang
- Đã bỏ phần hiển thị nhãn bữa ăn như **Brunch** trong chi tiết món.
- Đã bỏ bảng **Nutrition (total_nutrients)** và mục **All nutrients** khỏi giao diện chi tiết.
- Mỗi trang kết quả hiển thị **12 món ăn**.
- Phân trang tự cập nhật khi tìm kiếm/lọc.


## Giao diện MealMate (bản mới)
- Chỉ đổi giao diện (`web/index.html`, `web/css/style.css`, `web/js/app.js`, ảnh lá trong `web/assets/images/`); `api/`, `data/`, `scripts/`, công thức và dữ liệu giữ nguyên.
- Ngôn ngữ: **Python** (server) + **HTML/CSS/JavaScript thuần** (giao diện) – không cần cài thêm framework nào.
- Cột trái: Home / Favorites / History, **Sign in** và **Create account** (lưu SQLite trong `users.db`).
- Giữa: Ingredients (thẻ nhỏ có ×), Servings, Meal type, Search by dish name, Match ingredients, bộ lọc Diet / Cuisine / Diet type / Calories, 12 món mỗi trang.
- Phải: Dish details, nguyên liệu tự nhân theo khẩu phần, **AI Recipe** (cần đăng nhập), **Ask about this dish** (chatbot).
- Chữ dùng font Source Serif 4 và Lato tải từ Google Fonts (cần internet; không có thì dùng font dự phòng).
- Lỗi cần biết: `api/llm.py` mặc định model `gemini-3.8-flash`; nếu AI recipe báo lỗi, đặt `GEMINI_MODEL=gemini-2.5-flash` trong `.env`.

## Cập nhật mới nhất
- Ô **Ingredients**: nguyên liệu hiện thẳng trong thanh tìm kiếm, tự thêm ", " sau mỗi món ("chicken, egg, rice, "). Bấm gợi ý bên dưới để thêm hoặc bỏ món; danh sách món tự cập nhật khi gõ.
- **Create account / Sign in**: giao diện tự tìm server ở cổng 8000 kể cả khi bạn mở trang bằng Live Server; `api/main.py` thêm CORS cho localhost. Nếu server chưa chạy, cửa sổ báo rõ cách chạy; lỗi database hiện đúng nội dung thay vì báo chung chung.
- Cách chạy đúng (Windows/Mac/Linux): mở terminal ở thư mục gốc dự án rồi `pip install -r requirements.txt` và `uvicorn api.main:app --port 8000`, sau đó mở http://localhost:8000.

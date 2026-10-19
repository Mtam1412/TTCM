"""Kiểm thử API (chạy khi server đang hoạt động):  python scripts/test_api.py"""
import requests
B = "http://127.0.0.1:8000"
turn = lambda r, c: {"role": r, "content": c}
CASES = [  # (tên, phương thức, đường dẫn, dữ liệu gửi, các mã HTTP chấp nhận)
    ("Health", "get", "/api/health", None, (200,)),
    ("Trang chủ", "get", "/", None, (200,)),
    ("Dữ liệu nén", "get", "/data/recipes.json.gz", None, (200,)),
    ("Câu lệnh hợp lệ", "post", "/api/generate", {"input": "Giải thích protein là gì, 2 câu"}, (200, 503)),
    ("Hội thoại hợp lệ", "post", "/api/generate", {"input": [turn("user", "Natri là gì?")]}, (200, 503)),
    ("Input rỗng", "post", "/api/generate", {"input": "   "}, (422,)),
    ("Input quá dài", "post", "/api/generate", {"input": "a" * 9000}, (422,)),
    ("Thiếu trường input", "post", "/api/generate", {}, (422,)),
    ("Hội thoại kết thúc bằng assistant", "post", "/api/generate", {"input": [turn("user", "hi"), turn("assistant", "hello")]}, (422,)),
    ("Vai trò sai", "post", "/api/generate", {"input": [turn("admin", "hi")]}, (422,)),
]
ok = 0
for name, m, path, data, want in CASES:
    try:
        r = getattr(requests, m)(B + path, json=data, timeout=60) if data is not None else getattr(requests, m)(B + path, timeout=60)
        good = r.status_code in want
        print(f"[{'OK ' if good else 'LỖI'}] {name}: HTTP {r.status_code} (mong đợi {want})"); ok += good
    except requests.RequestException as e:
        print(f"[LỖI] {name}: không kết nối được ({e})")
print(f"{ok}/{len(CASES)} trường hợp đạt (503 là chấp nhận được khi chưa đặt GEMINI_API_KEY)")

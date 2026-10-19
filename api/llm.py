""" 
Nhiệm vụ: nhận 1 món ăn -> trả về công thức + video. Dùng Gemini.
Thứ tự làm việc:
  1. Tìm video hướng dẫn trên YouTube (YouTube Data API).
  2. Cho Gemini tìm trên web (Google Search) trước rồi mới viết công thức, chỉ dựa vào nguồn tìm được.
  3. Nếu web không có nguồn nào -> Gemini tự viết công thức (và báo rõ cho người dùng).
"""
import json
import os
import time
import re
from urllib.parse import urlparse

import httpx

YT_URL = "https://www.googleapis.com/youtube/v3/search"

_client = None


def _get_client(key: str):
    """Tạo Gemini client MỘT lần rồi dùng lại, để kết nối không bị đóng giữa chừng."""
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=key)
    return _client

JSON_FORMAT = (
    'Reply ONLY with JSON: {"summary": string, "prepTime": string|null, "cookTime": string|null, '
    '"steps": string[], "tips": string[], "notes": string|null}'
)


class AIError(Exception):
    """Lỗi có kèm mã HTTP để main.py trả về cho trình duyệt."""
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


# ---------- Gọi Gemini ----------
def _gemini(instructions: str, prompt: str, search: bool):
    """Trả về (chữ AI viết, danh sách nguồn web). search=True thì bật Google Search."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise AIError(503, "GEMINI_API_KEY is not configured on the server")
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=instructions,
        tools=[types.Tool(google_search=types.GoogleSearch())] if search else None,
    )
    client = _get_client(key)
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
                contents=prompt, config=config)
            return (resp.text or ""), _read_sources(resp)
        except Exception as e:
            print("GEMINI ERROR (recipe):", repr(e))
            msg = str(e)
            if ("503" in msg or "UNAVAILABLE" in msg) and attempt < 2:
                time.sleep(3 * (attempt + 1))   # Google đang quá tải: chờ 3 giây, rồi 6 giây, rồi thử lại
                continue
            limited = "429" in msg or "RESOURCE_EXHAUSTED" in msg
            raise AIError(429 if limited else 502,
                          "AI service is busy, please retry" if limited else "AI service error, please retry")


def _read_sources(resp) -> list:
    """Danh sách trang web THẬT mà Google Search đã tìm được cho câu trả lời này."""
    sources = {}
    try:
        chunks = resp.candidates[0].grounding_metadata.grounding_chunks or []
    except (AttributeError, IndexError, TypeError):
        return []
    for c in chunks:
        w = getattr(c, "web", None)
        if not w or not w.uri:
            continue
        domain = (w.domain or w.title or urlparse(w.uri).netloc).removeprefix("www.")
        sources.setdefault(w.uri, {"url": w.uri, "title": w.title or domain, "domain": domain})
    return list(sources.values())


def _parse_recipe(text: str):
    m = re.search(r"\{[\s\S]*\}", re.sub(r"```json|```", "", text))
    try:
        rec = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
    if rec and isinstance(rec.get("steps"), list) and rec["steps"]:
        return rec
    return None


def _dish_text(r: dict) -> str:
    lines = []
    for i in r["ingredients"]:
        measure = i.get("measure") if i.get("measure") != "<unit>" else ""
        lines.append(re.sub(r"\s+", " ", f"- {i.get('quantity') or ''} {measure or ''} {i['food']}"))
    return (f"Dish: {r['name']}\nServings: {r['servings']}\n"
            f"Ingredients (already scaled to {r['servings']} servings):\n" + "\n".join(lines))


# ---------- Bước 1: YouTube ----------
def find_videos(name: str) -> dict:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        return {"videos": [], "warning": "YOUTUBE_API_KEY is not configured."}
    try:
        r = httpx.get(YT_URL, timeout=20, params={
            "part": "snippet", "type": "video", "maxResults": 3, "videoEmbeddable": "true",
            "safeSearch": "strict", "q": f"{name} recipe", "key": key})
        data = r.json()
    except (httpx.HTTPError, ValueError):
        return {"videos": [], "warning": "YouTube request failed."}
    if r.status_code != 200:
        return {"videos": [], "warning": data.get("error", {}).get("message", "YouTube request failed.")}
    return {"videos": [{
        "id": v["id"]["videoId"],
        "url": "https://www.youtube.com/watch?v=" + v["id"]["videoId"],
        "title": v["snippet"]["title"],
        "channel": v["snippet"]["channelTitle"],
        "thumb": v["snippet"].get("thumbnails", {}).get("medium", {}).get("url"),
    } for v in data.get("items", [])]}


# ---------- Bước 2: tìm web rồi mới viết ----------
def _recipe_from_web(r: dict):
    """Trả về (công thức, nguồn). Trả None nếu Google Search không có nguồn nào."""
    text, sources = _gemini(
        "You are a careful recipe writer. You MUST first use Google Search to find 2-3 reputable "
        "recipes for the requested dish. Write the method ONLY from what those sources describe, "
        "adapted to the ingredient list and servings provided. Do not invent steps, temperatures "
        "or times that no source supports; if sources disagree, pick the most common approach "
        'and say so in "notes". ' + JSON_FORMAT,
        _dish_text(r), search=True)
    if not sources:
        return None
    recipe = _parse_recipe(text)
    if not recipe:
        raise AIError(502, "The AI reply could not be read.")
    return recipe, sources


# ---------- Bước 3 (dự phòng): AI tự viết ----------
def _recipe_from_ai_only(r: dict) -> dict:
    text, _ = _gemini(
        "You are a helpful chef. Write a clear, practical recipe for the dish using the ingredient "
        "list and amounts given. You may add water and basic seasonings (say they are optional). "
        "Include times and temperatures where needed. " + JSON_FORMAT,
        _dish_text(r), search=False)
    recipe = _parse_recipe(text)
    if not recipe:
        raise AIError(502, "The AI reply could not be read. Try again.")
    return recipe


# ---------- Hàm chính main.py sẽ gọi ----------
def make_recipe(r: dict) -> dict:
    out = find_videos(r["name"])                  # 1) video
    grounded = None
    try:
        grounded = _recipe_from_web(r)            # 2) web + công thức
    except AIError as e:
        if e.status == 503:                       # thiếu key thì dự phòng cũng hỏng
            raise
        # 429 (hết lượt) hoặc lỗi khác: vẫn thử viết công thức không cần tìm web
    if grounded:
        out["recipe"], out["web_sources"], out["grounded"] = grounded[0], grounded[1], True
    else:
        out["recipe"], out["web_sources"], out["grounded"] = _recipe_from_ai_only(r), [], False  # 3) dự phòng
    return out
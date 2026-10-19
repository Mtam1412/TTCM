"""Đọc data/recipes_clean.xlsx, rút gọn và nén thành web/data/recipes.json.gz cho trang web.
Mỗi món: i (số thứ tự), n (tên), s (khẩu phần gốc), c (tổng calo gốc), m (đuôi link ảnh),
d/u/t/y (chế độ ăn / ẩm thực / bữa ăn / loại món), g (nguyên liệu: [tên, lượng, đơn vị, gram]), x (dinh dưỡng của cả món)."""
import gzip, json, os, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUTK = "PROCNT FAT FASAT FAMS FAPU FATRN CHOLE CHOCDF SUGAR FIBTG WATER NA K CA FE MG P ZN VITA_RAE VITC VITD TOCPHA VITK1 THIA RIBF NIA VITB6A FOLDFE VITB12".split()
PREFIX = "https://datahive-prod-dataset-products.s3.eu-central-1.amazonaws.com/dataset/346/"
df = pd.read_excel(os.path.join(ROOT, "data", "recipes_clean.xlsx"), dtype=str)
L = lambda s: json.loads(s) if isinstance(s, str) and s else []
rows, bad = [], 0
for r in df.itertuples():
    try:
        s = max(1, int(round(float(r.servings)))); c = round(float(r.calories), 1)
        tn = json.loads(r.total_nutrients); ings = json.loads(r.ingredients)
    except (ValueError, TypeError, KeyError):
        bad += 1; continue                                   # bỏ dòng hỏng
    ing = [[g.get("food") or "", round(g["quantity"], 2) if g.get("scalable") and g.get("quantity") else None,
            g.get("measure"), round(g["weight"]) if g.get("weight") else None] for g in ings]
    u = r.image_url if isinstance(r.image_url, str) else ""
    rows.append({"i": len(rows), "n": r.recipe_name, "s": s, "c": c, "m": u[len(PREFIX):] if u.startswith(PREFIX) else "",
                 "d": L(r.diet_labels), "u": L(r.cuisine_type), "t": L(r.meal_type), "y": L(r.dish_type), "g": ing,
                 "x": {k: round(tn[k]["quantity"], 2) for k in NUTK if k in tn}})
raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
with open(os.path.join(ROOT, "web", "data", "recipes.json.gz"), "wb") as f: f.write(gzip.compress(raw, 9))
print("Đã ghi", len(rows), "món (bỏ", bad, "dòng hỏng) ->", "web/data/recipes.json.gz")

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from tools._shared import err, fold_text, terms


def extract_keywords(text: str = "", items: list[dict[str, Any]] | None = None, top_k: int = 10) -> dict[str, Any]:
    """Đếm tần suất các từ khóa có nghĩa trong text và/hoặc items, trả về top_k."""
    try:
        parts: list[str] = []
        if text:
            parts.append(str(text))
        for item in items or []:
            if isinstance(item, dict):
                parts.append(str(item.get("title", "")))
                parts.append(str(item.get("summary", "")))
            else:
                parts.append(str(item))

        blob = " ".join(p for p in parts if p).strip()
        if not blob:
            raise ValueError("Cần ít nhất `text` hoặc `items` có nội dung")

        # terms() trả về tập từ "có nghĩa" (đã fold dấu + bỏ stopword) nhưng mất tần
        # suất; nên tokenize lại blob theo cùng quy tắc rồi chỉ giữ token nằm trong tập đó.
        meaningful = terms(blob)
        tokens = re.findall(r"[a-z0-9]+", fold_text(blob))
        counter = Counter(tok for tok in tokens if tok in meaningful)

        k = int(top_k or 10)
        keywords = [{"term": term, "count": count} for term, count in counter.most_common(k)]
        return {"tool": "extract_keywords", "keywords": keywords}
    except Exception as exc:
        return err("extract_keywords", exc)

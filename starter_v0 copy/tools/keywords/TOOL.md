---
name: keywords
track: bonus
kind: local_formatter
provider: none
requires_env: []
inputs: [text, items, top_k]
outputs: [keywords]
side_effect: false
---
# keywords

Trích các từ khóa xuất hiện nhiều nhất từ một đoạn `text` HOẶC từ một danh sách
`items` (mỗi item có thể có `title` / `summary`). Tool chạy hoàn toàn cục bộ
(không gọi API), dùng lại `fold_text` + `terms` trong `tools/_shared.py` để bỏ
dấu tiếng Việt và loại stopword.

Dùng khi đã thu thập được tweet/bài viết và muốn biết những chủ đề/keyword nổi
bật để định hướng tìm tiếp hoặc đặt tiêu đề digest.

## Inputs

- `text` (string, optional): văn bản thô để phân tích.
- `items` (array, optional): danh sách item; gộp `title` + `summary` của từng item.
- `top_k` (integer, default 10): số keyword trả về.

Ít nhất một trong `text` hoặc `items` phải có nội dung.

## Output

```json
{ "tool": "extract_keywords", "keywords": [{"term": "ai", "count": 4}, ...] }
```

# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
>
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. **Xong trước 16:30** để làm tài liệu phụ trợ khi demo. Có thể làm thành poster HTML/SVG (`artifacts/poster.html` / `poster.svg`) để show cho team cùng zone.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. **Có thể hoàn thiện sau buổi debate để nộp bài.**

## Team

- Team: _Bàn B3_
- Members: Phùng Bá Quân - 2A202600866
           Nguyễn Hoàng Long - 2A202600785
           Đỗ Thị Huyền - 2A202600880
- Provider/model: **openai / gpt-4o-mini**

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent: tìm tin theo **từ khóa** hoặc **theo tài khoản**, đọc và tóm tắt **URL** cụ thể, tra **paper arXiv** + **policy nội bộ**, trích **keyword** từ nội dung đã thu thập, tổng hợp thành digest markdown, và **gửi lên Telegram khi user xác nhận**. Agent ưu tiên **route đúng tool + đúng args**, **hỏi lại khi thiếu thông tin** thay vì đoán.

**Link dùng thử (deploy):**

> Chạy local: `streamlit run app.py` (UI trace trong `app.py`). Deploy public bằng Cloudflare Tunnel / Streamlit Cloud rồi dán link.
>
> URL: http://192.168.1.27:8501

## A2. Tool agent có

| Tên tool      | Làm được gì                                                                             | Tool mới nhóm thêm? |
| ------------- | --------------------------------------------------------------------------------------- | ------------------- |
| clarify       | hỏi lại người dùng khi thiếu thông tin (text / yes_no / choice)                         | không               |
| timeline      | lấy tweet gần đây của một tài khoản (`screenname`, `limit`)                             | không               |
| social_search | tìm bài đăng theo từ khóa (`search_type`: Latest/Top)                                   | không               |
| lookup        | tìm web (`topic` general/news, `timeframe`)                                             | không               |
| fetch         | đọc nội dung một URL cụ thể                                                             | không               |
| format        | trình bày các item đã có thành markdown digest                                          | không               |
| send          | gửi text lên Telegram (chỉ khi `confirmed=true`)                                        | không (bonus)       |
| policy        | tra company policy markdown nội bộ                                                      | không (bonus)       |
| papers        | tìm paper trên arXiv                                                                    | không (bonus)       |
| paper_text    | tải PDF arXiv và trích text                                                             | không (bonus)       |
| **keywords**  | **trích keyword nổi bật từ `text`/`items` (chạy cục bộ, bỏ dấu + stopword tiếng Việt)** | **✅ Có**           |

## A3. Câu hỏi mẫu để thử

1. "Tin tức AI hôm nay có gì nổi bật?" → `lookup` (topic=news, timeframe=day)
2. "Lấy 7 tweet mới nhất của Sam Altman" → `timeline` (screenname=sama, limit=7)
3. "Đọc và tóm tắt giúp mình trang này: https://… " → `fetch` (đúng url)
4. "Tìm các paper trên arXiv về diffusion models" → `papers`
5. "Đăng bản tin này lên Telegram giúp mình" → `clarify` (yes_no) trước, chỉ `send` sau khi xác nhận

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version Evidence

Provider/model: openai / gpt-4o-mini · suite `base` (20 case).

| Version | Changed Artifact                                                             | Hypothesis                                                                                                                                                                          | Metric Before |                           Metric After | Run File                                           |
| ------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------: | -------------------------------------: | -------------------------------------------------- |
| v0      | baseline (prompt `eb1c…`, tools `af8e…`)                                     | starter mơ hồ → agent đoán handle/URL, tự gửi, sai args                                                                                                                             |             — |                       **0.65** (13/20) | `runs/v0_B_base_openai_20260602T123150512638.json` |
| v1      | `system_prompt.md` (`05ed…`)                                                 | Thiếu rule "thiếu info → clarify". Thêm rule HỎI LẠI khi thiếu handle/URL                                                                                                           |          0.65 |                       **0.85** (17/20) | `runs/v1_B_base_openai_20260602T123916539757.json` |
| v2      | `system_prompt.md` (`f1d8…`)                                                 | Còn tự `send` + multi-turn rớt (0.667). Thêm rule xác nhận yes_no trước send + carry-over tham số                                                                                   |          0.85 | **0.85** (routing 0.95, multiturn 1.0) | `runs/v2_B_base_openai_20260602T124155344264.json` |
| v3      | `system_prompt.md` (`fe5e…`) + `tools.yaml` (`34049…`, thêm tool `keywords`) | Còn wrong_tool/wrong_arg (`lookup` query="AI news" thay vì query="AI"+topic=news) và out_of_scope vẫn gọi `send`. Thêm routing rules chi tiết + arg convention + xử lý out-of-scope |          0.85 |                       **1.00** (20/20) | `runs/v3_B_base_openai_20260602T151602117617.json` |

> Best base run: **v3** — `case_accuracy 1.0`, `tool_routing 1.0`, `argument 1.0`, `multiturn 1.0`.
> artifact_version: `v3+pfe5e623c3232+t34049e178201`.

## B2. Failure Analysis

Lấy từ `results[*].result.failures` của baseline **v0** (7 case FAIL → đều được fix ở v1–v3).

| Case ID                     | Failure Type   | Actual Tool Calls        | What Failed                  | Fix                                               |
| --------------------------- | -------------- | ------------------------ | ---------------------------- | ------------------------------------------------- |
| R03_web_news_routing        | wrong_tool/arg | `lookup`                 | query="AI news" thay vì "AI" | v3: arg convention — tách topic=news khỏi query   |
| R08_out_of_scope            | out_of_scope   | `send`                   | gọi tool khi nên từ chối     | v3: rule out-of-scope → no tool                   |
| R10_missing_handle          | missing_info   | `timeline`               | đoán handle, thiếu `clarify` | v1: thiếu handle → clarify(text)                  |
| R11_missing_url             | missing_info   | `fetch`                  | đoán URL, thiếu `clarify`    | v1: thiếu URL → clarify(text)                     |
| R12_confirm_before_send     | wrong_boundary | `send`                   | gửi không xác nhận           | v2: clarify(yes_no) trước, send chỉ khi confirmed |
| R13_parallel_web_and_tweets | wrong_tool/arg | `lookup`,`social_search` | query="AI news", topic=None  | v3: convention args + multi-source routing        |
| R14_out_of_scope_coding     | out_of_scope   | `send`                   | gọi tool cho yêu cầu code    | v3: rule out-of-scope                             |

## B3. Team Eval Cases

10 case trong `data/eval_group.json` (5 single + 5 multi turn). Run: `runs/v3_B_group_openai_20260602T151659504483.json` — **10/10 pass (1.0)**.

| Case ID                    | What It Tests                                            | Expected Tool/Behavior                | Result  |
| -------------------------- | -------------------------------------------------------- | ------------------------------------- | ------- |
| G01_fetch_given_url        | Có URL cụ thể → fetch, không lookup                      | `fetch(url)`                          | ✅ pass |
| G02_timeline_limit_arg     | Map "Sam Altman"→sama, trích limit=7                     | `timeline(sama, limit=7)`             | ✅ pass |
| G03_papers_arxiv           | Yêu cầu paper arXiv → papers, không lookup               | `papers`                              | ✅ pass |
| G04_out_of_scope_booking   | Đặt vé ngoài phạm vi → không gọi tool                    | `no_tool`                             | ✅ pass |
| G05_keywords_from_text     | Trích keyword từ text có sẵn → tool mới `keywords`       | `keywords`                            | ✅ pass |
| G06_clarify_then_handle    | (multi) thiếu handle→clarify, lượt sau bổ sung→timeline  | `clarify` → `timeline(sama)`          | ✅ pass |
| G07_carryover_topic_switch | (multi) carry topic=news+timeframe=week, đổi query       | `lookup(news)`                        | ✅ pass |
| G08_confirm_then_send      | (multi) chỉ send với confirmed=true sau khi user yes     | `clarify(yes_no)` → `send(confirmed)` | ✅ pass |
| G09_switch_to_web          | (multi) bỏ social_search → lookup news, giữ chủ đề Tesla | `lookup`                              | ✅ pass |
| G10_correction_limit       | (multi) carry handle elonmusk, sửa limit 10→5            | `timeline(elonmusk, limit=5)`         | ✅ pass |

## B4. Live Chat Evidence

Từ `transcripts/v3_openai_20260602T125448169902.transcript.json` (provider openai, version v3).

| Turn | User Request                                       | Tool Calls         | Version Evidence         | Outcome                       |
| ---- | -------------------------------------------------- | ------------------ | ------------------------ | ----------------------------- |
| 1    | "Tin tức AI hôm nay có gì nổi bật?"                | `lookup`           | routing tin tức → lookup | ✅ đúng tool                  |
| 2    | "Tóm tắt bài viết này hộ mình" (chưa có URL)       | `clarify`          | rule thiếu URL → hỏi lại | ✅ hỏi lại, không đoán        |
| 3    | "https://www.anthropic.com/news/claude-3-5-sonnet" | `fetch`            | đã có URL → fetch        | ✅ đọc đúng URL               |
| 4    | "Đăng bản tin vừa rồi lên Telegram giúp mình"      | `clarify` (yes_no) | rule xác nhận trước send | ✅ hỏi xác nhận, KHÔNG tự gửi |

## B5. Bonus Evidence

| Bonus                  | Evidence File                                           | What Worked                                                  | Risk / Guardrail                                            |
| ---------------------- | ------------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------- |
| send (Telegram)        | transcript turn 4; case G08                             | Hỏi `clarify(yes_no)` trước, chỉ `send` khi `confirmed=true` | Không bao giờ gửi ở lượt đầu / khi chưa xác nhận            |
| arXiv / company policy | `runs/v3_B_extension_openai_20260602T151830023536.json` | Route đúng `papers`/`paper_text`/`policy` (routing 1.0)      | `policy_area` còn chọn sai (xem B6) — cần convention rõ hơn |
| UI                     | `app.py` (Streamlit Live Trace UI)                      | Hiển thị từng tool call/round khi chạy live                  | —                                                           |
| Tool mới `keywords`    | `tools/keywords/`, case G05                             | Trích keyword cục bộ, không gọi lại search                   | Chạy offline, không side-effect                             |

## B6. Reflection

- **Fix thuộc `system_prompt.md`:** rule "thiếu info → clarify" (v1), xác nhận yes_no trước `send` + carry-over multi-turn (v2), routing chi tiết + arg convention (news/timeframe/Top) + xử lý out-of-scope (v3). Đây là nhóm fix tạo ra phần lớn mức tăng 0.65 → 1.0.
- **Fix thuộc `tools.yaml`:** mô tả rõ _khi nào dùng_ mỗi tool + đăng ký tool mới `keywords` (tools_hash đổi `af8e…` → `34049…` ở v3).
- **Failure cần review tay:** extension `policy_area` (E01/E06/E07/E08) — agent route đúng tool `policy` nhưng chọn sai enum `policy_area` (got `all/external_publishing` thay vì `source_citation/ai_research`). Đây là `wrong_arg_value` tinh tế, cần đọc transcript để phán đoán, chấm tự động dễ gây tranh cãi → extension chỉ đạt 6/10 (0.6) dù routing 1.0.
- **Cải thiện tiếp:** thêm convention mapping ý định → `policy_area` trong `tools.yaml`/prompt; bổ sung eval case riêng cho `policy_area` để đo trước/sau.

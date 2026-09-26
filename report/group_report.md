# Báo cáo nhóm — Day 10: Data Pipeline & Data Observability

> Phạm vi bên dưới được phân công ngẫu nhiên theo bốn gói việc đã cân đối; mục tiêu là 25% đóng góp cho mỗi thành viên. Đây là phân công ownership, không phải xác nhận lịch sử commit hay tuyên bố thay thành viên rằng họ đã hoàn thành. Mỗi người cần rà soát và bổ sung phần việc mình thực sự đã làm trước khi nộp.

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | Chưa có tên nhóm trong repository |
| Repository | `K4-L3B-DAY10-TDCH-DataPipelineDataObservability` |
| Ngày trên artifact hiện có | 2026-09-26 |
| URL repository/LMS | Chưa được cung cấp |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò được phân công | Module/deliverable sở hữu | Tỷ trọng mục tiêu |
| --: | --- | --- | --- | --- | ---: |
| 1 | Vũ Quốc Huy | 02929 | Điều phối nền tảng và tích hợp pipeline | `src/core/*`, `src/pipelines/*`, `script/*` | 25% |
| 2 | Tống Trần Tiến Dũng | 02791 | Nền dữ liệu và benchmark | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/evaluation/testset.py` | 25% |
| 3 | Vũ Đức Thiên | 02437 | Corruption và observability | `src/ingestion/corruption.py`, `src/observability/*` | 25% |
| 4 | Nguyễn Hoàng Cường | 02473 | RAG, vector index và scoring | `src/retrieval/*`, `src/evaluation/metrics.py` | 25% |

Tỷ trọng là mục tiêu phân công ngang nhau, được cân đối theo độ phức tạp, đầu ra và trách nhiệm tích hợp; không suy ra từ số lượng file. Thành viên cần đối chiếu phân công với phần việc thực tế và lịch sử commit.

## 2. Tóm tắt kết quả

Repository hiện có pipeline lấy metadata Crossref, chuẩn hóa dữ liệu, tạo embedding và ChromaDB index, kiểm tra chất lượng/freshness, đánh giá trên test set cố định, tạo dữ liệu lỗi có kiểm soát và phục hồi từ raw records. Artifact baseline chứa 24 raw records, 24 clean records và 10 câu hỏi đánh giá. Ở baseline, retrieval hit rate, MAP, MRR, mean token F1 và judge accuracy đều là 100%; Great Expectations 1.x và Freshness SLA đều đạt. Corruption log ghi sáu loại thay đổi: bỏ bản ghi mới nhất, xóa summary, chèn nhiễu, cắt title, làm cũ ngày xuất bản và nhân bản dòng. Artifact corrupted ghi retrieval hit rate 60%, MAP/MRR 53.3%, token F1 70%, judge accuracy 70%; quality gate và freshness đều không đạt. Luồng repair dựng lại dữ liệu từ `data/raw/crossref_records.json`; artifact repaired trở lại 24 dòng, quality/freshness đạt và các metric trích xuất trở lại baseline. Các số liệu này lấy từ artifacts đã có, không được chạy lại trong lượt cập nhật report này. Ragas baseline là skipped; corrupted/repaired báo lỗi do thiếu cấu hình `GOOGLE_API_KEY`. Evaluation trực tiếp LangChain agent hiện là tùy chọn và chưa có kết quả trong artifacts này. Benchmark chỉ có 10 câu nên chưa đại diện cho kiểm thử production.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref API hoặc raw snapshot
  -> parse và lưu raw records
  -> cleaning, chuẩn hóa schema, age_days, text_for_embedding
  -> test set + embeddings MiniLM + ChromaDB
  -> quality/freshness gate + baseline evaluation/report
  -> sáu corruption có log + quality/evaluation
  -> rebuild clean data từ raw records + re-index/re-evaluate
  -> report so sánh baseline/corrupted/repaired
```

| Khối | Input và xử lý chính | Output chính | Owner được phân công |
| --- | --- | --- | --- |
| Nền tảng/orchestration | Settings, đường dẫn artifact, gọi đúng thứ tự các bước baseline và corruption/repair | Hai entrypoint pipeline và artifacts đầu-cuối | Vũ Quốc Huy |
| Ingestion/cleaning/benchmark set | Crossref hoặc snapshot; parse record, loại record thiếu trường bắt buộc, chuẩn hóa/deduplicate, tạo 10 câu hỏi | `data/raw/`, `data/clean/`, `data/eval/test_set.json` | Tống Trần Tiến Dũng |
| Corruption/observability/reporting | Sáu mutation; GX expectations; freshness SLA; tổng hợp kết quả | `corruption_log.json`, `data/quality/`, các report Markdown | Vũ Đức Thiên |
| Retrieval/scoring | Embedding MiniLM, ChromaDB cosine search, QA, judge/metrics | `data/embeddings/`, các metrics và answer JSON | Nguyễn Hoàng Cường |

## 4. Cách tái hiện và cấu hình liên quan

Lệnh được repository hướng dẫn:

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

Artifact hiện có ghi chế độ ưu tiên offline snapshot, 24 raw records, 24 clean records và 10 câu evaluation. Cấu hình trong source đặt `max_results=24`, `top_k=4`, embedding model `sentence-transformers/all-MiniLM-L6-v2`, freshness threshold 180 ngày và ngưỡng stale tối đa 25%. Runtime LLM provider/model có thể được ghi đè qua `.env`; artifact không đủ để xác nhận provider thực tế của lần tạo metric. Ragas baseline được skipped; Ragas corrupted/repaired trả lỗi do thiếu cấu hình API key. Source mới hỗ trợ opt-in evaluation cho LangChain agent bằng `RUN_AGENT_EVALUATION=1`; kết quả đó chưa được tạo trong artifacts hiện có.

Các report/JSON trong `data/` là bằng chứng đã có trong working tree. Lượt này chỉ đọc source và artifact để soạn báo cáo, không chạy lại pipeline hay xác nhận trạng thái môi trường hiện tại.

## 5. Ingestion, cleaning và data contract

- `src/ingestion/crossref.py` parse DOI, title, abstract, author, subject và ngày xuất bản; API có tối đa ba lần thử. Khi không yêu cầu refresh, module ưu tiên raw normalized records đã lưu, sau đó mới đọc snapshot. Raw records là nguồn dùng để repair.
- `src/ingestion/cleaning.py` loại HTML/JATS tag và chuẩn hóa whitespace; bỏ record thiếu `paper_id`, `title`, `summary` hoặc ngày xuất bản hợp lệ; khử trùng lặp theo `paper_id`; tính `age_days` và dựng `text_for_embedding` gồm Title, Authors, Published, Categories, Summary.
- Dataframe clean giữ các trường phục vụ hiển thị, truy vấn và lineage như `paper_id`, `title`, `summary`, `authors`, `categories`, `published`, `updated`, URL và các trường derived.
- Artifact đang có cho thấy 24 raw records và 24 clean records. Không có artifact riêng thống kê số record bị loại bởi từng cleaning rule, nên report không suy đoán các con số đó.

## 6. Evaluation setup

`data/eval/test_set.json` chứa 10 câu hỏi loại `summary`, `authors`, `date`, `categories`; mỗi câu giữ `ground_truth_doc_ids`. Baseline và corruption flow cùng đọc file test set đó. Index mặc định dùng ChromaDB local với cosine distance và `top_k=4`. Scoring hiện có retrieval hit rate, MAP, MRR, token F1 và LLM judge.

Metrics chính hiện vẫn được tạo qua `retrieval.qa.answer_question()` theo metadata/summary của kết quả retrieval. `retrieval.agent.build_agent()` định nghĩa LangChain agent riêng; code mới bổ sung nhánh đánh giá trực tiếp tùy chọn bằng `RUN_AGENT_EVALUATION=1`, lưu câu trả lời riêng và không thay thế metrics trích xuất hiện tại. Nhánh agent chưa được bật trong artifacts đang có. Judge dùng provider cấu hình được và có heuristic fallback. Trạng thái Ragas trong artifacts là baseline skipped, corrupted/repaired error do thiếu cấu hình credentials.

## 7. Kết quả baseline

| Metric | Baseline artifact | Diễn giải |
| --- | ---: | --- |
| Số câu | 10 | Cùng evaluation set được dùng trong corruption flow |
| Retrieval hit rate | 100.0% | 10/10 câu có ít nhất một ground-truth document trong top-k |
| MAP | 100.0% | Mean Average Precision trên các kết quả có thứ hạng |
| MRR | 100.0% | Mean Reciprocal Rank của ground-truth đầu tiên |
| Mean token F1 | 100.0% | Trung bình theo metric token overlap trong `evaluation/metrics.py` |
| Judge accuracy | 100.0% | Theo kết quả judge được lưu trong artifact |
| Mean judge score | 5.00/5 | Trung bình trên 10 câu |
| GX + Freshness | PASS | Engine ghi là `great_expectations_1.x`, 24 dòng |

## 8. Data quality và freshness

Quality gate dùng row-count range 5–5000; non-null cho `paper_id`, `title`, `text_for_embedding`; uniqueness của `paper_id`; và summary dài tối thiểu 30 ký tự. Freshness được tính theo `age_days > 180`; trạng thái đạt khi stale ratio không quá 25%.

| Trạng thái | Dòng | Quality gate | Freshness |
| --- | ---: | --- | --- |
| Baseline | 24 | PASS, GX 1.x | 1/24 stale (4.2%), PASS |
| Corrupted | 23 | FAIL: duplicate IDs và summary quá ngắn | 23/23 stale (100%), FAIL |
| Repaired | 24 | PASS, GX 1.x | 1/24 stale (4.2%), PASS |

## 9. Corruption và repair

| Loại corruption | Số record theo corruption log | Tín hiệu/bằng chứng |
| --- | ---: | --- |
| `drop_latest_records` | 5 | Giảm corpus sau khi bỏ nhóm bản ghi mới nhất |
| `blank_summary` | 1 | Vi phạm độ dài summary; quality report thấy 2 dòng rỗng sau khi có duplicate |
| `inject_summary_noise` | 4 | Summary bị thêm chuỗi ký tự tổng hợp |
| `truncate_title` | 4 | Title bị cắt còn tối đa 7 ký tự |
| `stale_publication_date` | 19 | Tất cả dòng còn lại vượt ngưỡng freshness |
| `duplicate_rows` | 4 | Quality report ghi nhận 8 giá trị paper_id không unique trên 23 dòng |

Luồng repair đọc `data/raw/crossref_records.json`, dựng lại clean dataframe, chạy quality/freshness, tạo repaired index và đánh giá lại. Nó không dùng dataframe corrupted làm nguồn khôi phục.

## 10. So sánh ba trạng thái

| Metric/signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 100.0% | 60.0% | 100.0% |
| MAP | 100.0% | 53.3% | 100.0% |
| MRR | 100.0% | 53.3% | 100.0% |
| Mean token F1 | 100.0% | 70.0% | 100.0% |
| Judge accuracy | 100.0% | 70.0% | 100.0% |
| Mean judge score | 5.00/5 | 3.80/5 | 5.00/5 |
| Quality gate | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |
| Ragas | skipped | error | error |

Trên cùng test set, artifact corrupted cho thấy retrieval hit rate giảm 40 điểm phần trăm và token F1 giảm 30 điểm phần trăm. Sau khi dựng lại từ raw records, cả hai trở về mức baseline. Đây là bằng chứng của lần chạy được phản ánh trong artifacts; để kết luận nhân quả chặt hơn cho từng mutation cần chạy từng kịch bản riêng, hiện corruption flow áp dụng đồng thời cả sáu loại.

## 11. Giới hạn và hướng cải thiện

| Giới hạn quan sát được | Ảnh hưởng | Hướng cải thiện |
| --- | --- | --- |
| Metrics chính dùng `answer_question()`; nhánh `RUN_AGENT_EVALUATION=1` mới thêm nhưng chưa chạy trong artifacts | Chưa có số liệu benchmark trực tiếp cho câu trả lời tự do của LangChain agent | Bật nhánh agent với credentials phù hợp, lưu `*_agent_answers.json` và so sánh riêng |
| Chỉ có 10 câu hỏi | Metric nhạy với từng record và chưa đại diện rộng cho corpus | Mở rộng test set, giữ nguyên phiên bản test set khi so sánh |
| Ragas baseline skipped; corrupted/repaired error do thiếu cấu hình credentials | Chưa có các chỉ số Ragas hợp lệ cho cả ba trạng thái | Chạy Ragas với provider credentials phù hợp và lưu provider/model cùng kết quả |
| Sáu corruption được áp dụng cùng lượt | Không tách được ảnh hưởng của từng lỗi lên từng metric | Chạy từng corruption riêng hoặc theo ablation, lưu cấu hình và seed |
| Chưa tìm thấy test suite trong cây source được kiểm kê | Chưa có kiểm chứng tự động hồi quy cho module contracts | Thêm unit/integration tests và chạy trong CI |

## 12. Hồ sơ cá nhân và xác nhận

Các bản nháp theo phạm vi được phân công nằm tại:

- [`02929_Vu_Quoc_Huy.md`](02929_Vu_Quoc_Huy.md)
- [`02791_Tong_Tran_Tien_Dung.md`](02791_Tong_Tran_Tien_Dung.md)
- [`02437_Vu_Duc_Thien.md`](02437_Vu_Duc_Thien.md)
- [`02473_Nguyen_Hoang_Cuong.md`](02473_Nguyen_Hoang_Cuong.md)

Mỗi thành viên cần xác nhận phần việc trực tiếp thực hiện, bổ sung commit/verification cá nhân và tự viết quyết định kỹ thuật, blocker hoặc bài học của mình. Không dùng phân công này để nhận quyền tác giả cho code nếu lịch sử thực tế không khớp.

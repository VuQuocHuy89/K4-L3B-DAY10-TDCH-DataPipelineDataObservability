# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | TDCH |
| Repository | [K4-L3B-DAY10-TDCH-DataPipelineDataObservability](https://github.com/VuQuocHuy89/K4-L3B-DAY10-TDCH-DataPipelineDataObservability) |
| Ngày hoàn thành/tái hiện | 2026-09-26 (GMT+7) |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| ---: | --- | --- | --- | --- |
| 1 | Vũ Quốc Huy | 02929 | Trưởng nhóm, điều phối và tích hợp pipeline | `src/core/`, `src/pipelines/`, `script/`, `app.py` |
| 2 | Tống Trần Tiến Dũng | 02791 | Nền dữ liệu và benchmark | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/evaluation/testset.py`; cập nhật MAP/MRR và RAGAS reporting |
| 3 | Vũ Đức Thiên | 02437 | Corruption và data observability | `src/ingestion/corruption.py`, `src/observability/`, corruption log và tests |
| 4 | Nguyễn Hoàng Cường | 02473 | RAG, vector index và scoring | `src/retrieval/`, `src/evaluation/metrics.py`, agent evaluation tùy chọn |

Phân công đặt mục tiêu khoảng 25% cho mỗi thành viên. Đây là tỷ trọng kế hoạch theo gói việc; báo cáo cá nhân ghi nhận phần việc và mức đóng góp do từng thành viên tự xác nhận.

## 2. Tóm tắt kết quả

Nhóm TDCH hoàn thiện pipeline thử nghiệm từ snapshot Crossref đến retrieval evaluation, corruption, observability và repair. Snapshot gồm 24 bản ghi metadata bài báo có abstract; nhóm chuẩn hóa dữ liệu, tạo `text_for_embedding`, lập embedding bằng MiniLM và lưu ba collection trong ChromaDB. Bộ benchmark gồm 10 câu hỏi, được giữ nguyên khi so sánh baseline, corrupted và repaired. Baseline đạt retrieval hit rate, MAP, MRR và mean token F1 là 100%; Great Expectations 1.x cùng Freshness SLA đều PASS. Pipeline áp dụng sáu mutation có log. Một số mutation như bỏ record mới nhất, thêm nhiễu summary và cắt ngắn title chưa được quality rules hiện tại phát hiện; toàn bộ corruption kết hợp làm quality/freshness FAIL, hit rate giảm còn 60%, MAP/MRR còn 53.3% và token F1 còn 70%. Khi Quality Gate hoặc Freshness SLA của corrupted dataset thất bại, pipeline tự động kích hoạt `auto_repair_if_needed`, đọc lại raw snapshot, clean và validate lại trước khi re-index. Repair đọc lại raw snapshot, chạy cleaning, quality/freshness, tạo index và đánh giá lại; các chỉ số trở về baseline. Kết quả trigger và validation được ghi tại `data/results/repair_log.json`. Judge dùng heuristic fallback với `LLM_PROVIDER=mock`; RAGAS và agent evaluation trực tiếp chưa chạy. Vì corpus chỉ có 24 metadata records và 10 câu, kết quả chỉ mô tả snapshot thử nghiệm, chưa đại diện cho toàn văn bài báo hay hệ thống production.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API hoặc snapshot đã lưu
  → raw response và normalized raw records
  → parse, cleaning, data contract và text_for_embedding
  → evaluation set cố định
  → MiniLM embeddings và ChromaDB index
  → baseline quality/freshness checks và evaluation
  → sáu corruption có cấu hình, lưu corruption log
  → corrupted quality/freshness checks và evaluation
  → nếu gate FAIL: auto-repair từ raw snapshot hoặc refetch fallback
  → cleaning, validate lại, re-index và evaluation repaired
  → ghi repair_log.json và báo cáo so sánh ba trạng thái
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref response hoặc local snapshot | Parse DOI, title, abstract, authors, categories và ngày; retry khi gọi API | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Tống Trần Tiến Dũng |
| Cleaning | Normalized raw records | Chuẩn hóa text/date, bỏ record thiếu trường bắt buộc hoặc trùng DOI, tạo trường dẫn xuất | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Tống Trần Tiến Dũng |
| Embedding/index | Clean records và `text_for_embedding` | `sentence-transformers/all-MiniLM-L6-v2`, ChromaDB cosine index | `data/embeddings/`, `data/chroma/`, ba collection theo trạng thái | Nguyễn Hoàng Cường |
| Evaluation | Cùng `data/eval/test_set.json` và từng collection | Top-K retrieval, extractive QA, hit rate, MAP/MRR, token F1 và judge | `data/results/*_metrics.json`, `data/results/*_answers.json` | Nguyễn Hoàng Cường; Tống Trần Tiến Dũng cập nhật MAP/MRR và RAGAS reporting |
| Observability | Clean/corrupted/repaired dataframe | Great Expectations 1.x, completeness, uniqueness, summary length và freshness SLA | `data/quality/` | Vũ Đức Thiên |
| Corruption/repair | Baseline clean data, quality/freshness result và raw snapshot | Sáu mutation; tự động trigger repair khi gate FAIL; rebuild và validate repaired dataset | `data/results/corruption_log.json`, `data/results/repair_log.json`, corrupted/repaired artifacts | Vũ Đức Thiên; Vũ Quốc Huy tích hợp auto-repair |
| Orchestration | Settings, raw snapshot và test set | Chạy baseline, corruption, repair theo thứ tự và sinh report | `script/run_phase1.py`, `script/run_corruption_flow.py`, `data/reports/` | Vũ Quốc Huy |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `mock` trong lần xác minh; không gọi LLM bên ngoài |
| `LLM_MODEL` | Giá trị mặc định cấu hình là `gemini-2.5-flash`; không được dùng khi chạy với provider `mock` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | Tối đa 24; lần xác minh dùng 24 records trong snapshot |
| Retrieval `top_k` | 4 |
| Freshness threshold | Record stale nếu `age_days > 180`; SLA cho phép tối đa 25% stale |
| Random seed | Không dùng; test set lưu sẵn, tạo theo thứ tự `paper_id` và không refresh trong lần xác minh |

Không ghi API key hoặc nội dung `.env` vào báo cáo. Lần xác minh dùng snapshot local và `REFRESH_SOURCE=0`, `REFRESH_TEST_SET=0`, `RUN_RAGAS=0`, `RUN_AGENT_EVALUATION=0`.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
LLM_PROVIDER=mock REFRESH_SOURCE=0 REFRESH_TEST_SET=0 RUN_RAGAS=0 RUN_AGENT_EVALUATION=0 \
  uv run python script/run_phase1.py
```

Corruption và repair:

```bash
LLM_PROVIDER=mock REFRESH_SOURCE=0 REFRESH_TEST_SET=0 RUN_RAGAS=0 RUN_AGENT_EVALUATION=0 \
  uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-09-26 | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json`, `data/quality/baseline_quality_report.json` |
| Corruption flow và repair | Thành công | 2026-09-26 | `data/results/corruption_log.json`, `data/results/repair_log.json`, `data/reports/corruption_report.md`, corrupted/repaired metrics và quality reports |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API; lần tái hiện dùng snapshot lưu tại `data/raw/` |
| Endpoint/query | `/works`; query `agentic retrieval augmented generation large language model` |
| Filter | `has-abstract:true` và `from-pub-date` theo cửa sổ 180 ngày được cấu hình |
| Thời điểm lấy dữ liệu | Timestamp của lần gọi API tạo snapshot ban đầu không được lưu trong artifact; lần tái hiện snapshot chạy ngày 2026-09-26, không refresh API |
| Số record nhận được | 24 normalized raw records |
| Retry/backoff | Tối đa 3 lần; lỗi request chờ 1 rồi 2 giây; HTTP 429/503 dùng `Retry-After` tối đa 5 giây hoặc backoff 1/2 giây |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | String | Có | DOI chuẩn hóa thành ID tài liệu | Chuyển chữ thường; bỏ record nếu rỗng |
| `title` | String | Có | Tiêu đề bài báo | Chọn title đầu tiên; làm sạch HTML/whitespace; bỏ record nếu rỗng |
| `summary` | String | Có | Abstract của Crossref | Làm sạch HTML/whitespace; bỏ record nếu rỗng |
| `authors`, `categories` | List[String] | Không | Tác giả và subject/category | Chuẩn hóa text, loại giá trị rỗng/trùng; giá trị thiếu thành list rỗng |
| `published` | ISO date | Có | Ngày xuất bản | Đọc các trường ngày Crossref; bỏ record nếu không chuyển đổi được |
| `updated` | ISO date | Không | Ngày cập nhật/index | Nếu không có giá trị hợp lệ thì dùng `published` |
| `abs_url`, `pdf_url`, `comment` | String | Không | URL và ghi chú từ metadata | `abs_url` fallback sang DOI URL; `pdf_url` fallback sang `abs_url` |
| `primary_category`, `authors_joined`, `categories_joined` | String | Dẫn xuất | Trường đơn/ghép dùng cho QA và metadata | Lấy category đầu tiên và ghép các list đã chuẩn hóa |
| `age_days`, `summary_chars` | Integer | Dẫn xuất | Tuổi record và số ký tự abstract | Tính từ ngày chạy và độ dài summary |
| `text_for_embedding` | String | Dẫn xuất | Title, authors, date, categories và summary ghép thành nội dung index | Tạo theo cùng thứ tự trường cho mọi record |

Snapshot có 24 records trước và sau cleaning; không record nào bị loại trong lần chạy này và cả 24 `paper_id` đều duy nhất. Các bản ghi là metadata thư mục và abstract; repository không lưu toàn văn PDF. Trường `pdf_url` là URL tham chiếu, không phải nội dung PDF đã tải.

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Loại HTML, decode entity và chuẩn hóa whitespace | Consistency/validity | 24 records được xử lý; số trường thay đổi không được thống kê riêng | `src/ingestion/cleaning.py` và clean JSON |
| Bỏ record thiếu DOI/title/abstract/ngày hợp lệ | Completeness/validity | 0 bị loại ở snapshot này (24 → 24) | So sánh số record raw và clean |
| Chuẩn hóa DOI thành chữ thường và khử trùng lặp `paper_id` | Uniqueness | 0 duplicate trong 24 records | Kiểm tra uniqueness trong baseline quality report |
| Tính trường ghép, `age_days`, `summary_chars`, `text_for_embedding` | Consistency | Tạo cho 24 records | Đối chiếu clean schema và embedding manifest |

`paper_id` là document ID dùng trong ChromaDB và `ground_truth_doc_ids`. `age_days` là số ngày giữa ngày chạy và `published`. `text_for_embedding` ghép title, authors, ngày xuất bản, categories và abstract; do corpus không có full text nên câu trả lời chỉ dựa trên metadata/abstract đó.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 |
| Các `question_type` | `summary` (3), `authors` (3), `date` (2), `categories` (2) |
| Ground-truth document ID | Một `paper_id`/DOI cho từng câu hỏi, lưu trong `ground_truth_doc_ids` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2`, vectors được normalize |
| Vector store/collection | ChromaDB persistent, cosine distance; `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | Provider `mock`; judge có heuristic fallback. LLM model mặc định không được gọi |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`; `REFRESH_TEST_SET=0` |

Test set cố định giữ nguyên câu hỏi và ground-truth document IDs giữa baseline, corrupted và repaired, để thay đổi metrics phản ánh khác biệt dữ liệu/index trong cùng benchmark thay vì thay đổi benchmark. QA evaluator trích xuất authors, ngày, category hoặc câu đầu summary từ metadata của tài liệu đứng đầu; metrics vì vậy không phải kết quả của một LLM sinh câu trả lời. Judge fields lần xác minh này là heuristic fallback.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có | Snapshot gồm 24 normalized records |
| Cleaned dataset | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Có | 24 records |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | Collection baseline và manifests |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu hỏi có ground truth |
| Baseline metrics | `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` | Có | 10 samples |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` | Có | Great Expectations 1.x và freshness summary |
| Baseline report | [`data/reports/phase1_report.md`](../data/reports/phase1_report.md) | Có | Tóm tắt pipeline và kết quả baseline |
| Auto-repair log | `data/results/repair_log.json` | Có | Ghi trigger, lý do, nguồn rollback và kết quả validation |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 100.0% | Có tài liệu ground truth trong top-K cho 10/10 câu |
| MAP | 100.0% | Ground-truth result được xếp hạng đầu trong benchmark này |
| MRR | 100.0% | Reciprocal rank trung bình là 1.0 |
| `mean_token_f1` | 100.0% | Token F1 trung bình trên 10 câu |
| `judge_accuracy` | 100.0%* | Kết quả heuristic fallback, không phải LLM judge |
| `mean_judge_score` | 5.00/5* | Kết quả heuristic fallback, không phải LLM judge |
| RAGAS | Skipped | `RUN_RAGAS=0`; không có RAGAS scores |

\* Lần tái hiện đặt `LLM_PROVIDER=mock`; heuristic fallback chấm dựa trên token F1. Xem reasoning trong `data/results/baseline_answers.json` trước khi diễn giải judge metrics.

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `ExpectTableRowCountToBeBetween` | Volume | 5–5000 rows | PASS, 24 rows | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` trên `paper_id`, `title`, `text_for_embedding` | Completeness | Không có null | PASS, 0 null trên mỗi cột | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` trên `paper_id` | Uniqueness | Mỗi paper ID duy nhất | PASS, 24/24 unique | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` trên `summary` | Validity/completeness | Tối thiểu 30 ký tự | PASS | `baseline_quality_report.json` |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Clean dataset trước khi index; trường `age_days` được kiểm tra trong quality report |
| Timestamp mới nhất / cũ nhất | `2026-07-22` / `2026-03-28` |
| Ngưỡng freshness | Stale nếu `age_days > 180`; SLA tối đa 25% stale |
| Trạng thái baseline | PASS; 1/24 stale (4.2%) |
| Lý do | Stale ratio 4.2% không vượt giới hạn 25% |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế / repair |
| --- | --- | ---: | --- | --- |
| `drop_latest_records` | Bỏ 20% records mới nhất theo ngày xuất bản | 5 | Không có completeness/coverage check hiện tại; silent | Cùng lượt chạy với các mutation khác; repair đọc lại raw records |
| `blank_summary` | Xóa summary của một record | 1 | Summary length tối thiểu 30 | Quality check phát hiện; repair dựng lại từ raw |
| `inject_summary_noise` | Thêm chuỗi ký tự nhiễu vào summary | 4 | Không có semantic/noise check hiện tại; silent | Tác động riêng chưa được cô lập; repair dựng lại từ raw |
| `truncate_title` | Cắt title còn 7 ký tự | 4 | Không có title-integrity check hiện tại; silent | Tác động riêng chưa được cô lập; repair dựng lại từ raw |
| `stale_publication_date` | Lùi ngày xuất bản 365 ngày | 19 | Freshness: `age_days > 180`, stale ratio tối đa 25% | Freshness check phát hiện; repair đọc lại ngày trong raw |
| `duplicate_rows` | Nhân bản 20% số records còn lại | 4 | Unique `paper_id` | Uniqueness check phát hiện; repair loại trạng thái corrupted bằng cách rebuild raw |

Corruption log: đường dẫn [`data/results/corruption_log.json`](../data/results/corruption_log.json), trạng thái **Có**. Log ghi 24 input rows, 23 output rows, config, các paper IDs và giá trị trước/sau. Event counts có thể trùng cùng paper ID nên không cộng chúng để tính số records duy nhất. Ba mutation được log là silent: `drop_latest_records`, `inject_summary_noise`, `truncate_title`.

Repair được điều khiển bởi `auto_repair_if_needed` trong `src/pipelines/repair.py`. Hàm chỉ kích hoạt khi Quality Gate hoặc Freshness SLA thất bại. Pipeline ưu tiên rollback từ `data/raw/crossref_records.json`; nếu raw snapshot không đọc được thì dùng Crossref fetch hoặc offline snapshot fallback. Sau đó dữ liệu được cleaning và validate lại trước khi re-index, rồi đánh giá bằng cùng `data/eval/test_set.json`. Quality gate PASS một mình không được xem là bằng chứng phục hồi; nhóm đối chiếu thêm freshness, `repair_log.json` và retrieval/answer metrics với baseline.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Số records sau cleaning | 24 | 23 | 24 | −1 record ròng | Về số lượng baseline | 5 records bị bỏ và 4 bản sao được thêm |
| `retrieval_hit_rate` | 100.0% | 60.0% | 100.0% | −40.0 điểm % | Trở lại baseline | 10 câu benchmark, hit nếu có ground-truth ID trong top-K |
| MAP | 100.0% | 53.3% | 100.0% | −46.7 điểm % | Trở lại baseline | Corruption kết hợp; không quy riêng cho một mutation |
| MRR | 100.0% | 53.3% | 100.0% | −46.7 điểm % | Trở lại baseline | Cùng test set cho cả ba trạng thái |
| `mean_token_f1` | 100.0% | 70.0% | 100.0% | −30.0 điểm % | Trở lại baseline | Answer quality giảm rồi phục hồi trong benchmark |
| `judge_accuracy`* | 100.0% | 70.0% | 100.0% | −30.0 điểm % | Trở lại baseline | Heuristic fallback, không phải LLM judge |
| `mean_judge_score`* | 5.00/5 | 3.80/5 | 5.00/5 | −1.20 điểm | Trở lại baseline | Heuristic fallback |
| Auto-repair status | NOT NEEDED | TRIGGERED | PASS | Corrupted Quality/Freshness fail đã tự động kích hoạt repair | Đạt lại cả hai gate | `repair_log.json` ghi trigger, raw source và kết quả validation |
| Quality checks | PASS | FAIL | PASS | Các check uniqueness và summary length fail | PASS lại | Row count 23 vẫn nằm trong khoảng cho phép |
| Freshness status | PASS, 1/24 stale | FAIL, 23/23 stale | PASS, 1/24 stale | Stale ratio tăng từ 4.2% lên 100% | Trở lại 4.2% | SLA giới hạn stale ratio ở 25% |

\* Judge metrics dùng heuristic fallback do `LLM_PROVIDER=mock`. RAGAS và agent evaluation đều `skipped`; không có score để so sánh.

Hai kết luận từ artifacts:

1. Sáu mutation được áp dụng cùng một lượt → quality checks và freshness báo FAIL, trong đó ba mutation không có detector tương ứng → retrieval hit rate giảm từ 100% xuống 60%, MAP/MRR xuống 53.3% và token F1 xuống 70%.
2. Quality/Freshness fail → `auto_repair_if_needed` tự đọc raw snapshot rồi cleaning, kiểm tra và re-index → quality/freshness trở lại PASS → hit rate, MAP/MRR và token F1 trở về baseline trên cùng 10 câu hỏi.

Do các mutation chạy cùng lượt, kết quả không xác định được mutation riêng lẻ nào gây phần suy giảm lớn nhất.

## 11. Vấn đề tích hợp quan trọng

Vấn đề phát sinh ở ranh giới giữa data quality gate và repair: một số mutation có thể không làm quality gate thất bại, nên chỉ dựa vào PASS/FAIL không đủ xác nhận dữ liệu đã khôi phục.

- **Triệu chứng:** Corruption log ghi `drop_latest_records`, `inject_summary_noise` và `truncate_title` là silent; quality rules hiện tại không phát hiện trực tiếp các trường hợp này.
- **Nguyên nhân:** Gate kiểm tra row-count range, null, uniqueness và summary length; chưa kiểm tra ingestion coverage, title integrity hay nhiễu ngữ nghĩa. Corrupted dataframe cũng không phải nguồn tin cậy để repair.
- **Cách xử lý:** `corruption_flow.py` gọi `auto_repair_if_needed`; khi gate FAIL, hàm ưu tiên nạp lại `data/raw/crossref_records.json`, chạy cleaning mới, quality/freshness, tạo repaired index và đánh giá trên test set cố định.
- **Cách xác minh:** `data/quality/repaired_quality_report.json` và freshness đều PASS; hit rate, MAP/MRR và token F1 của repaired bằng baseline trong `data/results/*_metrics.json`.
- **Cải thiện Auto-Repair:** Code cũ luôn gọi repair sau corruption nhưng chưa dùng kết quả Quality/Freshness để quyết định, nên đó là repair cố định chứ chưa phải self-healing có điều kiện. Code mới dùng `auto_repair_if_needed`, chỉ trigger khi gate FAIL, ghi lý do, validate lại dữ liệu và lưu audit log.
- **Bằng chứng:** `data/results/repair_log.json` ghi `triggered=true`, `source=raw_snapshot`, `output_rows=24`, `quality_success=true` và `freshness_success=true`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Corpus có 24 metadata records kèm abstract, không có toàn văn; benchmark có 10 câu | Kết quả nhạy với từng record và không đại diện cho full-text RAG hoặc production | Tăng corpus và benchmark; cố định phiên bản dữ liệu/test set rồi đo lại các metrics |
| Sáu mutation chạy cùng lượt | Không tách được tác động riêng của từng lỗi | Chạy ablation từng mutation, giữ cùng benchmark và lưu từng log/metric |
| Judge dùng heuristic fallback; RAGAS và agent evaluation chưa chạy | Không có đánh giá độc lập bằng LLM judge/RAGAS/agent cho kết quả này | Cấu hình provider hợp lệ, bật từng nhánh opt-in và lưu kết quả cùng model/provider |
| `drop_latest_records`, summary noise và title truncation là silent với rule hiện tại | Một số vấn đề có thể qua gate mà không tạo cảnh báo trực tiếp | Bổ sung kiểm tra coverage theo raw snapshot, title integrity và rule phát hiện nội dung nhiễu; đo precision/recall detector |
| Auto-repair mới kiểm tra trên snapshot local | Chưa chứng minh được nhánh Crossref refetch thực tế | Làm hỏng hoặc đổi tên raw snapshot trong môi trường test, sau đó kiểm tra fallback fetch/snapshot và ghi repair log |
| `tests/test_corruption.py` có trong repository nhưng chưa chạy trong lần xác minh; chưa có bằng chứng coverage/CI | Chưa xác nhận hồi quy tự động hoặc bonus kiểm thử | Chạy test suite, ghi kết quả và cấu hình CI/coverage trước khi tuyên bố đạt |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository khớp với cấu hình nhóm trong repository.
- [x] Phân công gắn với module, artifacts và đầu ra của pipeline; tỷ trọng 25% là mục tiêu phân công.
- [x] Hai lệnh tái hiện được ghi nhận đã chạy trên snapshot ngày 2026-09-26.
- [x] Baseline, corrupted và repaired dùng cùng `data/eval/test_set.json`.
- [x] Bảng metrics khớp với `data/results/baseline_metrics.json`, `corrupted_metrics.json` và `repaired_metrics.json`.
- [x] Kết luận quality/freshness khớp với các report trong `data/quality/`.
- [x] Đường dẫn report và artifact được ghi trong repository.
- [x] Tất cả thành viên đã hoàn thành và tự xác nhận báo cáo vai trò riêng; các thành viên còn lại cần tự hoàn thiện báo cáo cá nhân trước khi nộp.
- [x] Báo cáo không chứa API key/token; `.env` không được đưa vào commit.

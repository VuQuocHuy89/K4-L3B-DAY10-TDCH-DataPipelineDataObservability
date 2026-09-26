# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Vũ Quốc Huy |
| MSSV | 02929 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | TDCH |
| Vai trò chính | Điều phối nền tảng và tích hợp pipeline; phần việc được phân công khoảng 25% |
| Repository | https://github.com/VuQuocHuy89/K4-L3B-DAY10-TDCH-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cấu hình và tiện ích nền tảng | src/core/config.py, src/core/utils.py | Biến môi trường, cấu hình và đường dẫn project | Settings, Paths và tiện ích đọc/ghi artifacts | Hoàn thành; commit 83b811a |
| Điều phối baseline và corruption/repair | src/pipelines/phase1.py, src/pipelines/corruption_flow.py | Raw records, clean dataframe, test set và Settings | Baseline/corrupted/repaired indexes, metrics và reports | Hoàn thành; commit 83b811a |
| Entrypoints và giao diện demo | script/run_phase1.py, script/run_corruption_flow.py, app.py | Câu hỏi, snapshot và trạng thái pipeline | CLI cho hai luồng; UI trình bày câu trả lời, top-K và từng bước | Hoàn thành; commit 83b811a, 4754e8f |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp retrieval, evaluation và observability vào luồng chạy chung | Các module trong pipeline TDCH | Hai entrypoint tạo artifacts baseline/corrupted/repaired; UI gọi QA và hiển thị top-K |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tích hợp baseline orchestration | src/pipelines/phase1.py, script/run_phase1.py | Clean dataset, quality/freshness reports, index và baseline metrics | Chạy lệnh Phase 1; đối chiếu data/reports/phase1_report.md |
| Tích hợp corruption và repair orchestration | src/pipelines/corruption_flow.py, data/results/corruption_log.json | Corrupted/repaired data, metrics và comparison report | Chạy corruption flow; đối chiếu data/reports/corruption_report.md |
| Tích hợp giao diện demo pipeline | app.py, src/retrieval/qa.py | Chat answer, top-K evidence và điều khiển chạy tiếp từng trạng thái | Chạy Streamlit và truy vấn cùng câu hỏi trên các trạng thái |

Output cụ thể: trên cùng 10 câu hỏi, retrieval hit rate là 100% / 60% / 100%, MAP và MRR là 100% / 53.3% / 100%, token F1 là 100% / 70% / 100% ở baseline / corrupted / repaired. Repair dựng lại từ raw snapshot. Judge metrics của lượt xác minh là heuristic fallback.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần chạy theo đúng thứ tự từ dữ liệu đầu vào đến retrieval evaluation, sau đó tái tạo trạng thái repaired từ nguồn raw. UI cần cho người demo hỏi cùng một câu và quan sát câu trả lời/top-K theo từng bước.

### Cách triển khai

phase1.main() nạp records, làm sạch và ghi CSV/JSON, chạy quality/freshness checks, đọc hoặc tạo evaluation set, tạo vector index, đánh giá và sinh baseline report. corruption_flow.main() nạp baseline artifacts, ghi corruption log, đánh giá corrupted state, rồi đọc lại raw records để dựng repaired dataframe độc lập với corrupted dataframe; sau đó chạy lại checks, indexing và evaluation. app.py gọi các module này theo từng bước và hiển thị câu trả lời cùng top-K results.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | data/raw/crossref_records.json, data/eval/test_set.json, Settings và câu hỏi người dùng |
| Output | Clean data, ChromaDB collections, quality/freshness reports, per-question answers, metrics JSON và UI results |
| Module phụ thuộc | core.config, ingestion, observability, retrieval và evaluation |
| Module sử dụng output | script entrypoints, report generators và app.py |
| Điều kiện lỗi cần xử lý | Raw/test set thiếu, clean dataframe rỗng, baseline metrics không tồn tại, quality gate baseline fail hoặc index không nạp được |

### Cách xác minh

~~~bash
LLM_PROVIDER=mock REFRESH_SOURCE=0 REFRESH_TEST_SET=0 RUN_RAGAS=0 RUN_AGENT_EVALUATION=0 uv run python script/run_phase1.py
LLM_PROVIDER=mock REFRESH_SOURCE=0 REFRESH_TEST_SET=0 RUN_RAGAS=0 RUN_AGENT_EVALUATION=0 uv run python script/run_corruption_flow.py
~~~

- **Kết quả mong đợi:** Hai pipeline hoàn tất, tạo artifacts của ba trạng thái trên cùng evaluation set.
- **Kết quả thực tế:** Lần tái hiện ngày 2026-09-26 hoàn tất; 24 records và 10 câu được dùng. Hit rate 100% / 60% / 100%, MAP/MRR 100% / 53.3% / 100%, token F1 100% / 70% / 100%.
- **Artifact/log:** data/reports/phase1_report.md, data/reports/corruption_report.md, data/results/ và data/quality/. Judge dùng heuristic fallback; RAGAS và agent evaluation được ghi skipped.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Corrupted dataframe không còn là nguồn đáng tin để tạo trạng thái repaired.
- **Các phương án đã cân nhắc:** Vá các mutation trực tiếp trên dataframe lỗi; hoặc dựng lại clean dataframe từ raw snapshot đã lưu.
- **Phương án đã chọn:** Repair nạp data/raw/crossref_records.json, chạy cleaning lại, tạo index repaired và đánh giá bằng cùng data/eval/test_set.json.
- **Lý do:** Cách này tránh giữ lại mutation trong bản repair và giữ nguyên benchmark để so sánh.
- **Bằng chứng quyết định phù hợp:** src/pipelines/corruption_flow.py; repaired quality/freshness PASS và hit rate, MAP/MRR, token F1 trở về mức baseline trong data/results/ và data/reports/corruption_report.md.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Corruption log ghi drop_latest_records, inject_summary_noise và truncate_title là silent với quality rules hiện tại.
- **Lệnh hoặc bước tái hiện:** Chạy corruption flow trên snapshot baseline và đọc data/results/corruption_log.json.
- **Nguyên nhân gốc:** Bộ quality checks kiểm tra row count, null, uniqueness, summary length; Freshness SLA kiểm tra tuổi dữ liệu. Các rule hiện tại không kiểm tra ingestion coverage, summary noise hoặc title bị truncate.
- **Cách xử lý:** Không xem quality PASS riêng lẻ là bằng chứng phục hồi. Repair đọc raw snapshot và kết quả được đối chiếu thêm với freshness cùng retrieval/answer metrics trên test set cố định.
- **Cách xác minh sau khi sửa:** Corrupted quality/freshness FAIL; hit rate giảm còn 60%. Sau repair, quality/freshness PASS và hit rate, MAP/MRR, token F1 về mức baseline.
- **Điều học được:** Cần kiểm tra cả detector signals và tác động downstream; một số mutation cần rule riêng để được phát hiện trực tiếp.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. Crossref snapshot chứa metadata và abstract; parser/cleaning chuẩn hóa chúng thành records và text_for_embedding. MiniLM tạo vectors được lưu trong ChromaDB. Corpus hiện không chứa toàn văn PDF.
2. Mỗi câu evaluation có ground-truth answer và document IDs. Hit rate đo tìm thấy tài liệu liên quan; MAP/MRR đo vị trí xếp hạng; token F1 và judge so câu trả lời với reference.
3. Quality checks kiểm tra cấu trúc và giá trị như null, uniqueness, summary length. Freshness monitoring đo tuổi bản ghi theo ngưỡng 180 ngày và SLA stale tối đa 25%.
4. Cùng test set giữ câu hỏi và ground truth không đổi, giúp so sánh tập trung vào khác biệt của dữ liệu/index.
5. Repair thành công khi dựng từ raw snapshot, quality/freshness đạt và retrieval/answer metrics trở lại baseline trên cùng test set. Quality PASS riêng lẻ không đủ khi có silent mutations.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 100.0% | 60.0% | 100.0% | 4/10 câu không tìm được tài liệu liên quan sau corruption |
| mean_token_f1 | 100.0% | 70.0% | 100.0% | Câu trả lời giảm ở corrupted rồi trở lại baseline |
| judge_accuracy | 100.0%* | 70.0%* | 100.0%* | Heuristic fallback, không phải LLM judge |
| mean_judge_score | 5.00/5* | 3.80/5* | 5.00/5* | Điểm giảm ở corrupted rồi trở về baseline |
| Quality checks | PASS | FAIL | PASS | Đọc cùng quality reports từng trạng thái |
| Freshness status | PASS, 1/24 stale | FAIL, 23/23 stale | PASS, 1/24 stale | SLA cho phép tối đa 25% stale |

* Lượt xác minh dùng LLM_PROVIDER=mock; RAGAS và agent evaluation skipped.

### Kết luận từ số liệu

1. Sáu mutation được áp dụng cùng lượt → corrupted quality/freshness FAIL, trong đó một số mutation được ghi silent → hit rate giảm 100% xuống 60%, MAP/MRR còn 53.3% và token F1 còn 70%.
2. Repair từ raw snapshot → quality/freshness PASS → hit rate, MAP/MRR và token F1 trở lại các giá trị baseline.

Không thể cô lập mutation nào gây suy giảm lớn nhất từ lượt chạy tổng hợp này. Freshness phát hiện 23/23 records stale; uniqueness và summary-length checks cũng báo lỗi. Những mutation bị đánh dấu silent cần được kiểm tra bằng rule riêng hoặc thí nghiệm ablation.

Kết quả đáng chú ý là repaired metrics trùng baseline trên benchmark nhỏ gồm 24 records và 10 câu. Kết quả này xác nhận luồng đã phục hồi trên artifacts hiện tại, chưa đại diện cho corpus lớn hơn.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Repair từ raw snapshot tránh mang dữ liệu corruption sang trạng thái repaired.
2. Baseline, corrupted và repaired cần dùng cùng evaluation set để đối chiếu công bằng.
3. Quality/freshness reports và RAG metrics bổ sung cho nhau; không dùng một quality gate duy nhất để kết luận phục hồi.

### Nếu có thêm thời gian

Chạy ablation từng mutation riêng và bổ sung rule cho ingestion coverage, title integrity và summary noise; đo tỷ lệ phát hiện từng loại lỗi trên mutation suite.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [X] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [X] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [X] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [X] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [X] Báo cáo không chứa .env, API key, token hoặc secret.
- [X] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Quốc Huy
**Ngày xác nhận:** [2026-09-26]

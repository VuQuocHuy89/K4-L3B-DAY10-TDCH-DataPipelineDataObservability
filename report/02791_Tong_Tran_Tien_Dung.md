# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Tống Trần Tiến Dũng           |
| MSSV               | 2A202602791                    |
| Khóa/Lớp         | K4              |
| Tên nhóm         | TDCH     |
| Vai trò chính    | Evaluation & Metrics Extension                 |
| Repository         | `K4-L3B-DAY10-TDCH-DataPipelineDataObservability` |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Bổ sung metric retrieval ranking | `src/evaluation/metrics.py`: `_average_precision`, `_reciprocal_rank`, `evaluate_pipeline` | Evaluation set, `retrieved_doc_ids`, `ground_truth_doc_ids` | `map`, `mrr`, `mean_average_precision`, `mean_reciprocal_rank` trong các file metrics | Hoàn thành |
| Tích hợp RAGAS và xuất kết quả | `src/evaluation/metrics.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/observability/reporting.py` | Câu hỏi, câu trả lời, ground truth và retrieved contexts | Bốn điểm RAGAS, trạng thái chạy và bảng Baseline/Corrupted/Repaired | Hoàn thành phần code; RAGAS score chưa chạy được |
| Bổ sung dependency cho RAGAS | `requirements.txt`, `pyproject.toml` | Dependency của RAGAS | `pillow>=10.0.0` | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Kiểm tra tích hợp pipeline và đối chiếu artifact | Pipeline baseline/corruption/repair | Phát hiện baseline metric cũ chưa có MAP/MRR; đối chiếu và cập nhật kết quả theo `baseline_answers.json` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Bổ sung Average Precision và Reciprocal Rank cho từng câu hỏi, sau đó lấy trung bình thành MAP/MRR | `src/evaluation/metrics.py`, `data/results/*_metrics.json` | Baseline MAP/MRR 100%; Corrupted 53.3%; Repaired 100% | Kiểm tra công thức với các trường hợp hạng 1, hạng 2 và không tìm thấy tài liệu |
| Bổ sung RAGAS theo cơ chế opt-in và lưu bốn metric thành phần | `src/evaluation/metrics.py`, `data/reports/corruption_report.md` | Có các trường `answer_relevancy`, `context_precision`, `context_recall`, `faithfulness`; trạng thái lỗi được lưu thay vì làm dừng pipeline | Chạy với `RUN_RAGAS=1`; artifact hiện ghi thiếu `GOOGLE_API_KEY` |
| Hiển thị MAP/MRR/RAGAS trong các script | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/observability/reporting.py` | Console và comparison report có đủ MAP, MRR và trạng thái RAGAS | Đối chiếu output console và `data/reports/corruption_report.md` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Artifact chính là `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json` và `data/reports/corruption_report.md`. Trên cùng test set 10 câu, MAP/MRR lần lượt là `100.0% / 53.3% / 100.0%` cho Baseline/Corrupted/Repaired.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các metric ban đầu chỉ cho biết có tìm thấy tài liệu đúng hay không và chất lượng câu trả lời. Phần Evaluation bổ sung các metric có xét thứ hạng tài liệu trả về (MAP, MRR), đồng thời tích hợp RAGAS để đánh giá answer relevancy, context precision, context recall và faithfulness. Mục tiêu là phân biệt rõ lỗi retrieval ranking với lỗi sinh câu trả lời.

### Cách triển khai

Với mỗi câu hỏi, `retrieved_doc_ids` được xem là danh sách đã xếp hạng và `ground_truth_doc_ids` là tập tài liệu đúng. Average Precision cộng precision tại các vị trí có tài liệu liên quan rồi chia cho số tài liệu liên quan; Reciprocal Rank lấy `1/rank` của tài liệu đúng đầu tiên. MAP và MRR là trung bình các giá trị đó trên 10 câu hỏi.

RAGAS được bật có điều kiện bằng biến môi trường `RUN_RAGAS=1`. Pipeline ánh xạ các cột nội bộ sang schema RAGAS, chạy bốn metric, lấy trung bình theo toàn bộ câu hỏi và lưu cả `status`, `scores`, `error` nếu dependency hoặc credential chưa sẵn sàng. Khi không bật cờ, RAGAS ở trạng thái `skipped` để không làm chậm các lần chạy MAP/MRR thông thường.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `test_set.json`, `retrieved_doc_ids`, `ground_truth_doc_ids`, câu trả lời và retrieved contexts           |
| Output                         | Per-question `average_precision`, `reciprocal_rank`; summary `map`, `mrr`; RAGAS `status` và `scores` |
| Module phụ thuộc             | `retrieval.qa`, `retrieval.index`, `retrieval.llm`, `retrieval.embeddings`                    |
| Module sử dụng output        | `phase1.py`, `corruption_flow.py`, `reporting.py`, các file trong `data/results/`        |
| Điều kiện lỗi cần xử lý | Không có tài liệu đúng; danh sách rỗng; RAGAS chưa bật; thiếu Pillow, model embedding hoặc credential LLM |

### Cách xác minh

```bash
$env:PYTHONPATH = "src"
python -m py_compile src/evaluation/metrics.py src/observability/reporting.py src/pipelines/phase1.py src/pipelines/corruption_flow.py
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Ba trạng thái dùng cùng evaluation set và console/report hiển thị Hit Rate, MAP, MRR, Token F1, LLM Judge Accuracy và RAGAS status.
- **Kết quả thực tế:** Kiểm tra công thức MAP/MRR đạt; Baseline `100%/100%`, Corrupted `53.3%/53.3%`, Repaired `100%/100%`. RAGAS chưa có điểm số thật vì lần bật RAGAS thiếu `GOOGLE_API_KEY`; lỗi được ghi trong metrics thay vì làm mất kết quả cũ.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần đo chất lượng retrieval có xét thứ hạng, nhưng không được làm mất các metric cũ hoặc khiến pipeline luôn phụ thuộc vào LLM judge/RAGAS.
- **Các phương án đã cân nhắc:** (1) chỉ dùng Hit Rate; (2) tính MAP/MRR từ thứ hạng document ID; (3) chỉ dùng điểm semantic từ LLM/RAGAS.
- **Phương án đã chọn:** Giữ Hit Rate và Token F1, bổ sung MAP/MRR từ document ID; RAGAS chạy opt-in bằng `RUN_RAGAS=1`.
- **Lý do:** MAP/MRR có tính tái lập, không phụ thuộc LLM và phản ánh vị trí tài liệu đúng. RAGAS cung cấp đánh giá ngữ nghĩa nhưng tốn thời gian, cần model/credential và có thể phát sinh chi phí.
- **Bằng chứng quyết định phù hợp:** Khi corruption làm hỏng ranking, MAP/MRR giảm từ `100%` xuống `53.3%`; khi repair từ raw snapshot, cả hai phục hồi về `100%`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Baseline hiển thị `MAP 0.0%` và `MRR 0.0%` trong khi Hit Rate là `100.0%`.
- **Lệnh hoặc bước tái hiện:** Chạy corruption flow với `baseline_metrics.json` được tạo trước khi bổ sung hai metric mới.
- **Nguyên nhân gốc:** File baseline metrics cũ không có khóa `map` và `mrr`; phần report dùng giá trị mặc định `0.0` khi thiếu khóa, không phải retrieval thực tế bằng 0.
- **Cách xử lý:** Tính lại từ `baseline_answers.json`, đồng bộ baseline artifact và yêu cầu chạy lại Phase 1 trước Corruption Flow sau mỗi thay đổi schema metric.
- **Cách xác minh sau khi sửa:** 10/10 câu có tài liệu đúng ở hạng 1; baseline MAP/MRR là `1.0/1.0`, repaired cũng là `1.0/1.0`.
- **Điều học được:** Artifact sinh ra từ phiên bản code cũ có thể làm report sai dù code mới đúng; phải kiểm tra schema và thời điểm tạo metric trước khi kết luận.

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** Bốn điểm RAGAS chưa được ghi nhận; MAP/MRR và các metric còn lại không bị ảnh hưởng.
- **Những gì đã loại trừ:** Đã kiểm tra công thức MAP/MRR, schema metrics và artifact per-question; lỗi hiện tại nằm ở credential/dependency của RAGAS.
- **Bước tiếp theo:** Cài dependency từ `requirements.txt`, cấu hình credential đúng với `LLM_PROVIDER`, bật `RUN_RAGAS=1` và chạy lại Phase 1 trước Corruption Flow.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

Crossref trả về raw JSON. Module ingestion parse và chuẩn hóa thành `PaperRecord`, lưu raw response/raw records để có thể repair offline. Cleaning tạo DataFrame, chuẩn hóa text, tính `age_days`, tạo `text_for_embedding`, loại dòng lỗi và trùng `paper_id`. Index sinh embedding MiniLM và lưu vector trong ChromaDB cùng metadata.

Evaluation set gồm 10 câu hỏi thuộc bốn loại `summary`, `authors`, `date`, `categories`; mỗi câu có `ground_truth` và `ground_truth_doc_ids`. Hit Rate kiểm tra có tài liệu đúng trong danh sách trả về; MAP/MRR còn xét tài liệu đúng đứng ở vị trí nào; Token F1 và LLM Judge đánh giá câu trả lời.

Quality checks kiểm tra điều kiện dữ liệu tại một thời điểm, như số dòng, null, uniqueness và độ dài summary. Freshness monitoring theo dõi `age_days` và tỷ lệ tài liệu cũ; dữ liệu có thể hợp lệ về schema nhưng vẫn quá cũ.

Phải dùng cùng test set để baseline, corrupted và repaired vì nếu câu hỏi hoặc ground truth thay đổi thì chênh lệch metric không còn phản ánh riêng tác động của corruption.

Repair thành công khi raw snapshot tạo lại được cleaned dataset hợp lệ, quality/freshness trở lại PASS, đồng thời các metric retrieval/answer phục hồi về gần baseline. Trong kết quả này MAP, MRR, Hit Rate và Token F1 đều phục hồi về `100%`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 100.0% | 60.0% | 100.0% | Corruption làm mất tài liệu liên quan trong top-k ở 4/10 câu. |
| `map` | 100.0% | 53.3% | 100.0% | Chất lượng xếp hạng giảm rõ rệt vì tài liệu đúng không còn luôn ở vị trí đầu. |
| `mrr` | 100.0% | 53.3% | 100.0% | Vị trí tài liệu đúng đầu tiên giảm trung bình sau corruption. |
| `mean_token_f1`      | 100.0% | 70.0% | 100.0% | Nội dung trả lời giảm do context bị thiếu hoặc hỏng. |
| `judge_accuracy`     | 100.0% | 70.0% | 100.0% | LLM judge/fallback đánh giá 3/10 câu corrupted là không đúng hoàn toàn. |
| `mean_judge_score`   | 5.00/5 | 3.80/5 | 5.00/5 | Repair khôi phục chất lượng câu trả lời. |
| RAGAS status         | skipped | error | error | Chưa có điểm RAGAS; baseline chưa bật, corrupted/repaired thiếu credential LLM. |
| Quality checks         | PASS | FAIL | PASS | Corrupted vi phạm uniqueness và summary length. |
| Freshness status       | PASS | FAIL | PASS | Baseline stale `1/24 = 4.17%`; corrupted `23/23 = 100%`. |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. Corruption gồm drop record, blank summary, inject noise, truncate title, stale date và duplicate rows → Quality Gate phát hiện duplicate/summary ngắn, freshness chuyển FAIL với `23/23` stale → Hit Rate giảm `100% → 60%`, MAP/MRR giảm `100% → 53.3%`, Token F1 giảm `100% → 70%`.
2. Repair đọc lại raw snapshot thay vì sửa trên corrupted frame → quality/freshness trở lại PASS → Hit Rate, MAP, MRR và Token F1 phục hồi về `100%`; LLM Judge Accuracy cũng trở lại `100%`.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Corruption ảnh hưởng rõ nhất là nhóm thay đổi nội dung/identity của tài liệu dùng cho retrieval, đặc biệt blank summary, truncate title và drop latest records. Blank summary và title ngắn làm embedding/context mất tín hiệu; drop record khiến một số ground-truth document không còn trong index. Các thay đổi này giải thích việc Hit Rate giảm còn 60% và MAP/MRR còn 53.3%.

Kết quả nào khác với kỳ vọng ban đầu?

Kết quả ban đầu dễ gây hiểu nhầm là baseline MAP/MRR bằng 0 dù Hit Rate bằng 100%. Kiểm tra `baseline_answers.json` cho thấy cả 10 tài liệu đúng đều đứng ở hạng 1. Nguyên nhân là baseline metrics được tạo từ schema cũ chưa có khóa MAP/MRR; sau khi đồng bộ artifact, hai metric trở về 100%. RAGAS cũng chưa có điểm số vì chưa cấu hình credential phù hợp cho provider hiện tại.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Metric phải đi cùng version/schema của artifact; chạy pipeline theo đúng thứ tự và cùng evaluation set là điều kiện để so sánh có ý nghĩa.
2. Quality Gate phát hiện lỗi cấu trúc còn freshness phát hiện lỗi thời gian; cả hai bổ sung cho nhau.
3. Dữ liệu hỏng không nhất thiết làm hệ thống crash nhưng có thể làm giảm ranking và chất lượng câu trả lời RAG rõ rệt.

### Nếu có thêm thời gian

Cấu hình provider/credential RAGAS riêng cho môi trường chạy và bổ sung test tự động cho MAP/MRR, schema metrics và fallback khi thiếu dependency. Đo bằng việc pipeline tạo được bốn điểm RAGAS hợp lệ, không có `status=error`, đồng thời giữ MAP/MRR nhất quán giữa JSON và report.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Tự điền]
**Ngày xác nhận:** 2026-09-26

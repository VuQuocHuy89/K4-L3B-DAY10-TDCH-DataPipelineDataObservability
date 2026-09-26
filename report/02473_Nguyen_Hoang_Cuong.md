# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Hoàng Cường             |
| MSSV               | 02473                     |
| Khóa/Lớp         | K4-L3B              |
| Tên nhóm         | TDCH     |
| Vai trò chính    | RAG, vector index và scoring                 |
| Repository         | https://github.com/VuQuocHuy89/K4-L3B-DAY10-TDCH-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Embedding và vector index | `src/retrieval/embeddings.py`, `src/retrieval/index.py` | Clean records và metadata | MiniLM embeddings, ChromaDB collections và manifests | Hoàn thành theo phân công |
| Retrieval, QA và scoring | `src/retrieval/qa.py`, `src/evaluation/metrics.py` | Câu hỏi, test set và index | Top-K results, answers và metrics JSON | Hoàn thành; artifacts baseline/corrupted/repaired có sẵn |
| Agent evaluation tùy chọn | `src/retrieval/agent.py`, `src/evaluation/metrics.py` | Câu hỏi, test set và index | Agent answers JSON và summary metrics riêng | Đã triển khai; chưa bật trong artifacts. Commit `393c488`, Git ghi tác giả `unknown` với email khớp danh sách nhóm |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Không khai báo | — | — |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tạo embedding và lập index riêng theo trạng thái | `src/retrieval/embeddings.py`, `src/retrieval/index.py`, `data/embeddings/` | MiniLM embeddings và ChromaDB collections baseline/corrupted/repaired | Embedding manifests và cấu hình index |
| Truy xuất, QA và scoring | `src/retrieval/qa.py`, `src/evaluation/metrics.py`, `data/results/` | Top-K answers và metrics trên cùng test set | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` |
| Bổ sung agent scoring tùy chọn | `src/evaluation/metrics.py`, `src/retrieval/agent.py`, commit `393c488` | Agent answers và summary riêng khi bật `RUN_AGENT_EVALUATION=1` | Đối chiếu commit và source; nhánh chưa chạy trong artifacts |

Nổi bật: retrieval hit rate baseline/corrupted/repaired là 100%/60%/100%; MAP/MRR là 100%/53.3%/100%; mean token F1 là 100%/70%/100%.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Tìm đúng tài liệu và đánh giá chất lượng retrieval/answer trên baseline, corrupted và repaired bằng cùng một test set.

### Cách triển khai

Dùng MiniLM tạo embedding và ChromaDB lưu index riêng cho từng trạng thái. Retrieval lấy top-K kết quả; QA evaluator hiện tại tạo câu trả lời trích xuất và tính hit rate, MAP, MRR, token F1 cùng judge scores. Commit `393c488` thêm nhánh LangChain agent scoring tùy chọn, lưu kết quả riêng và chuẩn hóa output dạng text/content blocks.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean records, test set và ground-truth document IDs |
| Output                         | ChromaDB collections, top-K results, answers và metric JSON |
| Module phụ thuộc             | `src/core/config.py`, `src/evaluation/testset.py`, `src/retrieval/llm.py` |
| Module sử dụng output        | Pipeline baseline và corruption/repair |
| Điều kiện lỗi cần xử lý | Index/model/provider không khả dụng; test set rỗng; agent provider lỗi |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Ba trạng thái dùng cùng test set; repair khôi phục retrieval/QA metrics.
- **Kết quả thực tế:** Artifacts hiện có cho thấy corrupted giảm metrics và repaired trở lại mức baseline. Pipeline không được chạy lại khi soạn báo cáo.
- **Artifact/log:** `data/embeddings/*.json`, `data/results/*_metrics.json`, `data/results/*_answers.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần đánh giá LangChain agent mà vẫn giữ nguyên kết quả QA evaluator hiện có.
- **Các phương án đã cân nhắc:** Thay evaluator hiện tại bằng agent; luôn chạy cả hai; hoặc thêm agent evaluator tùy chọn.
- **Phương án đã chọn:** Thêm nhánh `RUN_AGENT_EVALUATION=1`, lưu answer JSON và scores riêng.
- **Lý do:** Không thay đổi metrics hiện tại và chỉ phát sinh agent calls khi được bật.
- **Bằng chứng quyết định phù hợp:** Commit `393c488`; nhánh agent chưa chạy nên chưa có agent metrics.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Metrics hiện tại có thể bị hiểu nhầm là kết quả LangChain agent.
- **Lệnh hoặc bước tái hiện:** Gọi `evaluate_pipeline()` với cấu hình mặc định.
- **Nguyên nhân gốc:** Evaluator mặc định gọi `answer_question()`; agent không được gọi.
- **Cách xử lý:** Thêm nhánh agent evaluation riêng và cờ bật tùy chọn trong commit `393c488`.
- **Cách xác minh sau khi sửa:** Đối chiếu source và flag; artifacts hiện tại không có kết quả agent vì nhánh chưa được bật.
- **Điều học được:** Cần ghi rõ metric thuộc QA evaluator hay agent evaluator.

## 7. Hiểu biết về luồng end-to-end

1. Clean records được embedding bằng MiniLM rồi ghi vào ChromaDB theo từng trạng thái.
2. Evaluation set cung cấp câu hỏi và ground-truth document IDs để đo retrieval/answer quality.
3. Quality checks kiểm tra schema/nội dung; freshness đo độ cũ của records theo SLA.
4. Dùng cùng test set giữ phép so sánh baseline, corrupted và repaired nhất quán.
5. Repair được đối chiếu qua quality/freshness status và việc metrics retrieval/QA trở lại mức baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 100% | 60% | 100% | Retrieval giảm khi corrupted và phục hồi sau repair |
| `mean_token_f1`      | 100% | 70% | 100% | Cùng xu hướng với retrieval |
| `judge_accuracy`     | 100% | 70% | 100% | QA evaluator; không phải agent evaluation |
| `mean_judge_score`   | 5.00/5 | 3.80/5 | 5.00/5 | Điểm phục hồi sau repair |
| Quality checks         | PASS | FAIL | PASS | Tín hiệu dữ liệu đi kèm kết quả retrieval |
| Freshness status       | PASS | FAIL | PASS | Corrupted vượt SLA freshness |

### Kết luận từ số liệu

1. Corruption tổng hợp → quality/freshness fail → retrieval hit rate giảm 40 điểm phần trăm và token F1 giảm 30 điểm phần trăm.
2. Repair từ raw records → quality/freshness pass → retrieval và QA metrics trở lại baseline.

Freshness cho thấy tín hiệu rõ nhất với dữ liệu cũ; do nhiều corruption chạy cùng lượt nên chưa thể tách mức ảnh hưởng retrieval của từng loại. Artifacts không ghi kỳ vọng cá nhân trước khi chạy; agent evaluation chưa có số liệu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Collection riêng giúp so sánh retrieval giữa các trạng thái mà không ghi đè index.
2. Cần giữ nguyên test set và ground-truth IDs để metrics có thể so sánh.
3. QA metrics hiện tại không đại diện cho chất lượng LangChain agent.

### Nếu có thêm thời gian

Bật agent evaluation với provider credentials, chạy trên cùng test set và so sánh riêng với QA evaluator; mở rộng test set để đánh giá ổn định hơn.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hoàng Cường
**Ngày xác nhận:** 2026-09-26

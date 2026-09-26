# Báo cáo vai trò cá nhân — Day 10: Data Pipeline & Data Observability

> Báo cáo này được điền từ source code và artifacts hiện có cho phạm vi Nguyễn Hoàng Cường được phân công. Các nhận định về kết quả pipeline dựa trên artifacts trong repository. Vui lòng xác nhận phần việc/commit cá nhân và các trải nghiệm chỉ người thực hiện mới biết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Hoàng Cường |
| MSSV | 02473 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | Chưa đặt tên trong repository |
| Vai trò được phân công | RAG, vector index và scoring |
| Tỷ trọng mục tiêu | 25% |
| Repository | `K4-L3B-DAY10-TDCH-DataPipelineDataObservability` |
| Ngày lập bản báo cáo | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc được phân công

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái theo repository |
| --- | --- | --- | --- | --- |
| Embedding và vector index | `retrieval/embeddings.py`; `retrieval/index.py`: `LocalEmbeddingIndex.build/search/lookup` | Clean dataframe có `paper_id`, `title`, `text_for_embedding` và metadata | ChromaDB collections, search results, `data/embeddings/*.json` manifests | Source và artifacts có trong repo; cần đối chiếu commit cá nhân |
| QA và LLM clients | `retrieval/qa.py`; `retrieval/agent.py`; `retrieval/llm.py` | Câu hỏi, index, Settings/provider config | Extractive answer hoặc LangChain agent response | Source có trong repo; evaluator hiện gọi QA trích xuất |
| Evaluation metrics | `evaluation/metrics.py`: `evaluate_pipeline`, hit rate, MAP, MRR, token F1, judge, optional Ragas | Test set, index và Settings | Metrics JSON và per-question answers JSON | Ba bộ metric artifacts có sẵn; code hiện có thêm nhánh agent evaluation opt-in |

### Việc hỗ trợ ngoài phạm vi chính

Repository không cung cấp bằng chứng đủ để xác nhận hoạt động hỗ trợ cá nhân ngoài phạm vi trên. Bổ sung phần này nếu bạn đã trực tiếp hỗ trợ thành viên hoặc tích hợp module khác.

## 3. Kết quả theo vai trò

| Nhiệm vụ trong phạm vi | File/hàm/artifact liên quan | Kết quả quan sát được | Cách đối chiếu |
| --- | --- | --- | --- |
| Tạo embedding và lập index local | `retrieval/embeddings.py`, `retrieval/index.py`, `data/chroma/`, `data/embeddings/` | Source cấu hình `sentence-transformers/all-MiniLM-L6-v2`; index dùng ChromaDB cosine và collection riêng cho baseline/corrupted/repaired | Đọc collection name/model trong manifests và cấu hình `core/config.py` |
| Tìm tài liệu và tạo câu trả lời | `retrieval/index.py`, `retrieval/qa.py` | Tìm kiếm top-k; câu hỏi có title trong dấu nháy đơn được exact lookup ưu tiên; answer lấy từ metadata hoặc câu đầu summary | Đối chiếu test set và per-question answer JSON |
| Tính metric cho ba trạng thái | `evaluation/metrics.py`; `data/results/*_metrics.json` | Hit rate: 100%/60%/100%; MAP/MRR: 100%/53.3%/100%; token F1 và judge accuracy: 100%/70%/100% | Đọc các file baseline/corrupted/repaired metrics |
| Đánh giá trực tiếp LangChain agent theo chế độ opt-in | `evaluation/metrics.py`, `retrieval/agent.py` | `RUN_AGENT_EVALUATION=1` tạo agent answers riêng và summary token F1/judge | Đối chiếu source; chưa bật/chạy nhánh này trong artifacts hiện có |

**Output cụ thể:** corruption làm retrieval hit rate giảm 40 điểm phần trăm, MAP/MRR giảm từ 100% xuống 53.3%, và mean token F1 giảm 30 điểm phần trăm. Artifact repaired trở lại các mức baseline. Ragas baseline được skipped; corrupted/repaired ghi trạng thái error vì thiếu cấu hình `GOOGLE_API_KEY`; không có key value trong báo cáo.

## 4. Giải thích phần kỹ thuật

### Vấn đề cần giải quyết

Phần retrieval/scoring biến clean records thành vector index để tìm paper liên quan, sau đó đo xem cùng một bộ câu hỏi có tìm đúng tài liệu và tạo câu trả lời gần ground truth hay không ở baseline, corrupted và repaired.

### Cách triển khai trong source hiện tại

`MiniLMEmbeddings` nạp `SentenceTransformer` và cache model; embedding document/query được chuẩn hóa. `LocalEmbeddingIndex.build()` dựng document từ `text_for_embedding` và metadata, xóa rồi tạo lại collection theo trạng thái, lưu vectors vào ChromaDB persistent với cosine distance, đồng thời ghi manifest. `search()` chuyển distance thành score; `lookup()` hỗ trợ exact paper ID/title.

`answer_question()` truy vấn index và trích câu trả lời theo loại câu hỏi: tác giả, ngày xuất bản, category hoặc câu đầu summary. `evaluate_pipeline()` đọc test set, tính retrieval hit bằng cách so `retrieved_doc_ids` với `ground_truth_doc_ids`, tính token F1 và gọi judge có structured output. Nếu judge không khả dụng, code dùng heuristic dựa trên token F1. Ragas chỉ chạy khi bật `RUN_RAGAS`.

Metrics chính hiện vẫn gọi `answer_question()` để giữ tương thích với kết quả trích xuất. Mình đã bổ sung nhánh agent evaluation riêng, bật bằng `RUN_AGENT_EVALUATION=1`; nhánh này gọi `build_agent()`/`run_agent_question()`, lưu answer JSON riêng theo từng trạng thái và trả summary riêng trong `agent_evaluation`. Mặc định nhánh bị tắt nên không làm phát sinh LLM calls hay thay đổi metrics cũ. `run_agent_question()` cũng chuẩn hóa kết quả message dạng string hoặc content blocks thành chuỗi text. Nhánh mới chưa được chạy trong artifacts hiện có; cần provider credentials để tạo kết quả thực.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean dataframe gồm `paper_id`, `title`, `text_for_embedding`, `published`, `authors_joined`, `categories_joined`, `summary`, URL; test set gồm question, ground truth và document IDs |
| Output | ChromaDB collection, `SearchResult`, answer records, metrics summary và JSON artifacts |
| Module phụ thuộc | `core.config.Settings`; clean data từ `ingestion.cleaning`; câu hỏi từ `evaluation.testset`; provider clients từ `retrieval.llm` |
| Module sử dụng output | `pipelines.phase1` và `pipelines.corruption_flow` gọi index/evaluator để tạo baseline, corrupted và repaired results |
| Điều kiện lỗi cần xử lý | Model/provider không khả dụng; collection hoặc manifest thiếu; dataframe/test set rỗng; không tìm thấy tài liệu; metric judge phải ghi nhận heuristic fallback |

### Cách xác minh

Các lệnh do repository hướng dẫn để tạo lại artifacts:

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

Hai lệnh chưa được chạy lại trong lượt soạn báo cáo. Kết quả hiện có được đối chiếu trực tiếp trong các JSON dưới đây.

- **Kết quả mong đợi:** Ba trạng thái dùng cùng `data/eval/test_set.json`; corrupted có thể giảm retrieval/answer metrics; repaired được dựng từ raw records và được đánh giá lại.
- **Kết quả trong artifact hiện có:** Baseline hit rate/MAP/MRR/token F1 đều 100%; corrupted lần lượt 60%/53.3%/53.3%/70%; repaired trở lại 100%.
- **Artifact:** `data/embeddings/papers_embeddings*.json`, `data/results/*_metrics.json`, `data/results/*_answers.json`, `data/eval/test_set.json`.
- **Agent evaluation mới:** Đặt `RUN_AGENT_EVALUATION=1` để sinh các file `*_agent_answers.json` và summary riêng. Chưa chạy trong lượt này.
- **Runtime LLM provider/model:** Metrics artifacts cho thấy Ragas corrupted/repaired lỗi do thiếu `GOOGLE_API_KEY`; provider/model runtime không được xác nhận đầy đủ. Không ghi API key vào báo cáo.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần đo câu trả lời của agent nhưng vẫn giữ metrics trích xuất trước đó ổn định và tránh LLM calls khi chưa bật.
- **Các phương án có thể dùng:** Thay hẳn evaluator hiện tại bằng agent; luôn chạy đồng thời hai luồng; hoặc thêm agent evaluator riêng, opt-in.
- **Phương án được thể hiện trong code:** `RUN_AGENT_EVALUATION=1` bật luồng agent riêng; mặc định bỏ qua; kết quả và answer JSON tách khỏi evaluator trích xuất.
- **Lý do kỹ thuật:** Giữ khả năng so sánh metrics cũ, đồng thời cho phép benchmark agent thực khi provider credentials sẵn sàng.
- **Bằng chứng:** `_run_agent_evaluation()` trong `evaluation/metrics.py`, `run_agent_question()` trong `retrieval/agent.py`, `.env.example`. Nhánh agent chưa được chạy để tạo metric.

## 6. Một lỗi hoặc blocker đã xử lý

Không có issue log hoặc commit attribution trong repository để xác nhận một lỗi đã được cá nhân xử lý. Qua đối chiếu source, có một điểm cần lưu ý khi diễn giải kết quả:

- **Triệu chứng:** Có thể hiểu nhầm các metrics là chất lượng câu trả lời của LangChain agent.
- **Nguyên nhân gốc:** `evaluate_pipeline()` gọi `answer_question()`; hàm này tạo câu trả lời trích xuất theo metadata/summary. `build_agent()` không được gọi trong evaluator.
- **Cách xử lý trong code:** Thêm nhánh agent evaluation opt-in riêng, lưu answers tách biệt và trả status/scores; chuẩn hóa output của agent để hỗ trợ message content dạng text blocks.
- **Cách xác minh:** Đối chiếu lời gọi trong `evaluation/metrics.py`, `retrieval/agent.py` và flag trong `.env.example`. Chưa chạy nhánh mới do cần provider credentials.
- **Trạng thái:** Code path đã được thêm trong working tree; chưa có artifact agent evaluation hoặc lần chạy xác nhận. Metrics artifacts hiện tại vẫn là evaluator trích xuất.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được parser thành `PaperRecord`; cleaning chuẩn hóa và tạo `text_for_embedding`. Index chuyển nội dung thành vector MiniLM, ghi vào ChromaDB cùng metadata.
2. Mỗi câu evaluation có ground-truth answer và `ground_truth_doc_ids`. Retrieval được tính hit nếu ít nhất một ID trong top-k khớp; answer được so với ground truth bằng token F1 và judge.
3. Quality checks xác minh cấu trúc/nội dung như row count, non-null, uniqueness và độ dài summary. Freshness riêng đo tỷ lệ dòng có `age_days > 180`, cho phép tối đa 25% stale.
4. Dùng cùng test set giúp khác biệt metric giữa baseline/corrupted/repaired phản ánh thay đổi dữ liệu/index thay vì thay đổi câu hỏi hoặc ground truth.
5. Repair thành công trong artifacts khi clean data trở lại 24 dòng, quality/freshness pass, retrieval hit rate và token F1 trở lại baseline 100%. Repair flow dùng `data/raw/crossref_records.json` làm nguồn, không dùng corrupted dataframe.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 100.0% | 60.0% | 100.0% | Giảm 40 điểm phần trăm rồi trở về baseline |
| `map` | 100.0% | 53.3% | 100.0% | Thứ hạng tài liệu liên quan giảm rồi hồi phục |
| `mrr` | 100.0% | 53.3% | 100.0% | Vị trí tài liệu đúng đầu tiên giảm rồi hồi phục |
| `mean_token_f1` | 100.0% | 70.0% | 100.0% | Giảm 30 điểm phần trăm rồi được phục hồi |
| `judge_accuracy` | 100.0% | 70.0% | 100.0% | Cùng xu hướng với token F1 trong artifacts |
| `mean_judge_score` | 5.00/5 | 3.80/5 | 5.00/5 | Điểm trung bình giảm khi corrupted và phục hồi sau repair |
| Quality checks | PASS | FAIL | PASS | Corrupted fail uniqueness và summary length |
| Freshness status | PASS, 1/24 stale | FAIL, 23/23 stale | PASS, 1/24 stale | Corrupted stale ratio 100%, vượt SLA 25% |
| Ragas status | skipped | error | error | Corrupted/repaired thiếu cấu hình `GOOGLE_API_KEY`; không có key value trong artifact |

### Kết luận từ số liệu

1. Sáu mutation được áp dụng cùng lượt → quality report phát hiện duplicate IDs/summary ngắn và freshness báo 23/23 stale → retrieval hit rate giảm từ 100% xuống 60%, token F1 giảm từ 100% xuống 70%.
2. Repair dựng lại clean dataframe từ raw records → quality/freshness trở lại PASS → hit rate, token F1 và judge accuracy trở lại 100%.

Corruption flow áp dụng đồng thời sáu loại lỗi nên artifacts hiện tại không cô lập được lỗi nào gây suy giảm retrieval nhiều nhất. Stale-date có tín hiệu freshness rõ nhất (100% stale); duplicate và summary length có bằng chứng trực tiếp trong quality checks. Không nên quy toàn bộ suy giảm RAG cho riêng một mutation khi chưa chạy ablation. Agent evaluation mới được tắt mặc định, nên bảng này không phải kết quả trực tiếp của agent.

Các artifact không lưu kỳ vọng cá nhân trước khi chạy, nên không thể xác nhận kết quả nào trái với kỳ vọng ban đầu. Ragas baseline bị skipped, còn corrupted/repaired báo lỗi credentials. Nhánh agent evaluation đã được thêm nhưng không có metric trong artifacts hiện tại vì chưa bật/chạy.

## 9. Điều học được và hướng cải thiện

### Ba điều rút ra từ phần kỹ thuật

1. Giữ collection riêng cho từng trạng thái giúp so sánh retrieval mà không ghi đè index trước đó.
2. Evaluation cần giữ nguyên test set và ground-truth IDs; nếu không, metric giữa các trạng thái không còn phép so sánh công bằng.
3. Quality/freshness signal cho biết dữ liệu có vi phạm kiểm tra, còn metrics cho thấy hệ quả downstream; cần đọc cả hai cùng với per-question answers.

### Nếu có thêm thời gian

Bật `RUN_AGENT_EVALUATION=1` trong môi trường có provider credentials hợp lệ, chạy lại baseline và corruption flow, rồi đối chiếu `*_agent_answers.json` và summary `agent_evaluation`. Sau đó bổ sung kiểm thử output agent dạng string/content blocks và chạy Ragas với provider credentials phù hợp.

## 10. Cam kết của thành viên

Các ô xác nhận dưới đây cần được Nguyễn Hoàng Cường tự đánh dấu sau khi rà soát phần việc và lịch sử thực tế:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end và module được phân công.
- [x] Các kết luận metric trong bản nháp có artifact trong repository để đối chiếu.
- [x] Bản nháp không khẳng định pipeline đã được chạy lại trong lượt soạn này.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo phân biệt evaluator trích xuất với LangChain agent.

**Họ và tên:** Nguyễn Hoàng Cường
**Ngày lập bản nháp:** 2026-09-26
**Ngày xác nhận cá nhân:** Chờ thành viên xác nhận

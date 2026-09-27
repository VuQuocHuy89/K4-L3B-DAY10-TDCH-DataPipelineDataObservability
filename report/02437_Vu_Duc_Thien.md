# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Vũ Đức Thiện          |
| MSSV               | 2A202602437                  |
| Khóa/Lớp         | K4              |
| Tên nhóm         | TDCH     |
| Vai trò chính    | Corruption & Data Observability                 |
| Repository         | `K4-L3B-DAY10-TDCH-DataPipelineDataObservability` |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Corruption suite có cấu hình | `src/ingestion/corruption.py`: `CorruptionConfig`, `corrupt_clean_dataframe`, `_refresh_derived_fields`; export trong `src/ingestion/__init__.py` | Clean DataFrame baseline (24 dòng) do `build_clean_dataframe` tạo ra | Corrupted DataFrame 23 dòng, được lưu thành `data/clean/papers_clean_corrupted.{csv,json}` | Hoàn thành |
| Detection log cho từng mutation | `src/ingestion/corruption.py`: `EXPECTED_DETECTORS`, `_event`, `_change` | Sáu mutation và các quality rule đang có trong `src/observability/quality.py` | `data/results/corruption_log.json` gồm config, 6 event, `expected_detectors`, cờ `silent`, giá trị before/after của từng bản ghi | Hoàn thành |
| Test suite cho corruption | `tests/test_corruption.py` (19 test) | Fixture 10 bài báo đi qua `build_clean_dataframe` thật | Kiểm tra sáu mutation, tính tất định, input không bị sửa, validate config và đối chiếu với quality gate | Hoàn thành, 19/19 pass |
| Đối chiếu tín hiệu Quality/Freshness | `src/observability/quality.py`: `_manual_expectation_results`, `_freshness_payload` (code gate do Huy tích hợp ở `83b811a`; tôi dùng lại để kiểm chứng) | Corrupted DataFrame, ngưỡng `freshness_threshold_days=180` | Xác nhận detector map khớp với `data/quality/{baseline,corrupted,repaired}_quality_report.json` | Hoàn thành phần kiểm chứng |

Commit có thể đối chiếu: `35484b0` — *feat: configurable corruption suite with detection log and tests* (3 file, +345/−49).

Liên hệ với thành viên khác:

- **Input:** clean DataFrame lấy từ `build_clean_dataframe` (Dũng). Corruption dựa vào schema này (`paper_id`, `title`, `summary`, `published`, `age_days`, `authors_joined`, `categories_joined`).
- **Output:** `corruption_flow.py` (Huy) gọi `corrupt_clean_dataframe` rồi chạy quality gate và build collection corrupted (Cường). Gate fail do corruption gây ra kích hoạt `auto_repair_if_needed` (Dũng).

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Đối chiếu artifacts của ba trạng thái baseline/corrupted/repaired | Luồng nhóm (`src/pipelines/corruption_flow.py`, báo cáo nhóm) | Corrupted: gate FAIL (uniqueness, summary length, freshness 23/23 stale). Repaired: gate PASS, 24 dòng, không còn noise, title ngắn hay summary rỗng; đủ 5 bản ghi đã bị drop |
| Kiểm tra lý do trigger auto-repair | Tống Trần Tiến Dũng — `src/pipelines/repair.py` | Ba `reasons` trong `data/results/repair_log.json` trùng với ba detector non-silent trong `EXPECTED_DETECTORS` (uniqueness, summary length, freshness) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Tham số hóa sáu mutation bằng `CorruptionConfig` (frozen dataclass, validate trong `__post_init__`). Giá trị mặc định cho ra đúng corrupted output như trước khi refactor | `src/ingestion/corruption.py`, `src/ingestion/__init__.py` | Corrupted dataset 24 → 23 dòng; config đã dùng được ghi vào log | `test_default_config_row_counts`, `test_custom_config_changes_severity`, `test_invalid_config_is_rejected` (7 trường hợp) |
| Ghi detection log có before/after và detector kỳ vọng cho từng mutation | `corruption.py`, `data/results/corruption_log.json` | 6 event với count 5/1/4/4/19/4; `silent_failures` gồm 3 loại | `test_log_records_before_and_after_values`, `test_detection_metadata_matches_detector_map` |
| Viết bộ test pytest cho corruption | `tests/test_corruption.py` | 19 test pass | `python -m pytest tests/test_corruption.py -q` |
| Đối chiếu quality gate với corruption log | `data/quality/*_quality_report.json`, `data/quality/freshness_report.json` | Corrupted fail đúng 2/6 expectation và freshness; baseline/repaired pass cả hai | `test_quality_gate_flags_only_the_non_silent_failures` và đọc lại các file JSON |
| Truy vết từng câu hỏi bị sai về mutation gây ra lỗi | `data/results/corrupted_answers.json` + `corruption_log.json` | Bảng nguyên nhân ở mục 8 (4 retrieval miss, 3 câu trả lời sai) | Ghép `ground_truth_doc_ids` với `paper_ids` của từng event |

Output cụ thể mà phần việc của tôi tạo ra:

`data/results/corruption_log.json` của lần chạy nhóm ghi `input_rows=24`, `output_rows=23` cùng sáu event:

| Event | Count | Detector kỳ vọng | Silent |
| --- | ---: | --- | :---: |
| `drop_latest_records` | 5 | — | ✔ |
| `blank_summary` | 1 | `ExpectColumnValueLengthsToBeBetween(summary, min_value=30)` | |
| `inject_summary_noise` | 4 | — | ✔ |
| `truncate_title` | 4 | — | ✔ |
| `stale_publication_date` | 19 | Freshness SLA (`age_days > 180` trên hơn 25% số dòng) | |
| `duplicate_rows` | 4 | `ExpectColumnValuesToBeUnique(paper_id)` | |

Mỗi thay đổi đều có before/after. Ví dụ title `Automated Data Quality Profiling with Great Expectations in CI/CD` → `Automat`, hoặc `published` `2026-04-18` → `2025-04-18`. Nhờ vậy, khi metric giảm có thể truy ngược đến đúng bản ghi và đúng mutation.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Muốn chứng minh observability hoạt động thì cần một bộ lỗi dữ liệu có kiểm soát, chạy lại cho ra cùng kết quả, và biết trước lỗi nào gate phải bắt được. Bản trước commit `35484b0` hard-code mọi tham số (`0.20`, `blank_indexes = [0]`, 365 ngày). Log khi đó chỉ có `type`, `count`, `paper_ids`: không có giá trị trước/sau, không biết lỗi nào quality gate sẽ phát hiện và không có test. Vì vậy khi metric corrupted giảm, nhóm không truy được câu hỏi nào hỏng vì mutation nào, cũng không biết lỗi nào đã lọt qua gate.

### Cách triển khai

**Sáu mutation theo thứ tự cố định:**

1. `drop_latest_records`: sắp xếp theo `published` giảm dần (sort stable), bỏ `ceil(n × 0.20)` bản ghi mới nhất. Mutation này mô phỏng việc bỏ lỡ một cửa sổ ingestion. Số dòng bị bỏ tối thiểu là 1 và luôn chừa lại ít nhất 1 dòng.
2. Sau bước drop, sắp xếp lại theo `paper_id` rồi chia các dòng đầu thành **ba nhóm không giao nhau**: `blank_summary` (1 dòng), `inject_summary_noise` (`ceil(n × group_ratio)` dòng, nối thêm chuỗi `" ### %% CORRUPTION_NOISE_7xQ @@@"`) và `truncate_title` (nhóm kế tiếp, cắt title còn 7 ký tự). Các nhóm tách rời nên ảnh hưởng của mỗi mutation lên metric có thể quy về đúng một nguyên nhân.
3. `stale_publication_date`: lùi `published` của mọi dòng còn lại 365 ngày và cộng thêm 365 vào `age_days`, để cảnh báo freshness chắc chắn xảy ra.
4. `duplicate_rows`: nối thêm bản sao của `ceil(n × 0.20)` dòng đầu.
5. Cuối cùng `_refresh_derived_fields` tính lại `summary_chars` và `text_for_embedding`. Nếu bỏ bước này, cột `summary`/`title` bị hỏng nhưng index vẫn embed text cũ, và retrieval sẽ không thấy corruption.

**`CorruptionConfig`** là frozen dataclass giữ mức độ của từng mutation. `__post_init__` từ chối cấu hình vô nghĩa: tỉ lệ nằm ngoài `(0, 1]`, `truncated_title_length` ngoài `1..7` (để title luôn ngắn hơn 8 ký tự), `stale_shift_days ≤ 0`, hoặc `noise_suffix` chỉ có khoảng trắng.

**`EXPECTED_DETECTORS`** ánh xạ mỗi mutation sang quality rule được kỳ vọng sẽ bắt nó. Danh sách rỗng nghĩa là **silent failure**: dữ liệu vẫn qua gate nhưng câu trả lời RAG bị ảnh hưởng. Mỗi event trong log ghi `expected_detectors`, `silent` và `changes` (before/after, cắt ở 60 ký tự). Phần đầu log ghi `input_rows`, `output_rows`, `config` và `silent_failures`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean DataFrame theo schema của `build_clean_dataframe`; `output_log_path`; `CorruptionConfig` tùy chọn (mặc định là cấu hình tham chiếu của lab) |
| Output                         | DataFrame mới cùng schema, với `summary_chars` và `text_for_embedding` đã được tính lại; DataFrame input **không bị sửa**; file JSON log tại `output_log_path` |
| Module phụ thuộc             | `ingestion/cleaning.py` (schema), `core/utils.write_json`, các rule trong `observability/quality.py` (cơ sở cho detector map) |
| Module sử dụng output        | `pipelines/corruption_flow.py` (ghi corrupted CSV/JSON, chạy `run_data_quality_checks(..., "corrupted")`, build collection corrupted, evaluate), `pipelines/repair.py` (trigger dựa trên kết quả gate) |
| Điều kiện lỗi cần xử lý | DataFrame rỗng → `ValueError`; config ngoài miền hợp lệ → `ValueError`; `published` không parse được ở bước drop → `errors="coerce"`; `age_days` không phải số → coerce về 0; tỉ lệ drop quá lớn → giới hạn còn `len - 1`. Bước stale dùng `date.fromisoformat`, nên phụ thuộc vào việc cleaning đã chuẩn hóa ngày về dạng ISO |

### Cách xác minh

```bash
$env:PYTHONPATH = "src"
python -m pytest tests/test_corruption.py -q
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả 19 test pass. Corruption log có đủ sáu event theo đúng thứ tự. Corrupted quality report chỉ fail ở các detector non-silent. Baseline và repaired pass cả Quality lẫn Freshness.
- **Kết quả thực tế:** `19 passed in 6.44s` (chạy lại ngày 2026-09-27). Artifacts từ lần chạy corruption flow của nhóm (2026-09-26): corrupted gate chạy bằng engine `great_expectations_1.x`, fail `ExpectColumnValuesToBeUnique` và `ExpectColumnValueLengthsToBeBetween`, freshness `23/23` stale. Baseline và repaired đều PASS, `1/24` stale (4.2%).
- **Artifact/log:** `data/results/corruption_log.json`, `data/quality/baseline_quality_report.json`, `data/quality/corrupted_quality_report.json`, `data/quality/repaired_quality_report.json`, `data/quality/freshness_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần cho phép điều chỉnh mức độ corruption. Tuy vậy, các thành viên khác đã dùng corrupted output hiện tại để tính MAP/MRR, build index và viết báo cáo, nên kết quả mặc định không được thay đổi.
- **Các phương án đã cân nhắc:**
  1. Corruption ngẫu nhiên theo xác suất và random seed.
  2. Corruption tất định theo vị trí (sau khi sort theo `paper_id`), các nhóm không giao nhau, tham số nằm trong `CorruptionConfig` với giá trị mặc định giống bản cũ.
  3. Giữ nguyên hard-code và chỉ bổ sung log.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Cùng input luôn cho cùng output và log giống nhau từng byte, nên metric của ba trạng thái so sánh được giữa các lần chạy và giữa các thành viên. Nhóm tách rời giúp quy mỗi thay đổi metric về một mutation. Random có seed vẫn phụ thuộc phiên bản thư viện và dễ tạo nhóm chồng nhau (một bản ghi vừa blank vừa bị cắt title), khiến việc quy nguyên nhân khó hơn. Phương án 3 không cho phép thử mức độ khác nhau.
- **Bằng chứng quyết định phù hợp:** `test_corruption_is_deterministic` so sánh hai lần chạy (DataFrame và file log giống hệt nhau). `test_failure_groups_do_not_overlap` xác nhận ba nhóm tách rời. Số lượng event trong artifact nhóm (5/1/4/4/19/4) khớp với cấu hình mặc định, và các metric corrupted (`60%` hit rate, `53.3%` MAP/MRR) mà nhóm đã báo cáo vẫn giữ nguyên.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Hit Rate của corrupted giảm từ `100%` xuống `60%`, nhưng `corrupted_quality_report.json` chỉ báo lỗi uniqueness, summary length và freshness. Không có tín hiệu nào cho việc **mất 5 bản ghi mới nhất**, trong khi đây chính là nguyên nhân của cả 4 câu retrieval miss.
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_corruption_flow.py`, sau đó đối chiếu `corrupted_answers.json` với `corruption_log.json`. Bốn câu `eval_002`, `eval_004`, `eval_007`, `eval_008` có `retrieval_hit=false`, và `ground_truth_doc_ids` của cả bốn đều nằm trong `paper_ids` của `drop_latest_records`.
- **Nguyên nhân gốc:** Các quality rule hiện tại chỉ kiểm tra thuộc tính tĩnh của một batch. `ExpectTableRowCountToBeBetween(5, 5000)` là khoảng tuyệt đối nên 23 dòng vẫn đạt, và không có rule nào so số dòng với baseline. Cũng không có rule về độ dài title hay ký tự bất thường trong summary. Vì vậy 3/6 mutation (`drop_latest_records`, `inject_summary_noise`, `truncate_title`) lọt qua gate.
- **Cách xử lý:** Tôi làm cho các lỗi này hiển thị rõ thay vì để chúng lẫn trong trạng thái FAIL chung. Cụ thể: thêm `EXPECTED_DETECTORS`, cờ `silent` và danh sách `silent_failures` vào log; thêm test `test_quality_gate_flags_only_the_non_silent_failures`. Test này chạy rule thật (bản pandas tương đương bộ GX) trên dữ liệu corrupted và yêu cầu tập rule fail **đúng bằng** tập detector non-silent. Nếu ai thêm hoặc bớt rule mà không cập nhật detector map thì test sẽ fail.
- **Cách xác minh sau khi sửa:** 19/19 test pass. Log ghi `silent_failures = ["drop_latest_records", "inject_summary_noise", "truncate_title"]`. Corrupted report fail đúng hai expectation và freshness như detector map dự đoán.
- **Điều học được:** Một trạng thái PASS/FAIL tổng không cho biết gate đang bỏ sót gì. Cần ghi rõ lỗi nào được kỳ vọng bắt bởi rule nào, lỗi nào đang silent, và giữ ánh xạ đó bằng test.

Phần chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** Quality gate trong `src/observability/quality.py` chưa bắt được ba silent failure. Trong luồng hiện tại, auto-repair vẫn được kích hoạt nhờ freshness và uniqueness fail; nhưng nếu chỉ riêng drop/noise/truncate xảy ra thì gate vẫn PASS và repair sẽ không chạy.
- **Những gì đã loại trừ:** Không phải do GX lỗi (engine là `great_expectations_1.x` và không có `gx_error`). Không phải do mutation không được áp dụng (test `test_each_failure_is_applied` và before/after trong log xác nhận).
- **Bước tiếp theo:** Thêm ba rule:
  - Số `paper_id` **duy nhất** tối thiểu so với baseline (ví dụ ≥ 90%). Không dùng tổng số dòng, vì duplicate đã bù lại (23/24 = 95.8% vẫn đạt), trong khi số `paper_id` duy nhất chỉ còn 19/24 = 79.2%.
  - `ExpectColumnValueLengthsToBeBetween(title, min_value=8)`: baseline có title ngắn nhất 55 ký tự.
  - `ExpectColumnValuesToNotMatchRegex(summary, "[#%@]{2,}")`: không khớp dòng nào ở baseline, khớp 7 dòng ở corrupted (4 bản ghi noise cộng 3 bản sao).

  Sau đó cập nhật `EXPECTED_DETECTORS` và chạy lại test để `silent_failures` về rỗng, đồng thời baseline/repaired vẫn PASS.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. `fetch_source_records` lấy dữ liệu từ Crossref API (hoặc snapshot offline) và lưu `data/raw/crossref_response.json`, `crossref_records.json`. Hai file này về sau là nguồn để repair. Payload được parse thành `PaperRecord`, sau đó `build_clean_dataframe` chuẩn hóa text, tính `age_days`, ghép `text_for_embedding` và loại trùng, cho ra 24 dòng trong `data/clean/`. Phase 1 chỉ index khi quality gate chạy bằng engine `great_expectations_1.x`. `LocalEmbeddingIndex.build` embed `text_for_embedding` bằng MiniLM và lưu vào ChromaDB, mỗi trạng thái (baseline/corrupted/repaired) một collection riêng.
2. `data/eval/test_set.json` có 10 câu hỏi thuộc bốn loại: summary, authors, date, categories. Mỗi câu có `ground_truth` (đáp án) và `ground_truth_doc_ids` (tài liệu chứa đáp án). Retrieval được đo bằng cách so `retrieved_doc_ids` với `ground_truth_doc_ids` (hit, AP, RR → Hit Rate, MAP, MRR). Chất lượng câu trả lời được đo bằng token F1 giữa `answer` và `ground_truth`, cùng LLM judge. Trong artifacts hiện tại, judge dùng fallback heuristic vì LLM evaluator không khả dụng.
3. Quality checks kiểm tra dữ liệu có **đúng** không tại thời điểm kiểm: đủ số dòng, không null, `paper_id` duy nhất, summary ≥ 30 ký tự. Freshness kiểm tra dữ liệu có còn **mới** không: tỉ lệ dòng có `age_days > 180` không được vượt 25%. Hai loại lỗi độc lập với nhau. Ví dụ trong corruption: `stale_publication_date` không vi phạm rule cấu trúc nào nhưng làm freshness fail (23/23 stale), còn `blank_summary` vi phạm quality nhưng không ảnh hưởng freshness.
4. Nếu câu hỏi hoặc ground truth thay đổi giữa các trạng thái, chênh lệch metric có thể đến từ test set chứ không phải từ dữ liệu. Giữ nguyên test set thì dữ liệu là biến duy nhất thay đổi. Việc `ground_truth_doc_ids` cố định cũng giúp phát hiện được việc một tài liệu bị drop khỏi index.
5. Có ba lớp bằng chứng. (a) `data/results/repair_log.json`: `triggered=true`, `source=raw_snapshot`, `output_rows=24`, `quality_success=true`, `freshness_success=true`. (b) `repaired_quality_report.json` PASS, với 1/24 dòng stale như baseline. (c) `repaired_metrics.json` trở về mức baseline: Hit Rate, MAP, MRR, token F1 và judge accuracy đều `100%`. Tôi kiểm thêm dữ liệu repaired: 24 `paper_id` duy nhất, đủ 5 bản ghi từng bị drop, không còn noise suffix, title < 8 ký tự hay summary < 30 ký tự.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 100.0% | 60.0% | 100.0% | Cả 4 câu miss (`eval_002/004/007/008`) đều có tài liệu đúng nằm trong 5 bản ghi bị `drop_latest_records` loại bỏ. |
| `map` / `mrr` | 100.0% | 53.3% | 100.0% | 4 câu miss có RR = 0. `eval_010` có tài liệu bị `truncate_title` (`Automat`) nên tụt xuống hạng 3 (RR = 0.333). Tổng 5.333/10. |
| `mean_token_f1`      | 100.0% | 70.0% | 100.0% | 3 câu sai: `eval_001` (blank summary → câu trả lời rỗng), `eval_003` (stale date → trả `2025-04-18` thay vì `2026-04-18`), `eval_007` (tài liệu bị drop → trả ngày của bài khác). |
| `judge_accuracy`     | 100.0% | 70.0% | 100.0% | Đúng 3 câu như token F1, vì judge đang dùng fallback heuristic. |
| `mean_judge_score`   | 5.00 | 3.80 | 5.00 | 7 câu × 5 điểm + 3 câu × 1 điểm = 38/10. |
| Quality checks         | PASS (6/6) | FAIL (4/6) | PASS (6/6) | Corrupted fail uniqueness (4 bản sao) và summary length (1 summary rỗng). 3 mutation còn lại là silent. |
| Freshness status       | PASS (1/24 stale, 4.2%) | FAIL (23/23 stale, 100%) | PASS (1/24 stale, 4.2%) | Lùi ngày 365 ngày đẩy mọi dòng qua ngưỡng 180 ngày. |

### Kết luận từ số liệu

1. `stale_publication_date` + `duplicate_rows` + `blank_summary` → freshness FAIL (23/23), `ExpectColumnValuesToBeUnique` và `ExpectColumnValueLengthsToBeBetween` FAIL → token F1 và judge accuracy giảm từ `100%` xuống `70%` (câu trả lời rỗng ở `eval_001`, ngày lệch đúng 1 năm ở `eval_003`). Song song đó, `drop_latest_records` là **silent**, không có tín hiệu nào, nhưng kéo Hit Rate xuống `60%` và MAP/MRR xuống `53.3%`.
2. Gate fail → `auto_repair_if_needed` dựng lại dữ liệu từ `data/raw/crossref_records.json` → 24 dòng, Quality và Freshness đều PASS → toàn bộ metric retrieval và answer phục hồi về `100%`, bằng baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest_records` ảnh hưởng mạnh nhất. Nó gây ra cả 4 retrieval miss (−40 điểm Hit Rate) và phần lớn mức giảm MAP/MRR (4.0 trong tổng 4.667 điểm AP bị mất). Tài liệu không còn trong index thì không có cách nào lấy lại được. Đây cũng là lỗi nguy hiểm nhất vì là silent failure: số dòng giảm từ 24 xuống 19 (trước khi bị nhân bản) vẫn nằm trong khoảng 5–5000 nên gate không báo. Nếu không có freshness và uniqueness fail đi kèm, pipeline sẽ index dữ liệu thiếu mà không có cảnh báo nào.

Kết quả nào khác với kỳ vọng ban đầu?

- **Answer metric che giấu retrieval failure.** 3/4 câu miss retrieval (`eval_002`, `eval_004`, `eval_008`) vẫn có F1 = 1.0. Tôi kiểm tra clean data thì thấy mỗi bài bị drop đều có một bài "song sinh" trùng authors/categories: `3671802` ↔ `3671814`, `3671804` ↔ `3671816`, `3671808` ↔ `3671820`. Retriever trả về bài song sinh nên câu trả lời trùng hợp đúng. Nếu chỉ nhìn token F1 (70%), nhóm sẽ đánh giá thấp mức hỏng thực tế của retrieval (60%).
- **`inject_summary_noise` không làm giảm metric nào.** Cả 4 bản ghi bị noise đều trả lời đúng. Nguyên nhân: `retrieval/qa.py` trả lời câu summary bằng `first_sentence(summary)`, còn noise được nối vào **cuối** summary nên không lọt vào câu trả lời. Với QA extractive hiện tại, mutation này còn quá yếu; muốn đo đúng thì phải chèn noise vào đầu hoặc giữa summary.
- **Bản sao chiếm chỗ trong top-K.** `eval_004` nhận `3671801` hai lần, `eval_007` nhận `3671803` hai lần. Duplicate không chỉ vi phạm uniqueness mà còn chiếm slot của tài liệu khác trong kết quả retrieval.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Mutation phải đi đến tận thứ mà retrieval thực sự nhìn thấy. Nếu không tính lại `text_for_embedding` sau khi sửa `title`/`summary`, index vẫn dùng text cũ và corruption không có tác dụng. Mỗi field dẫn xuất cần được tính lại hoặc kiểm tra lại sau khi dữ liệu gốc thay đổi.
2. **Data quality/observability:** Gate FAIL không có nghĩa là gate đã bắt đủ lỗi. Trong 6 mutation, gate chỉ bắt được 3. Rule dạng khoảng tuyệt đối (row count 5–5000) không phát hiện được việc mất 20% dữ liệu. Cần ánh xạ lỗi → detector, ghi rõ silent failure, và dùng test để giữ ánh xạ đó đồng bộ với rule thật.
3. **Ảnh hưởng đến RAG agent:** Metric câu trả lời có thể đúng "nhờ may mắn" khi corpus có tài liệu trùng thuộc tính, còn QA extractive có thể "miễn nhiễm" với một số lỗi. Vì vậy phải đọc retrieval metric (Hit Rate, MAP, MRR) cùng answer metric, và đối chiếu với corruption log ở mức từng câu hỏi.

### Nếu có thêm thời gian

Thêm ba rule cho ba silent failure (số `paper_id` duy nhất so với baseline, độ dài title, regex ký tự bất thường trong summary) và cập nhật `EXPECTED_DETECTORS`. Đo cải thiện bằng ba tiêu chí: `silent_failures` trong log về rỗng; `corrupted_quality_report.json` fail 5/9 expectation thay vì 2/6; baseline và repaired vẫn PASS (không có false positive). Tiếp theo, thêm cờ bật/tắt từng mutation vào `CorruptionConfig` để chạy ablation (mỗi lần chỉ một mutation) và đo riêng mức giảm Hit Rate, MAP, F1 của từng loại lỗi, thay vì suy luận từ một lần chạy gộp.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [X] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [X] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [X] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [X] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [X] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [X] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Đức Thiện
**Ngày xác nhận:** 2026-09-26

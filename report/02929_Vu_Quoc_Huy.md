# Bản nháp báo cáo cá nhân — Vũ Quốc Huy (02929)

> Phạm vi này được phân công ngẫu nhiên. Nội dung mô tả code và artifacts đang có, không xác nhận lịch sử commit hoặc việc cá nhân đã hoàn thành. Hãy bổ sung phần việc trực tiếp thực hiện trước khi nộp.

## 1. Vai trò và phạm vi

**Vai trò được phân công:** Điều phối nền tảng và tích hợp pipeline. **Tỷ trọng mục tiêu:** 25%.

| Module | Trách nhiệm | Input/output chính |
| --- | --- | --- |
| `src/core/config.py`, `src/core/utils.py` | Đọc cấu hình, định nghĩa đường dẫn artifacts, tiện ích JSON/CSV/text | `Settings`/`Paths`; đọc ghi `data/` |
| `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Điều phối baseline và corruption/repair theo thứ tự | Dataframes, test set, indexes, metrics/reports |
| `script/run_phase1.py`, `script/run_corruption_flow.py` | Entrypoints CLI cho hai luồng | Gọi `main()` tương ứng |

## 2. Luồng kỹ thuật trong phạm vi

`phase1.main()` lấy Settings, nạp dữ liệu qua ingestion, làm sạch, ghi clean CSV/JSON, chạy quality và freshness gate, đọc hoặc tạo test set 10 câu, tạo vector index, đánh giá và sinh phase 1 report. Baseline dừng trước indexing nếu Great Expectations không chạy bằng GX 1.x hoặc quality gate thất bại.

`corruption_flow.main()` yêu cầu baseline metrics và test set; nạp clean baseline; tạo corruption log/data; chạy quality, freshness, indexing và evaluation cho dữ liệu corrupted; sau đó nạp lại raw records để dựng repaired dataframe độc lập với dataframe lỗi, re-index/re-evaluate và sinh report đối chiếu.

## 3. Bằng chứng repository hiện có

| Artifact | Nội dung quan sát được |
| --- | --- |
| `data/reports/phase1_report.md` | Baseline có 24 raw/clean records và 10 câu evaluation |
| `data/reports/corruption_report.md` | Có bảng baseline/corrupted/repaired; token F1 lần lượt 100%/70%/100% |
| `data/results/corruption_log.json` | Ghi sáu loại mutation, input 24 dòng, output corrupted 23 dòng |

Các artifacts này được đọc từ repository; lệnh dưới đây là lệnh tái hiện được project hướng dẫn, chưa được chạy lại trong lượt soạn báo cáo này:

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

## 4. Bổ sung của cá nhân trước khi nộp

- **Phần tôi trực tiếp triển khai/tích hợp:** [Bổ sung]
- **Commit hoặc thay đổi có thể đối chiếu:** [Bổ sung]
- **Lỗi tích hợp, nguyên nhân và cách xác minh:** [Bổ sung nếu có; nếu không, ghi rõ]
- **Quyết định kỹ thuật/bài học cá nhân:** [Tự viết]
- **Kết quả chạy thực tế và thời điểm chạy:** [Bổ sung; không suy ra từ artifacts cũ]

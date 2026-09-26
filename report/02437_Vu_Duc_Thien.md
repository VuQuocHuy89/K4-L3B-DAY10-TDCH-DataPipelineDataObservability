# Bản nháp báo cáo cá nhân — Vũ Đức Thiên (02437)

> Phạm vi này được phân công ngẫu nhiên. Nội dung mô tả code và artifacts đang có, không xác nhận lịch sử commit hoặc việc cá nhân đã hoàn thành. Hãy bổ sung phần việc trực tiếp thực hiện trước khi nộp.

## 1. Vai trò và phạm vi

**Vai trò được phân công:** Corruption và observability. **Tỷ trọng mục tiêu:** 25%.

| Module | Trách nhiệm | Input/output chính |
| --- | --- | --- |
| `src/ingestion/corruption.py` | Tạo sáu biến đổi dữ liệu xác định và corruption log | Clean dataframe → corrupted dataframe + `corruption_log.json` |
| `src/observability/quality.py` | GX 1.x expectations, fallback diagnostics, freshness SLA | Dataframe + Settings → quality/freshness JSON |
| `src/observability/reporting.py` | Sinh report baseline và report so sánh ba trạng thái | Metrics + quality/freshness → Markdown reports |

## 2. Luồng kỹ thuật trong phạm vi

Corruption bỏ nhóm bản ghi mới nhất, blank summary, thêm summary noise, truncate title, làm cũ publication date và thêm duplicate rows. Mỗi event ghi `type`, mô tả, số record và `paper_ids`. Quality module kiểm tra số dòng 5–5000, non-null cho `paper_id`/`title`/`text_for_embedding`, uniqueness của `paper_id`, summary dài ít nhất 30 ký tự; Freshness SLA dùng ngưỡng 180 ngày và cho phép tối đa 25% stale rows. Khi GX lỗi, module lưu diagnostic bằng pandas fallback; baseline pipeline yêu cầu engine `great_expectations_1.x` trước khi index.

Reporting module trình bày retrieval hit rate, token F1, judge metrics, quality gate và freshness ở report baseline/comparison.

## 3. Bằng chứng repository hiện có

| Artifact | Nội dung quan sát được |
| --- | --- |
| `data/results/corruption_log.json` | Sáu event; số lượng lần lượt 5, 1, 4, 4, 19, 4 |
| `data/quality/baseline_quality_report.json` | GX 1.x PASS; 24 dòng; stale 1/24 (4.2%) |
| `data/quality/corrupted_quality_report.json` | Gate FAIL; duplicate IDs/summary length fail; stale 23/23 |
| `data/quality/repaired_quality_report.json` | Gate PASS; 24 dòng; freshness PASS |
| `data/reports/corruption_report.md` | So sánh metrics baseline/corrupted/repaired |

Lệnh project hướng dẫn để tái hiện corruption/repair:

```bash
python script/run_corruption_flow.py
```

Lệnh này chưa được chạy lại trong lượt soạn report.

## 4. Bổ sung của cá nhân trước khi nộp

- **Phần tôi trực tiếp triển khai/tích hợp:** [Bổ sung]
- **Commit hoặc thay đổi có thể đối chiếu:** [Bổ sung]
- **Quality rule/corruption tôi trực tiếp thiết kế:** [Bổ sung]
- **Lỗi hoặc cảnh báo đã xử lý và cách xác minh:** [Bổ sung nếu có; nếu không, ghi rõ]
- **Quyết định kỹ thuật và bài học cá nhân:** [Tự viết]

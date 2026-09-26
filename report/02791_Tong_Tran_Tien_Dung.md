# Bản nháp báo cáo cá nhân — Tống Trần Tiến Dũng (02791)

> Phạm vi này được phân công ngẫu nhiên. Nội dung mô tả code và artifacts đang có, không xác nhận lịch sử commit hoặc việc cá nhân đã hoàn thành. Hãy bổ sung phần việc trực tiếp thực hiện trước khi nộp.

## 1. Vai trò và phạm vi

**Vai trò được phân công:** Nền dữ liệu và benchmark. **Tỷ trọng mục tiêu:** 25%.

| Module | Trách nhiệm | Input/output chính |
| --- | --- | --- |
| `src/ingestion/crossref.py` | Parse metadata, ngày, tác giả/category; retry API và dùng snapshot/raw-record fallback | Crossref payload → `PaperRecord` → `data/raw/crossref_records.json` |
| `src/ingestion/cleaning.py` | Làm sạch text, kiểm tra trường bắt buộc, khử trùng lặp, tạo derived fields | Raw records → clean dataframe/CSV/JSON |
| `src/evaluation/testset.py` | Sinh benchmark có ground-truth | Clean dataframe → `data/eval/test_set.json` |

## 2. Luồng kỹ thuật trong phạm vi

Parser hỗ trợ các tên trường Crossref và dạng normalized record, chuẩn hóa DOI thành `paper_id`, lấy publication date từ các trường published, và bỏ record thiếu DOI/title/abstract/ngày hợp lệ. Fetch live có tối đa ba lần thử; khi không refresh, code ưu tiên raw records có sẵn rồi mới dùng snapshot.

Cleaning loại tag HTML/XML, chuẩn hóa whitespace và ngày; loại bản ghi thiếu `paper_id`, title, summary hoặc ngày xuất bản; khử trùng lặp theo `paper_id`; tạo `age_days`, joined authors/categories và `text_for_embedding` gồm năm phần Title/Authors/Published/Categories/Summary.

Test set lấy tối đa 10 record theo thứ tự `paper_id`, phân bổ câu hỏi qua bốn loại `summary`, `authors`, `date`, `categories`; mỗi item lưu `ground_truth_doc_ids` để đo retrieval hit. Corruption flow đọc lại chính file test set này khi so sánh.

## 3. Bằng chứng repository hiện có

| Artifact | Nội dung quan sát được |
| --- | --- |
| `data/raw/crossref_records.json` | Có snapshot normalized dùng làm nguồn repair |
| `data/clean/papers_clean.json` | 24 clean records trong artifact baseline |
| `data/eval/test_set.json` | 10 câu hỏi; dạng câu hỏi thuộc bốn nhóm trên |
| `data/reports/phase1_report.md` | Ghi 24 raw records, 24 clean records và 10 câu evaluation |

Lệnh project hướng dẫn để tái hiện pipeline:

```bash
python script/run_phase1.py
```

Lệnh này chưa được chạy lại trong lượt soạn report.

## 4. Bổ sung của cá nhân trước khi nộp

- **Phần tôi trực tiếp triển khai/tích hợp:** [Bổ sung]
- **Commit hoặc thay đổi có thể đối chiếu:** [Bổ sung]
- **Quy tắc dữ liệu tôi tự thiết kế hoặc xử lý:** [Bổ sung]
- **Lỗi dữ liệu, nguyên nhân và cách xác minh:** [Bổ sung nếu có; nếu không, ghi rõ]
- **Kết quả chạy thực tế và bài học cá nhân:** [Tự viết]

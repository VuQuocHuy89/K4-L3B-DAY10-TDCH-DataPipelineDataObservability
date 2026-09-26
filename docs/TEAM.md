# Danh sách thành viên và phân công nhóm

- **Lớp:** K4-L3B-DAY10
- **Repository:** `K4-L3B-DAY10-TDCH-DataPipelineDataObservability`
- **Cách phân công:** Bốc thăm ngẫu nhiên bốn gói module đã được cân đối theo độ phức tạp, đầu ra và trách nhiệm tích hợp.
- **Tỷ trọng mục tiêu:** 25% cho mỗi thành viên.

> Bảng dưới đây là ownership được phân công theo yêu cầu. Nó không xác nhận lịch sử commit hoặc khẳng định các thành viên đã hoàn thành toàn bộ phần việc. Mỗi người cần kiểm tra lại phạm vi và bổ sung phần việc thực tế trước khi nộp.

| STT | Họ và tên | MSSV | Vai trò và module phụ trách | Tỷ trọng mục tiêu | Báo cáo cá nhân |
| --: | --- | --- | --- | ---: | --- |
| 1 | Vũ Quốc Huy | 02929 | Điều phối nền tảng: `src/core/*`, `src/pipelines/*`, `script/*` | 25% | [`report/02929_Vu_Quoc_Huy.md`](../report/02929_Vu_Quoc_Huy.md) |
| 2 | Tống Trần Tiến Dũng | 02791 | Nền dữ liệu và benchmark: `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/evaluation/testset.py` | 25% | [`report/02791_Tong_Tran_Tien_Dung.md`](../report/02791_Tong_Tran_Tien_Dung.md) |
| 3 | Vũ Đức Thiên | 02437 | Corruption và observability: `src/ingestion/corruption.py`, `src/observability/*` | 25% | [`report/02437_Vu_Duc_Thien.md`](../report/02437_Vu_Duc_Thien.md) |
| 4 | Nguyễn Hoàng Cường | 02473 | RAG và scoring: `src/retrieval/*`, `src/evaluation/metrics.py` | 25% | [`report/02473_Nguyen_Hoang_Cuong.md`](../report/02473_Nguyen_Hoang_Cuong.md) |

## Cách bàn giao giữa các gói

1. Nền dữ liệu tạo raw records, clean dataframe và test set dùng chung.
2. RAG/scoring nhận clean dataframe để tạo index; metrics nhận test set và lưu metric/answer artifacts.
3. Corruption/observability nhận dataframe và metrics, tạo corruption log, quality/freshness results và comparison report.
4. Điều phối nền tảng nối thứ tự chạy baseline và corruption/repair, kiểm tra các đường dẫn artifacts và cập nhật báo cáo nhóm.

Trước khi nộp, từng thành viên cần bổ sung phần việc mình trực tiếp làm, bằng chứng chạy/commit cá nhân và tự xác nhận nội dung báo cáo cá nhân. Không khai ownership khác với lịch sử làm việc thực tế.

# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `TDCH`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-TDCH-DataPipelineDataObservability`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Vũ Quốc Huy | 02929 | vuquochuyforwork@gmail.com | Trưởng nhóm / Pipeline Integrator (`src/core/`, `src/pipelines/`, `script/`, `app.py`) | [02929_Vu_Quoc_Huy.md](../report/02929_Vu_Quoc_Huy.md) |
| 2 | Tống Trần Tiến Dũng | 02791 | tiendung3t@gmail.com | Nền dữ liệu, benchmark và auto-repair (`src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/evaluation/`, `src/pipelines/repair.py`; MAP/MRR và RAGAS reporting) | [02791_Tong_Tran_Tien_Dung.md](../report/02791_Tong_Tran_Tien_Dung.md) |
| 3 | Vũ Đức Thiên | 02437 | vuthien3002@gmail.com | Corruption & Data Observability (`src/ingestion/corruption.py`, `src/observability/`, corruption log và tests) | [02437_Vu_Duc_Thien.md](../report/02437_Vu_Duc_Thien.md) |
| 4 | Nguyễn Hoàng Cường | 02473 | hoangcuong170825@gmail.com | RAG & Evaluation (`src/retrieval/`, `src/evaluation/metrics.py`, vector index và agent evaluation tùy chọn) | [02473_Nguyen_Hoang_Cuong.md](../report/02473_Nguyen_Hoang_Cuong.md) |


---

## # Cá nhân

### ## Vũ Quốc Huy-02929

- **Vai trò:** Trưởng nhóm & Điều phối Pipeline.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống và tiện ích quản lý đường dẫn/artifacts trong `src/core/`.
  - Tích hợp luồng baseline và corruption/repair trong `src/pipelines/`, cùng các entrypoint `script/run_phase1.py` và `script/run_corruption_flow.py`.
  - Xây dựng giao diện Streamlit để demo câu hỏi, câu trả lời, top-K và các bước baseline/corrupted/repaired. Commit evidence: `83b811a`, `4754e8f`.
- **Điều học được / Đóng góp chính:**
  - Điều phối theo một snapshot và test set dùng chung giúp so sánh ba trạng thái nhất quán; repair cần dựng lại từ raw records rồi kiểm tra lại kết quả downstream.

### ## Tống Trần Tiến Dũng-02791

- **Vai trò:** Phụ trách nền dữ liệu, benchmark và cơ chế auto-repair.

- **Công việc đã hoàn thành:**
  - Hoàn thiện parser và chuẩn hóa dữ liệu Crossref trong `src/ingestion/crossref.py`, tập trung vào `_record_from_item`, `parse_crossref_payload` và `fetch_source_records`.
  - Hoàn thiện cleaning pipeline trong `src/ingestion/cleaning.py` với hàm `build_clean_dataframe`, tạo clean records có schema thống nhất.
  - Bổ sung MAP, MRR và RAGAS evaluation trong `src/evaluation/metrics.py` thông qua `_average_precision`, `_reciprocal_rank`, `_run_ragas` và `evaluate_pipeline`.
  - Cập nhật báo cáo metric trong `src/observability/reporting.py` với `generate_phase1_report` và `generate_corruption_report`.
  - Triển khai cơ chế auto-repair trong `src/pipelines/repair.py` với hàm `auto_repair_if_needed`. Khi Quality Gate hoặc Freshness SLA thất bại, pipeline đọc lại raw snapshot, cleaning, kiểm tra lại chất lượng và ghi audit log vào `data/results/repair_log.json`.
- **Artifacts bàn giao:**
  - 24 clean records trong `data/clean/`.
  - Evaluation set 10 câu hỏi trong `data/eval/test_set.json`.
  - Các file metrics và answer trong `data/results/`.
  - Log auto-repair tại `data/results/repair_log.json`.
  - Báo cáo so sánh tại `data/reports/corruption_report.md`.
- **Đóng góp và điều học được:**
  - Raw snapshot và ground truth được giữ nguyên để baseline, corrupted và repaired sử dụng cùng benchmark.
  - Auto-repair giúp phục hồi dữ liệu từ nguồn raw khi Quality/Freshness Gate phát hiện lỗi, đưa các chỉ số retrieval và answer quality trở lại mức baseline.

### ## Vũ Đức Thiên-02437

- **Vai trò:** Phụ trách Corruption và Data Observability.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng corruption suite có cấu hình, ghi detection log và bổ sung tests cho các mutation dữ liệu. Commit evidence: `35484b0`.
  - Phụ trách kiểm tra quality/freshness và đối chiếu artifacts giữa baseline, corrupted và repaired trong luồng nhóm.
  - Corruption log ghi sáu loại mutation; quality/freshness reports cho thấy corrupted không đạt và repaired đạt các cổng kiểm tra hiện có.
- **Điều học được / Đóng góp chính:**
  - Một số mutation có thể lọt qua các quality rules hiện tại; cần đọc corruption log, quality/freshness signals và retrieval metrics cùng nhau khi đánh giá dữ liệu.

### ## Nguyễn Hoàng Cường-02473

- **Vai trò:** Phụ trách RAG, Vector Index và Scoring.
- **Phần việc:** Embedding MiniLM, ChromaDB index, truy xuất top-K và QA trên các collection baseline/corrupted/repaired.
- **Commit có thể đối chiếu:** `393c488` bổ sung nhánh LangChain agent scoring tùy chọn trong `src/evaluation/metrics.py` và chuẩn hóa output trong `src/retrieval/agent.py`.
- **Điều học được / Đóng góp chính:**
  - Dùng cùng test set và collection riêng giúp so sánh retrieval; cần phân biệt metric QA hiện có với nhánh agent evaluation chưa chạy.

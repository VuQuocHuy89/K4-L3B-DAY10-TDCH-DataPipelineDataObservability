# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `TDCH`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-TDCH-DataPipelineDataObservability`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Vũ Quốc Huy | 02929 | vuquochuyforwork@gmail.com | Trưởng nhóm / Pipeline Integrator (`src/core/`, `src/pipelines/`, `script/`, `app.py`) | [02929_Vu_Quoc_Huy.md](../report/02929_Vu_Quoc_Huy.md) |
| 2 | Tống Trần Tiến Dũng | 02791 | tiendung3t@gmail.com | Data Foundation & Benchmark (`src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/evaluation/testset.py`; hỗ trợ MAP/MRR và RAGAS reporting) | [02791_Tong_Tran_Tien_Dung.md](../report/02791_Tong_Tran_Tien_Dung.md) |
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

- **Vai trò:** Phụ trách Nền dữ liệu và Benchmark.
- **Công việc chi tiết đã hoàn thành:**
  - Phụ trách parser Crossref, cleaning và evaluation set để tạo records có schema thống nhất cùng ground-truth document IDs.
  - Bổ sung/sửa MAP, MRR và RAGAS evaluation/reporting. Commit evidence: `2459302`, `bc68334`, `d949607`.
  - Các artifacts hiện có gồm 24 clean records và benchmark 10 câu hỏi để pipeline dùng chung.
- **Điều học được / Đóng góp chính:**
  - Giữ nguyên raw snapshot và ground truth giúp các bước retrieval, corruption và repair dùng đầu vào có thể đối chiếu trên cùng benchmark.

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
- **Công việc chi tiết đã hoàn thành:**
  - Phụ trách embedding MiniLM, ChromaDB index, truy xuất top-K và QA trên các collection baseline/corrupted/repaired.
  - Bổ sung nhánh đánh giá LangChain agent ở chế độ tùy chọn trong `src/evaluation/metrics.py` và `src/retrieval/agent.py`; nhánh này chưa được bật trong artifacts hiện tại.
  - Commit `393c488` có thay đổi agent evaluation nhưng Git hiện ghi tác giả là `unknown`; thành viên cần tự kiểm tra GitHub Insights để xác nhận attribution.
- **Điều học được / Đóng góp chính:**
  - Dùng cùng test set và collection riêng cho từng trạng thái giúp so sánh retrieval; cần phân biệt metric của QA evaluator hiện chạy với nhánh agent evaluation chưa chạy.

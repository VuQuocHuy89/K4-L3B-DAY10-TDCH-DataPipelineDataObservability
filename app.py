from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import pandas as pd
import streamlit as st

from core.config import Settings, load_settings, normalized_provider
from core.utils import now_utc, read_json, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import AnswerResult, answer_question


ROOT = Path(__file__).resolve().parent
DEMO_KEY = "pipeline_demo"
STAGES = ("baseline", "corrupted", "repaired")
LABELS = {"baseline": "Baseline", "corrupted": "Corrupted", "repaired": "Repaired"}
COLORS = {"Baseline": "#1E40AF", "Corrupted": "#D97706", "Repaired": "#0F766E"}
STAGE_STEPS = {
    "baseline": ("ingest", "clean", "quality_baseline", "index_baseline", "rag_baseline"),
    "corrupted": ("corrupt", "quality_corrupted", "index_corrupted", "rag_corrupted"),
    "repaired": ("repair", "quality_repaired", "index_repaired", "rag_repaired"),
}
STEPS = [
    ("ingest", "Nạp dữ liệu đầu vào", "Đọc snapshot Crossref hoặc làm mới từ API."),
    ("clean", "Làm sạch dữ liệu", "Chuẩn hóa, khử trùng lặp và tạo nội dung cho embedding."),
    ("quality_baseline", "Quality Gate · Baseline", "Chạy Great Expectations và Freshness SLA."),
    ("index_baseline", "Embedding & index · Baseline", "Tạo embedding và index ChromaDB."),
    ("rag_baseline", "Truy vấn RAG · Baseline", "Chạy câu hỏi, xem top-K nguồn và câu trả lời."),
    ("corrupt", "Tiêm lỗi dữ liệu", "Áp dụng sáu kịch bản corruption có ghi log."),
    ("quality_corrupted", "Quality Gate · Corrupted", "Quan sát các kiểm định phát hiện dữ liệu lỗi."),
    ("index_corrupted", "Embedding & index · Corrupted", "Index dữ liệu lỗi để đo tác động retrieval."),
    ("rag_corrupted", "Truy vấn RAG · Corrupted", "Chạy lại đúng câu hỏi trên dữ liệu lỗi."),
    ("repair", "Repair từ Raw", "Dựng lại dữ liệu sạch từ raw snapshot."),
    ("quality_repaired", "Quality Gate · Repaired", "Xác nhận chất lượng sau khi repair."),
    ("index_repaired", "Embedding & index · Repaired", "Index phiên bản đã phục hồi."),
    ("rag_repaired", "Truy vấn RAG · Repaired", "Chạy lại câu hỏi để xem mức phục hồi."),
]
CORRUPTION_LABELS = {
    "drop_latest_records": "Bỏ bản ghi mới nhất",
    "blank_summary": "Xóa summary",
    "inject_summary_noise": "Chèn ký tự nhiễu",
    "truncate_title": "Cắt ngắn tiêu đề",
    "stale_publication_date": "Làm cũ ngày xuất bản",
    "duplicate_rows": "Nhân bản bản ghi",
}

st.set_page_config(page_title="RAG Pipeline Live Demo", page_icon=":material/forum:", layout="wide")
st.markdown(
    """
    <style>
      :root { --ink:#1e1b4b; --muted:#475569; --line:#ddd6fe; --surface:#fff; --canvas:#faf5ff; --primary:#7c3aed; }
      .stApp { background:var(--canvas); color:var(--ink); }
      [data-testid="stHeader"] { background:transparent; }
      .block-container { max-width:1040px; padding:2rem 1.5rem 6rem; }
      [data-testid="stBottomBlockContainer"] { max-width:1040px!important; padding-left:1.5rem!important; padding-right:1.5rem!important; }
      h1,h2,h3 { color:var(--ink); letter-spacing:-.025em; }
      .eyebrow { color:#6d28d9; font-size:.76rem; font-weight:750; letter-spacing:.12em; text-transform:uppercase; }
      .subtle { color:var(--muted); max-width:58rem; line-height:1.55; }
      .stage-label { font-size:.75rem; font-weight:750; letter-spacing:.08em; text-transform:uppercase; }
      .suggestion-title { font-size:1rem; font-weight:700; margin:1.4rem 0 .5rem; }
      [data-testid="stChatMessage"] { background:var(--surface); border:1px solid var(--line); border-radius:16px; }
      [data-testid="stChatMessage"] p { line-height:1.55; }
      [data-testid="stChatInput"] { border-radius:14px; }
      [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
      div.stButton>button { min-height:44px; border-radius:10px; text-align:left; white-space:normal; }
      div.stButton>button:focus-visible { outline:3px solid var(--primary); outline-offset:2px; }
      @media(max-width:900px) {
        .block-container { padding:1rem 1rem 5rem; }
        [data-testid="stBottomBlockContainer"] { padding-left:1rem!important; padding-right:1rem!important; }
        [data-testid="stHorizontalBlock"] { flex-wrap:wrap; gap:.65rem; }
        [data-testid="column"] { min-width:min(100%,220px); flex:1 1 220px; }
      }
      @media(prefers-reduced-motion:reduce) { *,*::before,*::after { transition:none!important; } }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_test_cases(settings: Settings) -> list[dict[str, Any]]:
    try:
        cases = read_json(settings.paths.eval_testset)
    except (OSError, json.JSONDecodeError):
        return []
    return cases if isinstance(cases, list) else []


def token_f1(reference: str, prediction: str) -> float:
    refs, preds = set(reference.lower().split()), set(prediction.lower().split())
    if not refs or not preds:
        return 0.0
    overlap = len(refs & preds)
    precision, recall = overlap / len(preds), overlap / len(refs)
    return 2 * precision * recall / (precision + recall) if overlap else 0.0


def new_demo(question: str, test_case: dict[str, Any] | None, top_k: int, refresh_source: bool = False) -> dict[str, Any]:
    return {
        "version": 2,
        "question": question.strip(), "test_case": test_case, "top_k": top_k, "refresh_source": refresh_source,
        "cursor": 0, "completed": [], "durations": {}, "events": [], "frames": {}, "records": None,
        "quality": {}, "freshness": {}, "indices": {}, "rag": {}, "corruption_events": [], "error": None,
    }


def log_event(demo: dict[str, Any], message: str, level: str = "INFO") -> str:
    line = f"{datetime.now().astimezone().strftime('%H:%M:%S')}  {level:<5}  {message}"
    demo["events"].append(line)
    return line


def run_rag(demo: dict[str, Any], settings: Settings, stage: str, emit: Callable[[str], None]) -> None:
    index: LocalEmbeddingIndex = demo["indices"][stage]
    result: AnswerResult = answer_question(demo["question"], settings, index, top_k=demo["top_k"])
    emit(f"Retrieval trả về {len(result.candidates)} ứng viên (top_k={demo['top_k']}).")

    llm_answer, llm_error = None, None
    try:
        agent = build_agent(settings, index, top_k=demo["top_k"])
        llm_answer = run_agent_question(agent, demo["question"]).strip()
        if llm_answer:
            emit(f"LLM provider {normalized_provider(settings)} đã tạo câu trả lời.")
    except Exception as exc:
        llm_error = f"{type(exc).__name__}: dùng câu trả lời extractive từ top-1."
        emit(llm_error, "WARN")

    candidates = [
        {
            "rank": rank, "paper_id": item.paper_id, "title": item.title, "score": item.score,
            "answer": item.answer, "context": item.context, "abs_url": item.metadata.get("abs_url", ""),
        }
        for rank, item in enumerate(result.candidates, start=1)
    ]
    answer = llm_answer or result.answer
    case = demo.get("test_case")
    expected_ids = set((case or {}).get("ground_truth_doc_ids", []))
    hit = any(item["paper_id"] in expected_ids for item in candidates) if expected_ids else None
    f1 = token_f1(str(case.get("ground_truth", "")), answer) if case else None
    demo["rag"][stage] = {
        "answer": answer, "answer_source": "LLM Agent" if llm_answer else "RAG extractive · top-1",
        "llm_error": llm_error, "candidates": candidates, "hit": hit, "f1": f1,
    }
    if hit is not None:
        emit(f"Hit@{demo['top_k']}={'Có' if hit else 'Không'} · Answer Token F1={f1:.1%}.")


def execute_step(step_key: str, demo: dict[str, Any], settings: Settings, emit: Callable[[str], None]) -> None:
    settings = replace(settings, refresh_source=demo["refresh_source"])

    if step_key == "ingest":
        source = "Crossref API" if demo["refresh_source"] else "local raw snapshot"
        emit(f"Đọc nguồn {source}.")
        records = fetch_source_records(settings)
        if not records:
            raise RuntimeError("Nguồn không có bản ghi hợp lệ.")
        demo["records"] = records
        demo["frames"]["raw"] = pd.DataFrame([asdict(record) for record in records])
        emit(f"Đã nạp {len(records)} raw records; giữ raw làm nguồn repair.")
    elif step_key == "clean":
        records: list[PaperRecord] = demo["records"]
        clean = build_clean_dataframe(records, now_utc())
        if clean.empty:
            raise RuntimeError("Cleaning không tạo được bản ghi hợp lệ.")
        write_csv(clean, settings.paths.clean_csv)
        write_json(settings.paths.clean_json, clean.to_dict(orient="records"))
        demo["frames"]["clean"] = clean
        emit(f"Cleaning: {len(records)} raw → {len(clean)} clean rows.")
    elif step_key == "quality_baseline":
        clean = demo["frames"]["clean"]
        report = run_data_quality_checks(clean, settings, "baseline")
        freshness = build_freshness_report(clean, settings, settings.paths.freshness_report)
        demo["quality"]["baseline"], demo["freshness"]["baseline"] = report, freshness
        emit(f"Great Expectations {report['engine']}: {'PASS' if report['expectations_success'] else 'FAIL'}.")
        emit(f"Freshness: {freshness['stale_rows']}/{freshness['total_rows']} stale.")
        if report["engine"] != "great_expectations_1.x" or not report["success"]:
            raise RuntimeError("Baseline Quality Gate chưa đạt; chưa thể index dữ liệu.")
    elif step_key == "index_baseline":
        emit(f"Đang embed và index {len(demo['frames']['clean'])} tài liệu.")
        demo["indices"]["baseline"] = LocalEmbeddingIndex.build(
            demo["frames"]["clean"], settings, settings.paths.embeddings_json
        )
        emit(f"ChromaDB collection {settings.baseline_collection_name} sẵn sàng.")
    elif step_key == "rag_baseline":
        run_rag(demo, settings, "baseline", emit)
    elif step_key == "corrupt":
        corrupted = corrupt_clean_dataframe(demo["frames"]["clean"], settings.paths.corruption_log)
        write_csv(corrupted, settings.paths.corrupted_clean_csv)
        write_json(settings.paths.corrupted_clean_json, corrupted.to_dict(orient="records"))
        demo["frames"]["corrupted"] = corrupted
        payload = read_json(settings.paths.corruption_log)
        demo["corruption_events"] = payload.get("events", []) if isinstance(payload, dict) else []
        emit(f"Đã chạy {len(demo['corruption_events'])} kịch bản; {len(demo['frames']['clean'])} → {len(corrupted)} rows.")
    elif step_key == "quality_corrupted":
        frame = demo["frames"]["corrupted"]
        report = run_data_quality_checks(frame, settings, "corrupted")
        freshness = build_freshness_report(frame, settings, report_path=None)
        demo["quality"]["corrupted"], demo["freshness"]["corrupted"] = report, freshness
        emit(f"Corrupted Quality Gate: {'PASS' if report['success'] else 'FAIL'} (FAIL là cảnh báo dự kiến).")
        emit(f"Freshness: {freshness['stale_rows']}/{freshness['total_rows']} stale.")
    elif step_key == "index_corrupted":
        emit(f"Đang embed và index {len(demo['frames']['corrupted'])} tài liệu lỗi.")
        demo["indices"]["corrupted"] = LocalEmbeddingIndex.build(
            demo["frames"]["corrupted"], settings, settings.paths.corrupted_embeddings_json
        )
        emit(f"ChromaDB collection {settings.corrupted_collection_name} sẵn sàng.")
    elif step_key == "rag_corrupted":
        run_rag(demo, settings, "corrupted", emit)
    elif step_key == "repair":
        emit("Đọc lại raw_records_json, không lấy corrupted frame làm nguồn.")
        records = load_raw_records(settings.paths.raw_records_json)
        repaired = build_clean_dataframe(records, now_utc())
        if repaired.empty:
            raise RuntimeError("Repair từ raw snapshot không tạo được bản ghi.")
        write_csv(repaired, settings.paths.repaired_clean_csv)
        write_json(settings.paths.repaired_clean_json, repaired.to_dict(orient="records"))
        demo["frames"]["repaired"] = repaired
        emit(f"Repair dựng lại {len(repaired)} rows từ {len(records)} raw records.")
    elif step_key == "quality_repaired":
        frame = demo["frames"]["repaired"]
        report = run_data_quality_checks(frame, settings, "repaired")
        freshness = build_freshness_report(frame, settings, report_path=None)
        demo["quality"]["repaired"], demo["freshness"]["repaired"] = report, freshness
        emit(f"Quality Gate sau repair: {'PASS' if report['success'] else 'FAIL'}.")
        emit(f"Freshness: {freshness['stale_rows']}/{freshness['total_rows']} stale.")
        if report["engine"] != "great_expectations_1.x" or not report["success"]:
            raise RuntimeError("Chất lượng chưa được phục hồi sau repair.")
    elif step_key == "index_repaired":
        emit(f"Đang embed và index {len(demo['frames']['repaired'])} tài liệu đã repair.")
        demo["indices"]["repaired"] = LocalEmbeddingIndex.build(
            demo["frames"]["repaired"], settings, settings.paths.repaired_embeddings_json
        )
        emit(f"ChromaDB collection {settings.repaired_collection_name} sẵn sàng.")
    elif step_key == "rag_repaired":
        run_rag(demo, settings, "repaired", emit)
        emit("Cùng truy vấn đã chạy qua đủ ba trạng thái.")
    else:
        raise KeyError(f"Unknown pipeline step: {step_key}")


def render_stage_details(demo: dict[str, Any], stage: str) -> None:
    report = demo["quality"].get(stage)
    frame_name = "clean" if stage == "baseline" else stage
    frame = demo["frames"].get(frame_name)
    if report is None or frame is None:
        return
    with st.expander("Dữ liệu, Quality Gate và Freshness SLA"):
        freshness = report["freshness"]
        columns = st.columns(3)
        columns[0].metric("Quality Gate", "PASS" if report["success"] else "FAIL")
        columns[1].metric("Bản ghi", len(frame))
        columns[2].metric("Bản ghi quá hạn", f"{freshness['stale_rows']}/{freshness['total_rows']}")
        st.caption(f"Engine: {report['engine']} · Ngưỡng freshness: {freshness['threshold_days']} ngày")
        if stage == "corrupted" and demo["corruption_events"]:
            events = pd.DataFrame([
                {
                    "Lỗi được tiêm": CORRUPTION_LABELS.get(item.get("type", ""), item.get("type", "—")),
                    "Số bản ghi": item.get("count", 0),
                    "Quality Gate dự kiến": ", ".join(item.get("expected_detectors", [])) or "Silent failure",
                }
                for item in demo["corruption_events"]
            ])
            st.dataframe(events, hide_index=True, width="stretch")
        preview = [column for column in ("paper_id", "title", "summary", "published") if column in frame.columns]
        st.dataframe(frame[preview].head(5), hide_index=True, width="stretch")


def render_candidates(demo: dict[str, Any], result: dict[str, Any]) -> None:
    st.markdown(f"**Top {demo['top_k']} tài liệu được truy xuất**")
    candidates = result["candidates"]
    if not candidates:
        st.warning("Chưa tìm thấy tài liệu phù hợp. Hãy thử câu hỏi khác.")
        return
    for item in candidates:
        with st.container(border=True):
            title_col, score_col = st.columns([5, 1])
            title_col.markdown(f"**#{item['rank']} · {item['title']}**")
            score_col.markdown(f"**{item['score']:.1%}**")
            st.progress(max(0.0, min(1.0, item["score"])))
            st.write(item["answer"])
            with st.expander("Xem ngữ cảnh và nguồn"):
                st.caption(f"paper_id: {item['paper_id']}")
                st.write(item["context"])
                if item["abs_url"]:
                    st.link_button("Mở bài báo", item["abs_url"])


def render_conversation(demo: dict[str, Any]) -> None:
    with st.chat_message("user"):
        st.write(demo["question"])
    for stage in STAGES:
        result = demo["rag"].get(stage)
        if result is None:
            continue
        with st.chat_message("assistant"):
            st.markdown(
                f'<span class="stage-label" style="color:{COLORS[LABELS[stage]]}">{LABELS[stage]}</span>',
                unsafe_allow_html=True,
            )
            st.write(result["answer"])
            st.caption(f"{result['answer_source']} · cùng câu hỏi · Top-K={demo['top_k']}")
            if result["llm_error"]:
                st.caption(result["llm_error"])
            if result["hit"] is not None:
                score_columns = st.columns(2)
                score_columns[0].metric(f"Hit@{demo['top_k']}", "Hit" if result["hit"] else "Miss")
                score_columns[1].metric("Answer Token F1", f"{result['f1']:.1%}")
            render_candidates(demo, result)
            render_stage_details(demo, stage)


def render_logs(demo: dict[str, Any]) -> None:
    with st.expander(f"Nhật ký pipeline · {len(demo['events'])} sự kiện", expanded=bool(demo.get("error"))):
        st.code("\n".join(demo["events"][-100:]), language="text")


def run_stage_batch(demo: dict[str, Any], settings: Settings, stage: str) -> None:
    demo["error"] = None
    step_titles = {key: title for key, title, _ in STEPS}
    with st.status(f"Đang chạy {LABELS[stage]}...", expanded=True) as status:
        def emit(message: str, level: str = "INFO") -> None:
            status.write(log_event(demo, message, level))

        for step_key in STAGE_STEPS[stage]:
            if step_key in demo["completed"]:
                continue
            title = step_titles[step_key]
            status.write(log_event(demo, f"Bắt đầu {title}."))
            started = perf_counter()
            try:
                execute_step(step_key, demo, settings, emit)
            except Exception as exc:
                safe_error = f"{type(exc).__name__}: {exc}"
                for secret in (
                    settings.groq_api_key, settings.google_api_key, settings.openai_api_key,
                    settings.anthropic_api_key, settings.openrouter_api_key, settings.custom_llm_api_key,
                ):
                    if secret:
                        safe_error = safe_error.replace(secret, "[REDACTED]")
                demo["error"] = {"step": step_key, "message": safe_error}
                status.write(log_event(demo, f"Bước thất bại: {safe_error}", "ERROR"))
                status.update(label=f"{LABELS[stage]} gặp lỗi ở: {title}", state="error", expanded=True)
                return
            duration = perf_counter() - started
            demo["completed"].append(step_key)
            demo["durations"][step_key] = duration
            demo["cursor"] += 1
            status.write(log_event(demo, f"Hoàn tất {title} trong {duration:.1f}s."))
        status.update(label=f"Hoàn tất {LABELS[stage]}", state="complete", expanded=False)


def render_sidebar(settings: Settings, demo: dict[str, Any] | None) -> tuple[int, bool]:
    with st.sidebar:
        st.markdown("### Thiết lập demo")
        st.caption("Snapshot cục bộ được chọn mặc định để trình bày ổn định.")
        refresh = st.toggle("Làm mới từ Crossref API", value=False, disabled=demo is not None)
        top_k = st.slider(
            "Số tài liệu Top-K", 1, 8, max(1, min(8, settings.top_k)),
            disabled=demo is not None,
        )
        if demo is not None:
            st.caption("Các thiết lập được giữ nguyên cho cùng một câu hỏi.")
            if st.button("Đặt câu hỏi mới", width="stretch"):
                st.session_state.pop(DEMO_KEY, None)
                st.rerun()
        st.divider()
        st.caption(f"LLM: {normalized_provider(settings)} · API key được giữ kín")
    return top_k, refresh


def render_suggestions(cases: list[dict[str, Any]]) -> str | None:
    if not cases:
        return None
    st.markdown('<p class="suggestion-title">Câu hỏi gợi ý từ bộ benchmark</p>', unsafe_allow_html=True)
    selected = None
    columns = st.columns(2)
    for index, case in enumerate(cases[:4]):
        with columns[index % 2]:
            if st.button(str(case["question"]), key=f"suggestion_{case['id']}", width="stretch"):
                selected = str(case["question"])
    st.caption("Chọn câu hỏi gợi ý để có thêm Hit@K và Token F1, hoặc nhập câu hỏi riêng bên dưới.")
    return selected


def main() -> None:
    settings = load_settings(project_dir=ROOT)
    cases = load_test_cases(settings)
    demo = st.session_state.get(DEMO_KEY)
    if demo is not None and demo.get("version") != 2:
        st.session_state.pop(DEMO_KEY, None)
        demo = None
    top_k, refresh = render_sidebar(settings, demo)

    st.markdown('<p class="eyebrow">DAY 10 · RAG PIPELINE DEMO</p>', unsafe_allow_html=True)
    st.title("Hỏi đáp và quan sát pipeline")
    st.markdown(
        '<p class="subtle">Đặt một câu hỏi. Xem câu trả lời và top-K của Baseline, rồi chạy Corrupted và Repaired để quan sát thay đổi trên đúng câu hỏi đó.</p>',
        unsafe_allow_html=True,
    )
    if demo is None:
        if not (settings.paths.raw_records_json.exists() or settings.paths.raw_api_response.exists()):
            st.warning("Chưa tìm thấy snapshot raw. Chọn làm mới từ Crossref API trong thanh bên.")
        suggested = render_suggestions(cases)
    else:
        suggested = None
        render_conversation(demo)

    question = st.chat_input(
        "Nhập câu hỏi về bộ bài báo..." if demo is None else "Hỏi câu khác để bắt đầu phiên mới...",
        width="stretch",
    )
    question = suggested or question
    if question and question.strip():
        case = next((item for item in cases if item.get("question") == question.strip()), None)
        demo = new_demo(question, case, top_k, refresh)
        st.session_state[DEMO_KEY] = demo
        run_stage_batch(demo, settings, "baseline")
        st.rerun()

    if demo is not None:
        pending_stage = next((stage for stage in STAGES if stage not in demo["rag"]), None)
        if demo.get("error"):
            st.error(f"{demo['error']['step']}: {demo['error']['message']}")
        if pending_stage is not None:
            st.markdown("### Bước tiếp theo")
            if pending_stage == "corrupted":
                st.caption("Tiêm lỗi → Quality Gate → index → hỏi lại cùng câu hỏi.")
                label = "Chạy Corrupted và xem top-K mới"
            elif pending_stage == "repaired":
                st.caption("Dựng lại từ raw → Quality Gate → index → hỏi lại cùng câu hỏi.")
                label = "Chạy Repaired và xem top-K sau phục hồi"
            else:
                st.caption("Nạp snapshot → cleaning → Quality Gate → index → trả lời.")
                label = "Thử lại Baseline" if demo.get("error") else "Chạy Baseline"
            if demo.get("error") and pending_stage != "baseline":
                label = f"Thử lại {LABELS[pending_stage]}"
            if st.button(label, type="primary", width="stretch"):
                run_stage_batch(demo, settings, pending_stage)
                st.rerun()
        else:
            st.success("Đã chạy đủ Baseline → Corrupted → Repaired cho cùng một câu hỏi.")
        render_logs(demo)


if __name__ == "__main__":
    main()

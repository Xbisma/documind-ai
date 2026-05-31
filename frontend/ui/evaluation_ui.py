from __future__ import annotations

from typing import Optional
import streamlit as st

from frontend.services.eval_runner import run_retrieval_eval, write_report_md


def render_evaluation_tab(
    *,
    default_session_id: str = "",
    default_test_path: str = "evaluation/test_questions.json",
    report_out_path: str = "evaluation/retrieval_report.md",
) -> None:

    st.subheader("Evaluation (Retrieval Accuracy)")
    st.write(
        "Runs the test set and computes Doc@K + keyword-hit + no-context rate."
    )

    session_id = st.text_input(
        "Session ID to evaluate (use current chat session_id or paste one)",
        value=default_session_id,
        key="eval_session_id",
    )

    test_path = st.text_input(
        "Test questions path",
        value=default_test_path,
        key="eval_test_path",
    )

    col1, col2 = st.columns(2)

    with col1:
        top_k = st.slider("Top K", 1, 20, 5, key="eval_top_k")

    with col2:
        min_similarity = st.slider(
            "Min similarity",
            0.0,
            1.0,
            0.35,
            0.05,
            key="eval_min_sim",
        )

    if st.button("Run Evaluation", type="primary"):

        if not session_id.strip():
            st.warning("Provide a session_id. Upload PDFs first to create one.")
            return

        try:
            results, summary = run_retrieval_eval(
                test_questions_path=test_path,
                session_id=session_id.strip(),
                top_k=top_k,
                min_similarity=min_similarity,
            )

            st.success("Evaluation completed.")
            st.json(summary)

            write_report_md(report_out_path, results, summary)
            st.info(f"Report saved to: {report_out_path}")

            # Show first few rows as preview
            st.subheader("Preview (first 10 questions)")

            for r in results[:10]:
                st.write(
                    f"- Q: {r.question}\n"
                    f" Expected: {r.expected_doc}\n"
                    f" Top docs: {', '.join(r.top_docs)}"
                )

        except Exception as e:
            st.error("Evaluation failed.")
            st.write(str(e))
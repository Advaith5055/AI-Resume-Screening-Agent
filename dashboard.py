"""Streamlit interactive application for the AI Resume Screening Agent."""

import io
import json
from pathlib import Path
import tempfile
import time
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from app.engine.pipeline import BatchScreeningPipeline
from app.engine.scorer import ScoringEngine
from app.extractors.jd_extractor import extract_job_description
from app.extractors.resume_extractor import extract_resume
from app.exporters.csv_exporter import export_ranking_to_csv
from app.exporters.json_exporter import export_ranking_to_json
from app.models.job_description import JobDescription
from app.models.ranking import (
    BatchScreeningResult,
    MatchResult,
    RankedCandidate,
    RankingResult,
)

# ─── Page Configuration ───
st.set_page_config(
    page_title="AI Resume Screening Agent",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom Styling ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Preserve icon fonts */
    [data-testid="stIconMaterial"],
    [data-testid="stExpanderToggleIcon"],
    [data-testid="stExpanderToggleIcon"] * {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1250px;
    }

    h1 { font-weight: 800; letter-spacing: -0.5px; }
    h2 { font-weight: 700; letter-spacing: -0.3px; }
    h3 { font-weight: 600; }

    .metric-card {
        background: linear-gradient(135deg, #131424 0%, #1a1b32 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.3rem 1rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.25);
    }
    .metric-card.failed {
        background: linear-gradient(135deg, #2b1117 0%, #1e1115 100%);
        border: 1px solid rgba(255, 99, 132, 0.25);
    }
    .metric-card.failed .metric-value {
        background: linear-gradient(135deg, #ff6b8b 0%, #ff4757 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-card .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.2rem 0;
    }
    .metric-card .metric-label {
        font-size: 0.8rem;
        color: #8892b0;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    .score-bar-bg {
        background: rgba(255,255,255,0.06);
        border-radius: 8px;
        height: 10px;
        overflow: hidden;
        margin-top: 4px;
    }
    .score-bar-fill {
        height: 100%;
        border-radius: 8px;
        transition: width 0.6s ease;
    }

    .skill-tag {
        display: inline-block;
        padding: 4px 11px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 500;
        margin: 3px 4px 3px 0;
    }
    .skill-matched { background: rgba(72,199,142,0.15); color: #48c78e; border: 1px solid rgba(72,199,142,0.3); }
    .skill-missing { background: rgba(255,99,71,0.12); color: #ff6b6b; border: 1px solid rgba(255,99,71,0.25); }
    .skill-preferred { background: rgba(102,126,234,0.15); color: #667eea; border: 1px solid rgba(102,126,234,0.3); }

    .explanation-box {
        background: rgba(255,255,255,0.03);
        border-left: 3px solid #667eea;
        border-radius: 0 12px 12px 0;
        padding: 1rem 1.25rem;
        margin-top: 0.75rem;
        font-size: 0.9rem;
        line-height: 1.6;
        color: #a8b2d1;
    }

    div[data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ─── Helper Functions ───
def get_score_color(score: float) -> str:
    if score >= 80:
        return "linear-gradient(90deg, #48c78e, #3ec487)"
    elif score >= 60:
        return "linear-gradient(90deg, #667eea, #764ba2)"
    elif score >= 40:
        return "linear-gradient(90deg, #f6d365, #fda085)"
    else:
        return "linear-gradient(90deg, #ff6b6b, #ee5a24)"


def render_score_bar(label: str, value: float, max_val: float = 100.0):
    pct = min(100, (value / max_val) * 100) if max_val > 0 else 0
    color = get_score_color(value)
    st.markdown(f"""
        <div style="margin-bottom: 8px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                <span style="font-size:0.82rem; color:#8892b0; font-weight:500;">{label}</span>
                <span style="font-size:0.82rem; color:#ccd6f6; font-weight:600;">{value:.1f}%</span>
            </div>
            <div class="score-bar-bg">
                <div class="score-bar-fill" style="width:{pct:.1f}%; background:{color};"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)


@st.cache_resource
def get_pipeline() -> BatchScreeningPipeline:
    return BatchScreeningPipeline()


# ─── Session State Initialization ───
if "current_result" not in st.session_state:
    # Try loading existing ranking.json if available
    default_json = Path("outputs/ranking.json")
    if default_json.exists():
        try:
            with open(default_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.current_result = data
        except Exception:
            st.session_state.current_result = None
    else:
        st.session_state.current_result = None


# ─── Sidebar Controls ───
with st.sidebar:
    st.markdown("### ⚙️ Screening Control")
    mode = st.radio(
        "Mode",
        ["📁 Upload & Screen", "📊 View Existing Report"],
        help="Choose to screen new resumes or view saved reports."
    )

    st.markdown("---")
    st.markdown("### 🎯 Score & Rank Filters")
    min_score = st.slider("Minimum Score Threshold", 0.0, 100.0, 0.0, 1.0)
    top_n_limit = st.slider("Max Candidates to Display", 1, 50, 20)

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#5c6b89; font-size:0.75rem;'>"
        "AI Resume Screening Agent<br/>Deterministic • Explainable • Offline"
        "</div>",
        unsafe_allow_html=True
    )


# ─── Main View ───
st.markdown("# 📄 AI Resume Screening Agent")
st.markdown(
    "<p style='color:#8892b0; font-size:1.05rem; margin-top:-0.5rem;'>"
    "Automated, explainable multi-factor resume screening & candidate ranking</p>",
    unsafe_allow_html=True
)

if mode == "📁 Upload & Screen":
    st.markdown("### 📥 Input Job Description & Resumes")

    tab_upload, tab_sample = st.tabs(["📤 Custom File Upload", "📦 Load Sample Dataset"])

    with tab_upload:
        col_jd, col_res = st.columns([1, 1])

        with col_jd:
            st.markdown("**1. Target Job Description**")
            jd_upload_file = st.file_uploader(
                "Upload JD document (.pdf, .docx, .txt)",
                type=["pdf", "docx", "txt"],
                key="jd_file"
            )
            jd_text_input = st.text_area(
                "Or paste Job Description text directly:",
                height=150,
                placeholder="Job Title: Senior ML Engineer\nRequirements:\n- Python, PyTorch, SQL\n- 2+ years experience...",
                key="jd_text"
            )

        with col_res:
            st.markdown("**2. Candidate Resumes**")
            resume_files = st.file_uploader(
                "Upload candidate resumes (multiple .pdf, .docx, .txt files)",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True,
                key="resume_files"
            )
            st.caption("Upload multiple files to run automated batch screening.")

        start_custom_btn = st.button("🚀 Run Screening on Uploaded Files", type="primary", use_container_width=True)

        if start_custom_btn:
            if not jd_upload_file and not jd_text_input.strip():
                st.error("Please provide a Job Description (either upload a file or paste text).")
            elif not resume_files:
                st.error("Please upload at least one candidate resume.")
            else:
                with st.spinner("Processing resumes through parsing, extraction, semantic scoring, and ranking..."):
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        tmp_path = Path(tmp_dir)
                        resumes_dir = tmp_path / "resumes"
                        resumes_dir.mkdir()

                        # Save JD
                        if jd_upload_file:
                            jd_path = tmp_path / jd_upload_file.name
                            jd_path.write_bytes(jd_upload_file.getvalue())
                        else:
                            jd_path = tmp_path / "job_description.txt"
                            jd_path.write_text(jd_text_input, encoding="utf-8")

                        # Save uploaded resumes
                        for rf in resume_files:
                            r_file_path = resumes_dir / rf.name
                            r_file_path.write_bytes(rf.getvalue())

                        # Execute batch screening pipeline
                        pipeline = get_pipeline()
                        batch_res = pipeline.run(
                            job_path=jd_path,
                            resumes_dir=resumes_dir,
                            output_dir="outputs",
                        )

                        # Update session state
                        st.session_state.current_result = batch_res.model_dump()
                        st.success(
                            f"Successfully screened {batch_res.successful_count} candidate(s)! "
                            f"{batch_res.failed_count} file(s) failed."
                        )

    with tab_sample:
        st.info("Quickly run the screening engine against the pre-loaded 11 sample resumes and sample Job Description.")
        sample_jd_path = Path("data/job_descriptions/sample_job_description.txt")
        sample_resumes_dir = Path("data/resumes")

        if st.button("⚡ Run Screening on 11 Sample Resumes", type="secondary", use_container_width=True):
            if not sample_jd_path.exists() or not sample_resumes_dir.exists():
                st.error("Sample dataset directory not found.")
            else:
                with st.spinner("Running batch screening across sample dataset..."):
                    pipeline = get_pipeline()
                    batch_res = pipeline.run(
                        job_path=sample_jd_path,
                        resumes_dir=sample_resumes_dir,
                        output_dir="outputs",
                    )
                    st.session_state.current_result = batch_res.model_dump()
                    st.success("Sample screening completed successfully!")

elif mode == "📊 View Existing Report":
    report_path = st.text_input(
        "Path to JSON Report",
        value="outputs/ranking.json",
        help="Specify the file path of a previously generated ranking report."
    )
    if st.button("🔄 Reload Report", use_container_width=True):
        p = Path(report_path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                st.session_state.current_result = json.load(f)
            st.success("Report loaded!")
        else:
            st.error(f"File not found: {report_path}")


# ─── Results Visualization ───
result_data = st.session_state.current_result

if result_data:
    st.markdown("---")

    all_rankings = result_data.get("rankings", [])
    total_files = result_data.get("total_files", len(all_rankings))
    successful_count = result_data.get("successful_count", len(all_rankings))
    failed_count = result_data.get("failed_count", 0)
    errors = result_data.get("errors", [])
    job_title = result_data.get("job_title", "Position")

    # Apply filters
    filtered_rankings = [r for r in all_rankings if r["final_score"] >= min_score][:top_n_limit]
    filtered_count = len(filtered_rankings)
    avg_score = (
        sum(r["final_score"] for r in filtered_rankings) / filtered_count
        if filtered_count > 0 else 0.0
    )

    st.markdown(f"### 📋 Screening Results for: **{job_title}**")

    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Resumes</div>
                <div class="metric-value">{total_files}</div>
            </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Matching Filter (≥ {min_score:.0f})</div>
                <div class="metric-value">{filtered_count} / {successful_count}</div>
            </div>
        """, unsafe_allow_html=True)

    with m3:
        failed_class = "failed" if failed_count > 0 else ""
        st.markdown(f"""
            <div class="metric-card {failed_class}">
                <div class="metric-label">Processing Failures</div>
                <div class="metric-value">{failed_count}</div>
            </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Avg Filtered Score</div>
                <div class="metric-value">{avg_score:.1f}</div>
            </div>
        """, unsafe_allow_html=True)

    # Failed Files Breakdown (if any)
    if errors:
        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
        with st.expander(f"⚠️ **Processing Errors ({len(errors)} failed files)**", expanded=True):
            st.warning("The following files could not be parsed or processed:")
            for err in errors:
                st.markdown(f"- **`{err.get('file', 'Unknown')}`**: {err.get('error', 'Error during extraction')}")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Score Distribution
    if filtered_rankings:
        st.markdown("### 📊 Score Distribution")
        chart_df = pd.DataFrame([
            {"Candidate": r["candidate_name"].title(), "Score": r["final_score"]}
            for r in filtered_rankings
        ])
        st.bar_chart(chart_df.set_index("Candidate"), y="Score", color="#667eea", height=280)

        # Action / Export row
        exp_col1, exp_col2, _ = st.columns([1, 1, 2])
        with exp_col1:
            csv_path = Path("outputs/ranking.csv")
            if csv_path.exists():
                st.download_button(
                    "📥 Download CSV Report",
                    data=csv_path.read_bytes(),
                    file_name="ranking.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        with exp_col2:
            json_path = Path("outputs/ranking.json")
            if json_path.exists():
                st.download_button(
                    "📥 Download JSON Report",
                    data=json_path.read_bytes(),
                    file_name="ranking.json",
                    mime="application/json",
                    use_container_width=True,
                )

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        # Candidate Cards
        st.markdown(f"### 🏆 Ranked Candidates ({filtered_count})")

        for candidate in filtered_rankings:
            rank = candidate["rank"]
            name = candidate["candidate_name"]
            score = candidate["final_score"]
            bd = candidate["breakdown"]
            explanation = candidate.get("explanation", "")

            score_color = get_score_color(score)

            medal = ""
            if rank == 1: medal = " 🥇"
            elif rank == 2: medal = " 🥈"
            elif rank == 3: medal = " 🥉"

            label = f"Rank {rank}  ·  {name.title()}  ·  {score:.1f}/100{medal}"

            with st.expander(label, expanded=(rank <= 3)):
                top_row = st.columns([2, 3])

                with top_row[0]:
                    st.markdown(f"""
                        <div style="text-align:center; padding:1rem 0;">
                            <div style="font-size:3rem; font-weight:800; background:{score_color};
                                 -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                                {score:.1f}
                            </div>
                            <div style="font-size:0.85rem; color:#8892b0; font-weight:500;">out of 100</div>
                        </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                        <div style="text-align:center; margin-top:0.5rem;">
                            <span style="font-size:0.82rem; color:#8892b0;">Experience:</span>
                            <span style="font-size:0.95rem; color:#ccd6f6; font-weight:600;">
                                {bd.get('candidate_experience_years', 0):.1f} yrs
                            </span>
                            <span style="font-size:0.78rem; color:#4a5568;">
                                / {bd.get('required_experience_years', 0) or 0:.0f} required
                            </span>
                        </div>
                    """, unsafe_allow_html=True)

                with top_row[1]:
                    render_score_bar("Required Skills", bd["required_skill_score"])
                    render_score_bar("Preferred Skills", bd["preferred_skill_score"])
                    render_score_bar("Semantic Match", bd["semantic_similarity_score"])
                    render_score_bar("Experience", bd["experience_score"])
                    render_score_bar("Education", bd["education_score"])

                st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
                skills_cols = st.columns(3)

                with skills_cols[0]:
                    matched = bd.get("matched_required_skills", [])
                    if matched:
                        st.markdown("**✅ Matched Required**")
                        tags = "".join(f'<span class="skill-tag skill-matched">{s}</span>' for s in matched)
                        st.markdown(tags, unsafe_allow_html=True)

                with skills_cols[1]:
                    missing = bd.get("missing_required_skills", [])
                    if missing:
                        st.markdown("**❌ Missing Required**")
                        tags = "".join(f'<span class="skill-tag skill-missing">{s}</span>' for s in missing)
                        st.markdown(tags, unsafe_allow_html=True)
                    else:
                        st.markdown("**✅ No Missing Skills**")

                with skills_cols[2]:
                    preferred = bd.get("matched_preferred_skills", [])
                    if preferred:
                        st.markdown("**⭐ Matched Preferred**")
                        tags = "".join(f'<span class="skill-tag skill-preferred">{s}</span>' for s in preferred)
                        st.markdown(tags, unsafe_allow_html=True)

                if explanation:
                    st.markdown(
                        f'<div class="explanation-box">💡 {explanation}</div>',
                        unsafe_allow_html=True
                    )
    else:
        st.warning(f"No candidates scored above the {min_score:.1f} threshold. Lower the threshold in the sidebar to view more candidates.")
else:
    st.info("No screening results loaded. Use the upload tab above or load the sample dataset to run screening.")

# ─── Footer ───
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#4a5568; font-size:0.8rem; padding:1rem 0;'>"
    "AI Resume Screening Agent — Deterministic scoring • Grounded explanations • Fully offline"
    "</div>",
    unsafe_allow_html=True
)

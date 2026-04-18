# main.py
import time
import os
from io import BytesIO
from datetime import datetime

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import re
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from descriptors import DESCRIPTORS

# =========================
# GLOBAL CSS — step track, guidance boxes, ref badges
# =========================
CUSTOM_CSS = """
<style>
.step-track {
    display: flex; gap: 0; margin-bottom: 1.2rem;
    border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
    font-family: sans-serif;
}
.step {
    flex: 1; padding: 10px 8px; font-size: 11px; text-align: center;
    border-right: 1px solid #e5e7eb; background: #f9fafb;
}
.step:last-child { border-right: none; }
.step-done { background: #f0fdf4; }
.step-done .sn { background: #bbf7d0; color: #15803d; }
.step-done .sl { color: #15803d; }
.step-active { background: #eef2ff; }
.step-active .sn { background: #c7d2fe; color: #3730a3; }
.step-active .sl { color: #3730a3; font-weight: 600; }
.step-locked { background: #f9fafb; }
.step-locked .sn { background: #e5e7eb; color: #9ca3af; }
.step-locked .sl { color: #9ca3af; }
.sn {
    display: inline-flex; width: 20px; height: 20px; border-radius: 50%;
    align-items: center; justify-content: center;
    font-size: 10px; font-weight: 700; margin-bottom: 3px;
}
.sl { font-size: 11px; line-height: 1.35; display: block; }
.guidance-box {
    background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 8px;
    padding: 10px 14px; margin-bottom: 1rem; font-size: 13px;
    color: #312e81; line-height: 1.6;
}
.guidance-title {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.5px; color: #4338ca; margin-bottom: 4px; display: block;
}
.refl-box {
    background: #fafafa; border-left: 3px solid #818cf8; border-radius: 4px;
    padding: 8px 10px; margin: 6px 0 10px; font-size: 12px;
    color: #374151; line-height: 1.5;
}
.refl-label {
    font-size: 10px; font-weight: 700; color: #6366f1;
    text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 3px;
    display: block;
}
.next-action {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; background: #fef3c7; border: 1px solid #fbbf24;
    border-radius: 5px; font-size: 11px; font-weight: 600; color: #92400e;
    margin-bottom: 10px;
}
.locked-msg {
    font-size: 12px; color: #9ca3af; margin-top: 6px; font-style: italic;
}
</style>
"""

def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def step_track(steps):
    """
    steps: list of (label, status) where status is 'done'|'active'|'locked'
    """
    html = '<div class="step-track">'
    for i, (label, status) in enumerate(steps):
        html += f'<div class="step step-{status}"><div class="sn">{i+1}</div><div class="sl">{label}</div></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def guidance_box(title, body):
    st.markdown(
        f'<div class="guidance-box"><span class="guidance-title">{title}</span>{body}</div>',
        unsafe_allow_html=True
    )

def show_reflection(label, text):
    if text and text.strip():
        st.markdown(
            f'<div class="refl-box"><span class="refl-label">{label}</span>{text}</div>',
            unsafe_allow_html=True
        )

# =========================
# Helper functions
# =========================
def safe_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)

def title_case_name(name: str) -> str:
    return " ".join(part.capitalize() for part in safe_text(name).split())

def highlight_ratings(val):
    colors = {
        "HE": "background-color: #a8e6a1;",
        "E": "background-color: #d0f0fd;",
        "IN": "background-color: #fff3b0;",
        "DNMS": "background-color: #f8a5a5;",
        "Highly Effective": "background-color: #a8e6a1;",
        "Effective": "background-color: #d0f0fd;",
        "Improvement Necessary": "background-color: #fff3b0;",
        "Does Not Meet Standards": "background-color: #f8a5a5;",
    }
    return colors.get(val, "")

def rating_rank(value):
    order = {
        "Does Not Meet Standards": 1, "Improvement Necessary": 2,
        "Effective": 3, "Highly Effective": 4,
        "DNMS": 1, "IN": 2, "E": 3, "HE": 4,
    }
    return order.get(str(value).strip(), 0)

def rating_short(value):
    mapping = {
        "Highly Effective": "HE", "Effective": "E",
        "Improvement Necessary": "IN", "Does Not Meet Standards": "DNMS",
        "HE": "HE", "E": "E", "IN": "IN", "DNMS": "DNMS",
    }
    return mapping.get(str(value).strip(), str(value).strip())

def trend_arrow(initial_value, final_value):
    init_score = rating_rank(initial_value)
    final_score = rating_rank(final_value)
    if init_score == 0 or final_score == 0:
        return ""
    if final_score > init_score:
        return "↑ Improved"
    if final_score < init_score:
        return "↓ Dropped"
    return "→ No change"

def trend_style(val):
    styles = {
        "↑ Improved": "background-color: #d9f2d9; color: #1f6f1f; font-weight: bold;",
        "↓ Dropped": "background-color: #f8d7da; color: #842029; font-weight: bold;",
        "→ No change": "background-color: #eef2f7; color: #495057;"
    }
    return styles.get(val, "")

def build_initial_final_comparison(rows_df):
    if rows_df.empty:
        return None, None, pd.DataFrame()
    working = rows_df.copy()
    if "Assessment Cycle" not in working.columns:
        working["Assessment Cycle"] = "Initial"
    else:
        working["Assessment Cycle"] = working["Assessment Cycle"].replace("", "Initial")

    initial_rows = working[working["Assessment Cycle"] == "Initial"]
    final_rows = working[working["Assessment Cycle"] == "Final"]

    latest_initial = (
        initial_rows.sort_values("Timestamp", ascending=False).head(1)
        if not initial_rows.empty else None
    )
    latest_final = (
        final_rows.sort_values("Timestamp", ascending=False).head(1)
        if not final_rows.empty else None
    )

    comparison_rows = []
    for domain, items in DOMAINS.items():
        for code, label in items:
            strand = f"{code} {label}"
            init_val = ""
            final_val = ""
            if latest_initial is not None and not latest_initial.empty:
                init_val = safe_text(latest_initial.iloc[0].get(strand, ""))
            if latest_final is not None and not latest_final.empty:
                final_val = safe_text(latest_final.iloc[0].get(strand, ""))
            comparison_rows.append({
                "Domain": domain.split(":")[0],
                "Strand": strand,
                "Explanation": DESCRIPTORS.get(strand, {}).get("HE", ""),
                "Initial": rating_short(init_val),
                "Final": rating_short(final_val),
                "Trend": trend_arrow(init_val, final_val),
            })

    comparison_df = pd.DataFrame(comparison_rows)
    return latest_initial, latest_final, comparison_df

def rating_to_descriptor_key(rating_text):
    mapping = {
        "Highly Effective": "HE", "Effective": "E",
        "Improvement Necessary": "IN", "Does Not Meet Standards": "DNMS",
        "HE": "HE", "E": "E", "IN": "IN", "DNMS": "DNMS",
    }
    return mapping.get(safe_text(rating_text), "")

def highlight_rating(val):
    color_map = {
        "HE": "#a8e6a1", "E": "#d0f0fd",
        "IN": "#fff3b0", "DNMS": "#f8a5a5"
    }
    return f"background-color: {color_map.get(val, '')}; color: black;"

def highlight_trend(val):
    if "Improved" in val:
        return "color: green; font-weight: 600;"
    elif "Dropped" in val:
        return "color: red; font-weight: 600;"
    elif "No change" in val:
        return "color: #555; font-weight: 500;"
    return ""

def render_grouped_comparison(df, key_prefix="cmp", initial_record=None, final_record=None):
    """
    Renders domain-grouped comparison table.
    If initial_record / final_record supplied, also shows domain reflections below each domain.
    """
    if df.empty:
        st.info("No comparison data available.")
        return

    domain_titles = {
        "A": "Planning and Preparation for Learning",
        "B": "Classroom Management",
        "C": "Delivery of Instruction",
        "D": "Monitoring, Assessment, and Follow-Up",
        "E": "Family and Community Outreach",
        "F": "Professional Responsibility",
    }
    domain_full_keys = {
        "A": "A: Planning and Preparation for Learning",
        "B": "B: Classroom Management",
        "C": "C: Delivery of Instruction",
        "D": "D: Monitoring, Assessment, and Follow-Up",
        "E": "E: Family and Community Outreach",
        "F": "F: Professional Responsibility",
    }

    for domain in ["A", "B", "C", "D", "E", "F"]:
        domain_df = df[df["Domain"] == domain].copy()
        if domain_df.empty:
            continue

        display_df = domain_df[["Strand", "Initial", "Final", "Trend"]].copy()
        styled_df = (
            display_df.style
            .map(highlight_rating, subset=["Initial", "Final"])
            .map(highlight_trend, subset=["Trend"])
            .set_properties(subset=["Initial", "Final", "Trend"], **{
                "text-align": "center", "padding": "6px", "font-size": "13px"
            })
            .set_properties(subset=["Strand"], **{"padding": "6px", "font-size": "13px"})
        )

        expander_title = f"Domain {domain} — {domain_titles.get(domain, '')}"
        with st.expander(expander_title, expanded=(domain == "A")):
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # Show reflections if records provided
            if initial_record is not None or final_record is not None:
                full_key = domain_full_keys.get(domain, "")
                refl_key = f"{full_key} Reflection"

                init_refl = safe_text(initial_record.get(refl_key, "")) if initial_record else ""
                final_refl = safe_text(final_record.get(refl_key, "")) if final_record else ""

                if init_refl or final_refl:
                    st.markdown("**Domain reflections:**")
                    if init_refl:
                        show_reflection("Initial reflection", init_refl)
                    if final_refl:
                        show_reflection("Final reflection", final_refl)

# =========================
# DOCX generation helpers
# =========================
def add_summary_section_to_doc(doc, latest_record):
    doc.add_heading("OIS Teacher Appraisal Summary", level=1)
    p = doc.add_paragraph()
    p.add_run("Teacher: ").bold = True
    p.add_run(safe_text(latest_record.get("Name", "")))
    p = doc.add_paragraph()
    p.add_run("Appraiser: ").bold = True
    p.add_run(safe_text(latest_record.get("Appraiser", "")))
    p = doc.add_paragraph()
    p.add_run("Submitted on: ").bold = True
    p.add_run(safe_text(latest_record.get("Timestamp", "")))
    p = doc.add_paragraph()
    p.add_run("Last edited on: ").bold = True
    p.add_run(safe_text(latest_record.get("Last Edited On", "")))
    doc.add_paragraph("")
    for domain, items in DOMAINS.items():
        doc.add_heading(domain, level=2)
        for code, label in items:
            strand_key = f"{code} {label}"
            selected_rating = safe_text(latest_record.get(strand_key, ""))
            descriptor_key = rating_to_descriptor_key(selected_rating)
            explanation = ""
            if strand_key in DESCRIPTORS and descriptor_key in DESCRIPTORS[strand_key]:
                explanation = safe_text(DESCRIPTORS[strand_key][descriptor_key])
            p = doc.add_paragraph()
            p.add_run(f"{strand_key}\n").bold = True
            p.add_run("Selected Rating: ").bold = True
            p.add_run(f"{selected_rating}\n")
            p.add_run("Explanation: ").bold = True
            p.add_run(explanation if explanation else "No explanation found.")
        domain_reflection = safe_text(latest_record.get(f"{domain} Reflection", ""))
        if domain_reflection:
            p = doc.add_paragraph()
            p.add_run("Domain Reflection: ").bold = True
            p.add_run(domain_reflection)
        doc.add_paragraph("")

def generate_teacher_docx(teacher_name, latest_df):
    latest_record = latest_df.iloc[0].to_dict()
    doc = Document()
    add_summary_section_to_doc(doc, latest_record)
    out = BytesIO()
    doc.save(out)
    out.seek(0)
    return out

def generate_final_evaluation_docx(record: dict):
    template_path = os.path.join(os.path.dirname(__file__), "..", "Copy of Letter template OIS JVLR.docx")
    try:
        doc = Document(template_path)
    except Exception:
        doc = Document()

    teacher_name = title_case_name(record.get("Teacher Name", ""))
    appraiser_name = title_case_name(record.get("Appraiser", ""))
    subject_area = safe_text(record.get("Subject Area", ""))

    if doc.paragraphs:
        first_para = doc.paragraphs[0]
        first_para.paragraph_format.space_before = Pt(0)
        first_para.paragraph_format.space_after = Pt(0)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run("FINAL EVALUATION SUMMARY")
    run.bold = True
    run.font.size = Pt(14)
    doc.add_paragraph("")

    for label_text, field in [
        ("Teacher: ", "Teacher Name"),
        ("Appraiser: ", "Appraiser"),
        ("Subject Area: ", "Subject Area"),
    ]:
        p = doc.add_paragraph()
        p.add_run(label_text).bold = True
        p.add_run(title_case_name(record.get(field, "")) if field in ["Teacher Name", "Appraiser"] else safe_text(record.get(field, "")))

    doc.add_paragraph("")

    p = doc.add_paragraph()
    run = p.add_run("Student Survey Feedback")
    run.bold = True; run.font.size = Pt(12)
    p = doc.add_paragraph()
    p.add_run("Administered by the teacher each Semester").italic = True
    doc.add_paragraph(safe_text(record.get("Student Survey Feedback", "")))
    doc.add_paragraph("")

    p = doc.add_paragraph()
    run = p.add_run("Overall Reflection by the teacher on the school year")
    run.bold = True; run.font.size = Pt(12)
    doc.add_paragraph(safe_text(record.get("Overall Reflection", "")))
    doc.add_paragraph("")

    p = doc.add_paragraph()
    run = p.add_run("Ratings on Individual Rubrics")
    run.bold = True; run.font.size = Pt(12)

    for col_name, label in final_eval_domain_rows():
        p = doc.add_paragraph()
        p.add_run(f"{label}: ").bold = True
        p.add_run(safe_text(record.get(col_name, "")))

    doc.add_paragraph("")

    p = doc.add_paragraph()
    run = p.add_run("Overall Rating")
    run.bold = True; run.font.size = Pt(12)
    p = doc.add_paragraph()
    run = p.add_run(safe_text(record.get("Overall Rating", "")))
    run.bold = True
    doc.add_paragraph("")

    p = doc.add_paragraph()
    run = p.add_run("Overall Appraiser Comments")
    run.bold = True; run.font.size = Pt(12)
    doc.add_paragraph(safe_text(record.get("Overall Comments", "")))
    doc.add_paragraph("")

    p = doc.add_paragraph()
    run = p.add_run("Sign Off")
    run.bold = True; run.font.size = Pt(12)
    p = doc.add_paragraph()
    p.add_run(f"{appraiser_name} signed off on: ").bold = True
    p.add_run(safe_text(record.get("Evaluator Sign Off Date", "")))
    p = doc.add_paragraph()
    p.add_run(f"{teacher_name} signed off on: ").bold = True
    p.add_run(safe_text(record.get("Teacher Sign Off Date", "")))
    doc.add_paragraph("")
    doc.add_paragraph(
        "The teacher's signature indicates that he or she has seen and discussed the evaluation; "
        "it does not necessarily denote agreement with the report."
    )

    out = BytesIO()
    doc.save(out)
    out.seek(0)
    return out

def build_teacher_initial_final(email):
    df = load_responses_df()
    mine = df[df["Email"] == email.strip().lower()] if not df.empty else pd.DataFrame()
    if mine.empty:
        return None, None, pd.DataFrame()
    if "Assessment Cycle" not in mine.columns:
        mine["Assessment Cycle"] = "Initial"
    else:
        mine["Assessment Cycle"] = mine["Assessment Cycle"].replace("", "Initial")

    initial_rows = mine[mine["Assessment Cycle"] == "Initial"]
    final_rows = mine[mine["Assessment Cycle"] == "Final"]

    latest_initial = (
        initial_rows.sort_values("Timestamp", ascending=False).head(1)
        if not initial_rows.empty else None
    )
    latest_final = (
        final_rows.sort_values("Timestamp", ascending=False).head(1)
        if not final_rows.empty else None
    )

    comparison_rows = []
    for domain, items in DOMAINS.items():
        for code, label in items:
            strand = f"{code} {label}"
            init_val = ""
            final_val = ""
            if latest_initial is not None and not latest_initial.empty:
                init_val = safe_text(latest_initial.iloc[0].get(strand, ""))
            if latest_final is not None and not latest_final.empty:
                final_val = safe_text(latest_final.iloc[0].get(strand, ""))
            comparison_rows.append({
                "Domain": domain.split(":")[0],
                "Strand": strand,
                "Explanation": DESCRIPTORS.get(strand, {}).get("HE", ""),
                "Initial": rating_short(init_val),
                "Final": rating_short(final_val),
                "Trend": trend_arrow(init_val, final_val),
            })

    comparison_df = pd.DataFrame(comparison_rows)
    return latest_initial, latest_final, comparison_df

def render_comparison_html(df):
    if df.empty:
        return "<p>No comparison data available.</p>"

    rating_bg = {"HE": "#a8e6a1", "E": "#d0f0fd", "IN": "#fff3b0", "DNMS": "#f8a5a5"}
    trend_bg = {
        "↑ Improved": "#d9f2d9", "↓ Dropped": "#f8d7da",
        "→ No change": "#eef2f7", "": "#ffffff",
    }

    html = """
    <div style="overflow-x:auto;">
      <table style="border-collapse:collapse;width:100%;table-layout:fixed;font-family:Arial,sans-serif;font-size:13px;">
        <thead>
          <tr style="background-color:#f5f6f7;">
            <th style="border:1px solid #ddd;padding:8px;width:7%;text-align:left;">Domain</th>
            <th style="border:1px solid #ddd;padding:8px;width:14%;text-align:left;">Strand</th>
            <th style="border:1px solid #ddd;padding:8px;width:49%;text-align:left;">Explanation</th>
            <th style="border:1px solid #ddd;padding:8px;width:8%;text-align:center;">Initial</th>
            <th style="border:1px solid #ddd;padding:8px;width:8%;text-align:center;">Final</th>
            <th style="border:1px solid #ddd;padding:8px;width:14%;text-align:center;">Trend</th>
          </tr>
        </thead>
        <tbody>
    """

    for _, row in df.iterrows():
        initial = safe_text(row.get("Initial", ""))
        final = safe_text(row.get("Final", ""))
        trend = safe_text(row.get("Trend", ""))
        initial_bg = rating_bg.get(initial, "#ffffff")
        final_bg = rating_bg.get(final, "#ffffff")
        trend_bg_color = trend_bg.get(trend, "#ffffff")
        explanation_html = safe_text(row.get("Explanation", "")).replace("\n", "<br>")

        html += f"""
          <tr>
            <td style="border:1px solid #ddd;padding:8px;vertical-align:top;">{safe_text(row.get("Domain",""))}</td>
            <td style="border:1px solid #ddd;padding:8px;vertical-align:top;">{safe_text(row.get("Strand",""))}</td>
            <td style="border:1px solid #ddd;padding:8px;vertical-align:top;white-space:normal;word-wrap:break-word;overflow-wrap:break-word;line-height:1.4;">{explanation_html}</td>
            <td style="border:1px solid #ddd;padding:8px;text-align:center;background:{initial_bg};font-weight:bold;">{initial}</td>
            <td style="border:1px solid #ddd;padding:8px;text-align:center;background:{final_bg};font-weight:bold;">{final}</td>
            <td style="border:1px solid #ddd;padding:8px;text-align:center;background:{trend_bg_color};font-weight:bold;">{trend}</td>
          </tr>
        """

    html += "</tbody></table></div>"
    return html

def build_printable_comparison_html(teacher_name, teacher_email, appraiser, latest_initial, latest_final, display_df):
    initial_date = ""
    final_date = ""
    if latest_initial is not None and not latest_initial.empty:
        initial_date = safe_text(latest_initial.iloc[0].get("Timestamp", ""))
    if latest_final is not None and not latest_final.empty:
        final_date = safe_text(latest_final.iloc[0].get("Timestamp", ""))

    table_html = render_comparison_html(display_df)
    html = f"""
    <html><head><title>{teacher_name} - Initial vs Final Comparison</title>
    <style>
        body{{font-family:Arial,sans-serif;margin:24px;color:#111;}}
        h1{{font-size:24px;margin-bottom:8px;}}
        h2{{font-size:18px;margin-top:0;margin-bottom:20px;color:#444;}}
        .meta{{margin-bottom:20px;line-height:1.6;font-size:14px;}}
        .meta strong{{display:inline-block;min-width:140px;}}
        .print-btn{{margin-bottom:20px;}}
        @media print{{.print-btn{{display:none;}}body{{margin:10mm;}}}}
    </style></head>
    <body>
        <div class="print-btn"><button onclick="window.print()" style="padding:10px 16px;font-size:14px;cursor:pointer;">Print</button></div>
        <h1>{teacher_name}</h1>
        <h2>Initial vs Final Self-Assessment Comparison</h2>
        <div class="meta">
            <div><strong>Email:</strong> {teacher_email}</div>
            <div><strong>Appraiser:</strong> {appraiser}</div>
            <div><strong>Initial Submitted:</strong> {initial_date or "-"}</div>
            <div><strong>Final Submitted:</strong> {final_date or "-"}</div>
        </div>
        {table_html}
    </body></html>
    """
    return html

# =========================
# FINAL EVALUATION HELPERS
# =========================
def count_words(text):
    return len(re.findall(r"\b\S+\b", safe_text(text)))

def is_before_deadline(deadline_dt):
    return datetime.now() <= deadline_dt

def teacher_can_start_final_evaluation(email: str) -> bool:
    return user_has_submission(email, cycle="Final")

def final_eval_expected_headers():
    return [
        "Timestamp", "Last Edited On", "Teacher Email", "Teacher Name",
        "Appraiser", "Subject Area", "Student Survey Feedback", "Overall Reflection",
        "Teacher Submitted", "Teacher Submitted On", "Appraiser Started",
        "Appraiser Completed", "Appraiser Completed On",
        "A Rating", "B Rating", "C Rating", "D Rating", "E Rating", "F Rating",
        "Overall Rating", "Overall Comments",
        "Evaluator Sign Off", "Evaluator Sign Off Date",
        "Teacher Sign Off", "Teacher Sign Off Date",
    ]

@st.cache_resource
def ensure_final_eval_headers_once():
    exp = final_eval_expected_headers()
    current = with_backoff(FINAL_EVAL_WS.row_values, 1)
    if not current:
        with_backoff(FINAL_EVAL_WS.insert_row, exp, 1)
        return True
    if current != exp:
        st.warning(
            "The existing header row in **FinalEvaluation** does not match the expected structure. "
            "Submissions may misalign if the header was changed manually."
        )
    return True

@st.cache_data(ttl=180)
def load_final_eval_df():
    vals = with_backoff(FINAL_EVAL_WS.get_all_values)
    if not vals:
        return pd.DataFrame(columns=final_eval_expected_headers())
    header, rows = vals[0], vals[1:]
    df = pd.DataFrame(rows, columns=header) if rows else pd.DataFrame(columns=header)
    if "Teacher Email" in df.columns:
        df["Teacher Email"] = df["Teacher Email"].astype(str).str.strip().str.lower()
    if "Appraiser" in df.columns:
        df["Appraiser"] = df["Appraiser"].astype(str).str.strip().str.lower()
    return df

def get_teacher_final_eval_record(teacher_email: str):
    df = load_final_eval_df()
    if df.empty:
        return {}
    teacher_email = teacher_email.strip().lower()
    rows = df[df["Teacher Email"] == teacher_email]
    if rows.empty:
        return {}
    if "Timestamp" in rows.columns:
        rows = rows.sort_values("Timestamp", ascending=False)
    return dict(rows.iloc[0])

def save_final_eval_record(record: dict):
    headers = final_eval_expected_headers()
    df = load_final_eval_df()
    teacher_email = safe_text(record.get("Teacher Email", "")).strip().lower()
    row_values = [record.get(col, "") for col in headers]
    if not df.empty and "Teacher Email" in df.columns:
        matches = df[df["Teacher Email"].astype(str).str.strip().str.lower() == teacher_email]
        if not matches.empty:
            row_num = matches.index[0] + 2
            with_backoff(FINAL_EVAL_WS.update, f"A{row_num}:Y{row_num}", [row_values])
            load_final_eval_df.clear()
            return
    with_backoff(FINAL_EVAL_WS.append_row, row_values, value_input_option="USER_ENTERED")
    load_final_eval_df.clear()

def teacher_final_eval_completed(teacher_email: str) -> bool:
    rec = get_teacher_final_eval_record(teacher_email)
    return safe_text(rec.get("Teacher Submitted", "")).strip().lower() == "yes"

def appraiser_final_eval_completed(teacher_email: str) -> bool:
    rec = get_teacher_final_eval_record(teacher_email)
    return safe_text(rec.get("Appraiser Completed", "")).strip().lower() == "yes"

def evaluator_signed_off(teacher_email: str) -> bool:
    rec = get_teacher_final_eval_record(teacher_email)
    return safe_text(rec.get("Evaluator Sign Off", "")).strip().lower() == "yes"

def teacher_signed_off_final_eval(teacher_email: str) -> bool:
    rec = get_teacher_final_eval_record(teacher_email)
    return safe_text(rec.get("Teacher Sign Off", "")).strip().lower() == "yes"

def final_eval_domain_rows():
    return [
        ("A Rating", "A. Planning and Preparation for Learning"),
        ("B Rating", "B. Classroom Management"),
        ("C Rating", "C. Delivery of Instruction"),
        ("D Rating", "D. Monitoring, Assessment, and Follow-Up"),
        ("E Rating", "E. Family and Community Outreach"),
        ("F Rating", "F. Professional Responsibilities"),
    ]

def teacher_started_final_evaluation(teacher_email: str) -> bool:
    rec = get_teacher_final_eval_record(teacher_email)
    if not rec:
        return False
    return any([
        safe_text(rec.get("Teacher Submitted", "")).strip().lower() == "yes",
        safe_text(rec.get("Subject Area", "")).strip() != "",
        safe_text(rec.get("Student Survey Feedback", "")).strip() != "",
        safe_text(rec.get("Overall Reflection", "")).strip() != "",
    ])

def teacher_can_edit_final_self_assessment(teacher_email: str) -> bool:
    if not user_has_submission(teacher_email, cycle="Final"):
        return False
    if teacher_started_final_evaluation(teacher_email):
        return False
    return True

def domain_letter_from_strand(strand_code: str) -> str:
    return safe_text(strand_code).split()[0][:1]

def get_full_appraiser_name(appraiser_value: str) -> str:
    raw = safe_text(appraiser_value).strip()
    if not raw:
        return "Not Assigned"
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    if not parts:
        return raw
    matched_names = []
    for part in parts:
        match = users_df[
            users_df["Name"].astype(str).str.strip().str.lower().str.split().str[0] == part
        ]
        if not match.empty:
            matched_names.extend(match["Name"].astype(str).tolist())
        else:
            matched_names.append(part.title())
    return ", ".join(dict.fromkeys(matched_names))

def render_final_evaluation_review_panel(record: dict, heading: str = "Appraiser Review"):
    rating_colour_map = {
        "Highly Effective": "#d4edda", "Effective": "#d1ecf1",
        "Improvement Necessary": "#fff3cd", "Does Not Meet Standards": "#f8d7da",
    }
    text_colour_map = {
        "Highly Effective": "#155724", "Effective": "#0c5460",
        "Improvement Necessary": "#856404", "Does Not Meet Standards": "#721c24",
    }
    st.markdown(f"### {heading}")
    st.markdown("#### Ratings on Individual Rubrics")
    cols = st.columns(2)
    for i, (col_name, label) in enumerate(final_eval_domain_rows()):
        rating_value = safe_text(record.get(col_name, ""))
        bg = rating_colour_map.get(rating_value, "#f4f4f4")
        fg = text_colour_map.get(rating_value, "#222")
        with cols[i % 2]:
            st.markdown(
                f"""<div style="border:1px solid #e6e6e6;border-radius:12px;padding:14px 16px;
                margin-bottom:12px;background:#ffffff;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                <div style="font-size:14px;font-weight:600;color:#333;margin-bottom:10px;">{label}</div>
                <div style="display:inline-block;padding:8px 12px;border-radius:999px;
                background:{bg};color:{fg};font-weight:700;font-size:13px;">{rating_value}</div></div>""",
                unsafe_allow_html=True
            )

    st.markdown("### Overall Rating")
    overall_rating = safe_text(record.get("Overall Rating", ""))
    overall_bg = rating_colour_map.get(overall_rating, "#f4f4f4")
    overall_fg = text_colour_map.get(overall_rating, "#222")
    st.markdown(
        f"""<div style="border:2px solid #dcdcdc;border-radius:14px;padding:18px;
        margin-top:8px;margin-bottom:14px;background:#fafafa;box-shadow:0 1px 6px rgba(0,0,0,0.05);">
        <div style="font-size:15px;font-weight:600;color:#333;margin-bottom:12px;">Final Overall Rating</div>
        <div style="display:inline-block;padding:10px 16px;border-radius:999px;
        background:{overall_bg};color:{overall_fg};font-weight:700;font-size:15px;">{overall_rating}</div></div>""",
        unsafe_allow_html=True
    )

    st.markdown("### Appraiser Comments")
    comments_text = safe_text(record.get("Overall Comments", "")).replace("\n", "<br>")
    st.markdown(
        f"""<div style="border:1px solid #e6e6e6;border-radius:12px;padding:16px;
        background:#ffffff;box-shadow:0 1px 4px rgba(0,0,0,0.06);line-height:1.6;
        color:#333;margin-bottom:12px;">{comments_text}</div>""",
        unsafe_allow_html=True
    )

# =========================
# UI CONFIG (must be first Streamlit call)
# =========================
st.set_page_config(page_title="OIS Teacher Appraisal", layout="wide")

try:
    from googleapiclient.errors import HttpError
except Exception:
    class HttpError(Exception):
        pass

def _rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# =========================
# CONFIG
# =========================
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
ENABLE_REFLECTIONS = True
CURRENT_ASSESSMENT_CYCLE = "Final"   # "Initial" or "Final"
FINAL_EVAL_SHEET_NAME = "FinalEvaluation"

FINAL_EVAL_TEACHER_DEADLINE = datetime(2026, 4, 30, 23, 59, 59)
FINAL_EVAL_APPRAISER_DEADLINE = datetime(2026, 5, 20, 23, 59, 59)

FINAL_EVAL_MAX_WORDS_SURVEY = 150
FINAL_EVAL_MAX_WORDS_REFLECTION = 150
FINAL_EVAL_MAX_WORDS_COMMENTS = 150

FINAL_EVAL_RATINGS = [
    "Highly Effective", "Effective",
    "Improvement Necessary", "Does Not Meet Standards",
]

SUBJECT_AREA_OPTIONS = [
    "English", "Mathematics", "Science", "Individuals and Societies",
    "Languages", "Design", "Physical and Health Education",
    "Visual Arts", "Music", "Theatre", "Computer Science", "SSP", "Other",
]

ADMINS_FROM_SECRETS = set([e.strip().lower() for e in st.secrets.get("admins", [])])
IST_OFFSET_HOURS = 5
IST_OFFSET_MINUTES = 30

def now_ist():
    return datetime.utcnow() + pd.Timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES)

def now_ist_str():
    return now_ist().strftime("%Y-%m-%d %H:%M:%S")

def fmt_ist(dt_value):
    txt = safe_text(dt_value)
    return txt if txt else "-"

# =========================
# DOMAINS & SUB-STRANDS
# =========================
DOMAINS = {
    "A: Planning and Preparation for Learning": [
        ("A1", "Expertise"), ("A2", "Goals"), ("A3", "Units"),
        ("A4", "Assessments"), ("A5", "Anticipation"), ("A6", "Lessons"),
        ("A7", "Materials"), ("A8", "Differentiation"), ("A9", "Environment"),
    ],
    "B: Classroom Management": [
        ("B1", "Expectations"), ("B2", "Relationships"), ("B3", "Social Emotional"),
        ("B4", "Routines"), ("B5", "Responsibility"), ("B6", "Repertoire"),
        ("B7", "Prevention"), ("B8", "Incentives"),
    ],
    "C: Delivery of Instruction": [
        ("C1", "Expectations"), ("C2", "Mindset"), ("C3", "Framing"),
        ("C4", "Connections"), ("C5", "Clarity"), ("C6", "Repertoire"),
        ("C7", "Engagement"), ("C8", "Differentiation"), ("C9", "Nimbleness"),
    ],
    "D: Monitoring, Assessment, and Follow-Up": [
        ("D1", "Criteria"), ("D2", "Diagnosis"), ("D3", "Goals"),
        ("D4", "Feedback"), ("D5", "Recognition"), ("D6", "Analysis"),
        ("D7", "Tenacity"), ("D8", "Support"), ("D9", "Reflection"),
    ],
    "E: Family and Community Outreach": [
        ("E1", "Respect"), ("E2", "Belief"), ("E3", "Expectations"),
        ("E4", "Communication"), ("E5", "Involving"), ("E6", "Responsiveness"),
        ("E7", "Reporting"), ("E8", "Outreach"), ("E9", "Resources"),
    ],
    "F: Professional Responsibility": [
        ("F1", "Language"), ("F2", "Reliability"), ("F3", "Professionalism"),
        ("F4", "Judgement"), ("F5", "Teamwork"), ("F6", "Leadership"),
        ("F7", "Openness"), ("F8", "Collaboration"), ("F9", "Growth"),
    ],
}

RATINGS = [
    "Highly Effective", "Effective",
    "Improvement Necessary", "Does Not Meet Standards",
]

# =========================
# Retry/backoff for Sheets
# =========================
def with_backoff(fn, *args, **kwargs):
    max_attempts = 5
    delay = 0.6
    last_exc = None
    for _ in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except HttpError as e:
            status = getattr(e, "status_code", None)
            if status in (429, 500, 502, 503, 504):
                time.sleep(delay); delay *= 2; last_exc = e; continue
            raise
        except gspread.exceptions.APIError as e:
            msg = str(e).lower()
            if any(code in msg for code in ["429", "500", "502", "503", "504"]):
                time.sleep(delay); delay *= 2; last_exc = e; continue
            raise
        except Exception as e:
            time.sleep(delay); delay *= 2; last_exc = e; continue
    if last_exc:
        raise last_exc
    return fn(*args, **kwargs)

# =========================
# Google Sheet Connections
# =========================
@st.cache_resource
def get_worksheets():
    client = gspread.authorize(
        Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
    )
    sh = client.open_by_key(SPREADSHEET_ID)
    resp_ws = sh.worksheet("Responses")
    users_ws = sh.worksheet("Users")
    try:
        drafts_ws = sh.worksheet("Drafts")
    except gspread.exceptions.WorksheetNotFound:
        drafts_ws = sh.add_worksheet(title="Drafts", rows="1000", cols="100")
        drafts_ws.update([["Email"]])
    try:
        final_eval_ws = sh.worksheet(FINAL_EVAL_SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        final_eval_ws = sh.add_worksheet(title=FINAL_EVAL_SHEET_NAME, rows="1000", cols="50")
    return resp_ws, users_ws, drafts_ws, final_eval_ws

RESP_WS, USERS_WS, DRAFTS_WS, FINAL_EVAL_WS = get_worksheets()

# =========================
# DRAFT HELPERS
# =========================
def save_draft(email, form_data):
    try:
        all_drafts = DRAFTS_WS.get_all_records()
        emails = [row["Email"] for row in all_drafts]
        row_data = [email] + [form_data.get(f, "") for f in form_data.keys()]
        if email in emails:
            row_num = emails.index(email) + 2
            DRAFTS_WS.update(f"A{row_num}", [row_data])
        else:
            if not all_drafts:
                headers = ["Email"] + list(form_data.keys())
                DRAFTS_WS.append_row(headers, value_input_option="USER_ENTERED")
            DRAFTS_WS.append_row(row_data, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"⚠️ Could not save draft: {e}")
        return False

def load_draft(email):
    try:
        all_drafts = pd.DataFrame(DRAFTS_WS.get_all_records())
        user_draft = all_drafts[all_drafts["Email"] == email]
        if not user_draft.empty:
            return dict(user_draft.iloc[0])
    except Exception:
        return {}
    return {}

# =========================
# HEADER MANAGEMENT
# =========================
def expected_headers():
    headers = ["Timestamp", "Email", "Name", "Appraiser", "Assessment Cycle"]
    for domain, items in DOMAINS.items():
        for code, label in items:
            headers.append(f"{code} {label}")
        if ENABLE_REFLECTIONS:
            headers.append(f"{domain} Reflection")
    headers.append("Last Edited On")
    return headers

@st.cache_resource
def ensure_headers_once():
    exp = expected_headers()
    current = with_backoff(RESP_WS.row_values, 1)
    if not current:
        with_backoff(RESP_WS.insert_row, exp, 1)
        return True
    if current != exp:
        st.warning(
            "The existing header row in **Responses** does not match the current rubric. "
            "Submissions will still append, but columns may be misaligned if the rubric changed."
        )
    return True

ensure_headers_once()
ensure_final_eval_headers_once()

# =========================
# USERS: load once
# =========================
def _pick_col(candidates, cols):
    norm_map = {c.strip().lower(): c for c in cols}
    for want in candidates:
        key = want.strip().lower()
        if key in norm_map:
            return norm_map[key]
    for c in cols:
        cl = c.strip().lower()
        if any(w in cl for w in candidates):
            return c
    return None

@st.cache_resource
def load_users_once_df():
    records = with_backoff(USERS_WS.get_all_records)
    if not records:
        return pd.DataFrame(columns=["Email", "Name", "Appraiser", "Role", "Password", "Campus"])
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["Email", "Name", "Appraiser", "Role", "Password", "Campus"])
    cols = list(df.columns)
    email_header     = _pick_col(["email", "school email", "work email", "ois email", "e-mail"], cols)
    name_header      = _pick_col(["name", "full name", "teacher name", "staff name"], cols)
    appraiser_header = _pick_col(["appraiser", "line manager", "manager", "appraiser name", "supervisor"], cols)
    role_header      = _pick_col(["role", "access", "admin"], cols)
    password_header  = _pick_col(["password", "pwd", "pass"], cols)
    campus_header    = _pick_col(["campus"], cols)
    out = pd.DataFrame()
    out["Email"] = (
        df[email_header].astype(str).str.strip().str.lower() if email_header else ""
    )
    out["Name"] = (
        df[name_header].astype(str).str.strip() if name_header else ""
    )
    out["Appraiser"] = (
        df[appraiser_header].astype(str).str.strip().replace({"": "Not Assigned"})
        if appraiser_header else "Not Assigned"
    )
    out["Role"] = (
        df[role_header].astype(str).str.strip().str.lower() if role_header else ""
    )
    out["Password"] = (
        df[password_header].astype(str).str.strip() if password_header else ""
    )
    out["Campus"] = (
        df[campus_header].astype(str).str.strip() if campus_header else ""
    )
    return out

users_df = load_users_once_df()

# =========================
# RESPONSES cache
# =========================
@st.cache_data(ttl=180)
def load_responses_df():
    vals = with_backoff(RESP_WS.get_all_values)
    if not vals:
        return pd.DataFrame()
    header, rows = vals[0], vals[1:]
    df = pd.DataFrame(rows, columns=header) if rows else pd.DataFrame(columns=header)
    if "Email" in df.columns:
        df["Email"] = df["Email"].astype(str).str.lower()
    if "Assessment Cycle" not in df.columns:
        df["Assessment Cycle"] = "Initial"
    else:
        df["Assessment Cycle"] = df["Assessment Cycle"].replace("", "Initial")
    return df

def user_has_submission(email: str, cycle: str | None = None) -> bool:
    if not email:
        return False
    df = load_responses_df()
    if df.empty or "Email" not in df.columns:
        return False
    filtered = df[df["Email"] == email.strip().lower()]
    if cycle is not None and "Assessment Cycle" in df.columns:
        filtered = filtered[filtered["Assessment Cycle"] == cycle]
    return not filtered.empty

# =========================
# Authentication
# =========================
def authenticate_user(email, password):
    email = email.strip().lower()
    user_row = users_df[users_df["Email"].str.lower() == email]
    if user_row.empty:
        return None, None
    role = user_row.iloc[0]["Role"].strip().lower()
    if role == "admin":
        return ("admin", user_row.iloc[0]) if password == "OIS2025" else (None, None)
    if role == "sadmin":
        return ("sadmin", user_row.iloc[0]) if password == "SOIS2025" else (None, None)
    if role == "user":
        stored_pw = str(user_row.iloc[0].get("Password", "")).strip()
        entered_pw = str(password).strip()
        if stored_pw and entered_pw and stored_pw == entered_pw:
            return "user", user_row.iloc[0]
        else:
            return None, None

# =========================
# AUTH CHECK
# =========================
inject_css()

user_name = st.session_state.get("auth_name", "")
campus_label = st.session_state.get("auth_campus", "")

with st.sidebar:
    st.markdown("### 👤 Logged in as")
    if user_name:
        st.markdown(f"**{user_name}**")
    if campus_label:
        st.markdown(f"🏫 **{campus_label} Campus**")

if "auth_email" not in st.session_state or not st.session_state.auth_email:
    st.info("Please log in first.")
    st.stop()

if st.sidebar.button("🚪 **LOGOUT**", type="primary", use_container_width=True):
    for key in ["token", "auth_email", "auth_name", "auth_role", "auth_campus", "submitted"]:
        if key in st.session_state:
            del st.session_state[key]
    st.cache_data.clear()
    st.cache_resource.clear()
    st.switch_page("app.py")

# =========================
# Sidebar: Live progress (teachers only)
# =========================
total_items = sum(len(v) for v in DOMAINS.values())

def current_progress_from_session() -> int:
    count = 0
    for _, items in DOMAINS.items():
        for code, label in items:
            if st.session_state.get(f"{code}-{label}"):
                count += 1
    return count

if st.session_state.get("auth_role") == "user":
    with st.sidebar.expander("📊 Progress", expanded=True):
        done = current_progress_from_session()
        st.progress(done / total_items if total_items else 0.0)
        st.caption(f"{done}/{total_items} sub-strands rated")

# =========================
# MAIN
# =========================
st.title("🌟 OIS Teacher Appraisal 2025-26")

if not st.session_state.auth_email:
    st.info("Please log in from the sidebar to continue.")
    st.stop()

already_submitted = user_has_submission(
    st.session_state.auth_email,
    cycle=CURRENT_ASSESSMENT_CYCLE
)

me_row = users_df[users_df["Email"] == st.session_state.auth_email]
if me_row.empty:
    role = "user"
    campus = ""
else:
    role = str(me_row.iloc[0].get("Role", "user")).lower().strip()
    campus = str(me_row.iloc[0].get("Campus", "")).strip()

st.session_state.auth_role = role
st.session_state.auth_campus = campus

i_am_admin = (role == "admin")
i_am_sadmin = (role == "sadmin")

# Navigation
if i_am_sadmin:
    nav_options = ["Super Admin"]
elif i_am_admin:
    nav_options = ["Admin"]
else:
    teacher_has_final_self = teacher_can_start_final_evaluation(st.session_state.auth_email)
    if already_submitted:
        nav_options = ["My Submission"]
    else:
        nav_options = ["Self-Assessment (Initial & Final)", "My Submission"]
    nav_options.append("Final Evaluation")
    if not teacher_has_final_self:
        st.sidebar.caption("⏳ Final Evaluation unlocks after Final self-assessment is submitted.")

tab = st.sidebar.radio("Menu", nav_options, index=0)
admin_view_mode = None
if tab == "Admin" and i_am_admin:
    admin_view_mode = st.sidebar.selectbox(
        "Jump to",
        ["Summary of Teachers", "View Teacher Self-Assessment", "Self-Assessment Grid"],
        index=0
    )

sadmin_view_mode = None
if tab == "Super Admin" and i_am_sadmin:
    sadmin_view_mode = st.sidebar.selectbox(
        "Jump to",
        ["Summary of Teachers", "View Teacher Self-Assessment", "Self-Assessment Grid"],
        index=0
    )

# =========================
# Page: Self-Assessment
# =========================
from descriptors import DESCRIPTORS

if tab == "Self-Assessment (Initial & Final)":
    if already_submitted and not i_am_admin:
        st.success("✅ You've already submitted your self-assessment. Redirecting to your submission...")
        tab = "My Submission"
    else:
        me = users_df[users_df["Email"] == st.session_state.auth_email].iloc[0] if not users_df.empty else {}
        appraiser = me.get("Appraiser", "Not Assigned") if isinstance(me, pd.Series) else "Not Assigned"
        st.sidebar.info(f"Your appraiser: **{appraiser}**")

        draft_data = load_draft(st.session_state.auth_email) or {}
        latest_initial, latest_final, comparison_df = build_teacher_initial_final(
            st.session_state.auth_email
        )

        if draft_data:
            st.info("💾 A saved draft was found and preloaded. You can continue where you left off.")

        # ── Step track ──
        if CURRENT_ASSESSMENT_CYCLE == "Final":
            step_track([
                ("Initial self-assessment\nSep 2025 ✓", "done"),
                ("Final self-assessment\nIn progress", "active"),
                ("Final evaluation\nUnlocks after step 2", "locked"),
                ("Sign-off\nAfter meeting", "locked"),
            ])
            guidance_box(
                "How to complete this",
                "Rate yourself on each strand below. Your <strong>initial ratings from Sep 2025</strong> "
                "are visible in the sidebar on the right for reference. Complete all 54 strands, "
                "then click Submit — your appraiser cannot see this until you submit."
            )
        else:
            step_track([
                ("Initial self-assessment\nIn progress", "active"),
                ("Final self-assessment\nApr 2026", "locked"),
                ("Final evaluation\nAfter final", "locked"),
                ("Sign-off\nAfter meeting", "locked"),
            ])
            guidance_box(
                "How to complete this",
                "Rate yourself honestly on each strand. Open each domain below. "
                "Use the descriptors to understand what each rating means. "
                "You can save a draft and return — submit only when all 54 strands are rated."
            )

        # ── Sidebar: initial reference panel ──
        if CURRENT_ASSESSMENT_CYCLE == "Final" and latest_initial is not None and not latest_initial.empty:
            initial_record_ref = latest_initial.iloc[0].to_dict()
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 📘 Initial Reference — Sep 2025")
                short_map = {
                    "Highly Effective": "HE", "Effective": "E",
                    "Improvement Necessary": "IN", "Does Not Meet Standards": "DNMS"
                }
                colour_map = {"HE": "🟩", "E": "🟦", "IN": "🟨", "DNMS": "🟥"}
                for domain, items in DOMAINS.items():
                    with st.expander(domain, expanded=False):
                        for code, label in items:
                            strand = f"{code} {label}"
                            value = initial_record_ref.get(strand, "")
                            short_value = short_map.get(value, value)
                            colour = colour_map.get(short_value, "⬜")
                            st.markdown(f"{colour} **{code}** — {short_value}")
                        # Show initial reflection if it exists
                        refl_key = f"{domain} Reflection"
                        refl_text = safe_text(initial_record_ref.get(refl_key, ""))
                        if refl_text:
                            st.caption(f"📝 Reflection: {refl_text[:120]}{'...' if len(refl_text) > 120 else ''}")

        # ── Show initial table if Final cycle ──
        if CURRENT_ASSESSMENT_CYCLE == "Final" and latest_initial is not None and not latest_initial.empty:
            st.markdown("### Your Initial Self-Assessment — Sep 2025")
            initial_display = latest_initial.copy().replace({
                "Highly Effective": "HE", "Effective": "E",
                "Improvement Necessary": "IN", "Does Not Meet Standards": "DNMS"
            })
            st.dataframe(
                initial_display.style.map(highlight_ratings, subset=initial_display.columns[5:]),
                use_container_width=True
            )
            st.divider()
            st.markdown("### Final Self-Assessment — Apr 2026")
            st.caption(
                "Complete your final self-assessment independently. "
                "Use your initial ratings in the sidebar as a reference only."
            )

        # ── Main form ──
        selections = {}
        reflections = {}
        initial_record_data = (
            latest_initial.iloc[0].to_dict()
            if latest_initial is not None and not latest_initial.empty
            else {}
        )

        for domain, items in DOMAINS.items():
            with st.expander(domain, expanded=False):
                for code, label in items:
                    strand_key = f"{code} {label}"
                    key = f"{code}-{label}"
                    saved_value = draft_data.get(strand_key, "")

                    # Show initial rating as context
                    if CURRENT_ASSESSMENT_CYCLE == "Final" and initial_record_data:
                        init_val = safe_text(initial_record_data.get(strand_key, ""))
                        if init_val:
                            st.caption(f"📌 Initial (Sep 2025): **{rating_short(init_val)}** — {init_val}")

                    selections[strand_key] = st.radio(
                        f"{strand_key}",
                        RATINGS,
                        index=RATINGS.index(saved_value) if saved_value in RATINGS else None,
                        key=key,
                    ) or ""

                    # Strand descriptors
                    if strand_key in DESCRIPTORS:
                        expand_default = saved_value == ""
                        with st.expander("📖 See descriptors for this strand", expanded=expand_default):
                            st.markdown(f"""
**Highly Effective (HE):** {DESCRIPTORS[strand_key]['HE']}

**Effective (E):** {DESCRIPTORS[strand_key]['E']}

**Improvement Necessary (IN):** {DESCRIPTORS[strand_key]['IN']}

**Does Not Meet Standards (DNMS):** {DESCRIPTORS[strand_key]['DNMS']}
                            """)

                # Domain reflection box
                if ENABLE_REFLECTIONS:
                    saved_refl = draft_data.get(f"Reflection-{domain}", "")

                    # Show initial reflection as context in Final cycle
                    if CURRENT_ASSESSMENT_CYCLE == "Final":
                        init_refl = safe_text(initial_record_data.get(f"{domain} Reflection", ""))
                        if init_refl:
                            show_reflection("Your initial reflection (Sep 2025)", init_refl)

                    reflections[domain] = st.text_area(
                        f"{domain} Reflection (optional)",
                        key=f"refl-{domain}",
                        placeholder="Notes / evidence / next steps (optional)",
                        value=saved_refl,
                    )

        # Submit / Save Draft
        selected_count = sum(1 for v in selections.values() if v)
        remaining = total_items - selected_count

        col1, col2 = st.columns([1, 3])
        with col1:
            submit = st.button(
                "✅ Submit",
                disabled=(selected_count < total_items) or st.session_state.get("submitted", False)
            )

        with st.sidebar:
            if st.button("💾 Save Draft", use_container_width=True):
                draft_payload = {}
                for domain, items in DOMAINS.items():
                    for code, label in items:
                        draft_payload[f"{code} {label}"] = selections[f"{code} {label}"]
                    if ENABLE_REFLECTIONS:
                        draft_payload[f"Reflection-{domain}"] = reflections.get(domain, "")
                save_draft(st.session_state.auth_email, draft_payload)
                st.success("✅ Draft saved!")

            st.markdown(
                """<br><a href="https://drive.google.com/file/d/1GrDAkk8zev6pr4AmmKA6YyTzeUdZ8dZC/view?usp=sharing"
                   target="_blank" style="text-decoration:none;font-weight:bold;color:#1a73e8;">
                   📄 View Teacher Growth Rubric</a>""",
                unsafe_allow_html=True
            )

        if remaining > 0:
            st.markdown(
                f'<p class="locked-msg">Submit unlocks when all {total_items} strands are rated — {remaining} remaining.</p>',
                unsafe_allow_html=True
            )

        if submit:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [
                now_str, st.session_state.auth_email, st.session_state.auth_name,
                appraiser, CURRENT_ASSESSMENT_CYCLE,
            ]
            for domain, items in DOMAINS.items():
                for code, label in items:
                    row.append(selections[f"{code} {label}"])
                if ENABLE_REFLECTIONS:
                    row.append(reflections.get(domain, ""))
            row.append(now_str)
            try:
                with_backoff(RESP_WS.append_row, row, value_input_option="USER_ENTERED")
                load_responses_df.clear()
                st.session_state.submitted = True
                st.success("🎉 Submitted! See **My Submission** to review your responses.")
            except Exception as e:
                st.error("⚠️ Could not submit right now. Please try again shortly.")
                st.caption(f"Debug info: {e}")

# =========================
# Page: My Submission
# =========================
if tab == "My Submission":
    st.subheader("My Submission")

    latest_initial, latest_final, comparison_df = build_teacher_initial_final(
        st.session_state.auth_email
    )

    if latest_initial is None and latest_final is None:
        st.info("No submission found yet.")
    else:
        step_track([
            ("Initial\nSep 2025", "done" if latest_initial is not None else "locked"),
            ("Final self-assessment\nApr 2026", "done" if latest_final is not None else ("active" if latest_initial is not None else "locked")),
            ("Final evaluation", "done" if teacher_final_eval_completed(st.session_state.auth_email) else "locked"),
            ("Sign-off", "done" if teacher_signed_off_final_eval(st.session_state.auth_email) else "locked"),
        ])

        top_cols = st.columns(2)
        with top_cols[0]:
            st.markdown("### Initial Self-Assessment — Sep 2025")
            if latest_initial is not None and not latest_initial.empty:
                st.dataframe(
                    latest_initial.style.map(highlight_ratings, subset=latest_initial.columns[5:]),
                    use_container_width=True
                )
            else:
                st.info("No initial submission available.")

        with top_cols[1]:
            if latest_final is not None and not latest_final.empty:
                st.markdown("### Final Self-Assessment — Apr 2026")
                final_display = latest_final.copy().replace({
                    "Highly Effective": "HE", "Effective": "E",
                    "Improvement Necessary": "IN", "Does Not Meet Standards": "DNMS"
                })
                st.dataframe(
                    final_display.style.map(highlight_ratings, subset=final_display.columns[5:]),
                    use_container_width=True
                )
            else:
                st.info("No Final submission yet.")

        st.divider()
        st.markdown("### Initial vs Final Comparison")

        if not comparison_df.empty:
            initial_rec = latest_initial.iloc[0].to_dict() if latest_initial is not None and not latest_initial.empty else None
            final_rec = latest_final.iloc[0].to_dict() if latest_final is not None and not latest_final.empty else None
            comparison_display = comparison_df[["Domain", "Strand", "Explanation", "Initial", "Final", "Trend"]].copy()
            render_grouped_comparison(
                comparison_display,
                key_prefix="teacher_cmp",
                initial_record=initial_rec,
                final_record=final_rec
            )

# =========================
# Page: Final Evaluation (Teacher)
# =========================
if tab == "Final Evaluation" and role == "user":
    st.subheader("Final Evaluation")
    teacher_email = st.session_state.auth_email.strip().lower()
    teacher_name = st.session_state.auth_name

    me = users_df[users_df["Email"] == teacher_email].iloc[0] if not users_df.empty else {}
    appraiser_raw = me.get("Appraiser", "Not Assigned") if isinstance(me, pd.Series) else "Not Assigned"
    appraiser = get_full_appraiser_name(appraiser_raw)

    # ── Guard: must have submitted Final self-assessment ──
    if not teacher_can_start_final_evaluation(teacher_email):
        step_track([
            ("Initial ✓", "done"),
            ("Final self-assessment\nRequired first", "active"),
            ("Final evaluation\nLocked", "locked"),
            ("Sign-off", "locked"),
        ])
        st.warning(
            "⏳ **Final Evaluation is locked.** "
            "You must first submit your **Final Self-Assessment** before this section becomes available."
        )
        st.stop()

    record = get_teacher_final_eval_record(teacher_email)
    teacher_locked = (
        not is_before_deadline(FINAL_EVAL_TEACHER_DEADLINE)
        or teacher_final_eval_completed(teacher_email)
    )

    # Step track state
    t_submitted = teacher_final_eval_completed(teacher_email)
    a_completed = appraiser_final_eval_completed(teacher_email)
    ev_signed = evaluator_signed_off(teacher_email)
    t_signed = teacher_signed_off_final_eval(teacher_email)

    step_track([
        ("Initial & Final\nself-assessment ✓", "done"),
        ("Your section", "done" if t_submitted else "active"),
        ("Appraiser review", "done" if a_completed else ("active" if t_submitted else "locked")),
        ("Sign-off\nAfter meeting", "done" if t_signed else ("active" if ev_signed else "locked")),
    ])

    st.info(f"**Appraiser:** {appraiser}")
    st.caption(f"Your deadline (IST): {FINAL_EVAL_TEACHER_DEADLINE.strftime('%d %b %Y, %I:%M %p')}")

    # ── Teacher's own section ──
    subject_existing = safe_text(record.get("Subject Area", ""))
    survey_existing = safe_text(record.get("Student Survey Feedback", ""))
    reflection_existing = safe_text(record.get("Overall Reflection", ""))
    subject_index = SUBJECT_AREA_OPTIONS.index(subject_existing) if subject_existing in SUBJECT_AREA_OPTIONS else 0

    with st.expander("📝 Your section — reflection & feedback", expanded=not t_submitted):
        if t_submitted:
            st.success("✅ Your section has been submitted.")

        subject_area = st.selectbox(
            "Subject Area", SUBJECT_AREA_OPTIONS, index=subject_index,
            disabled=teacher_locked, key="fe_subject_area"
        )
        student_survey_feedback = st.text_area(
            "Student Survey Feedback (150 words or less)",
            value=survey_existing, height=150, disabled=teacher_locked, key="fe_student_survey"
        )
        survey_wc = count_words(student_survey_feedback)
        st.caption(f"Word count: {survey_wc}/{FINAL_EVAL_MAX_WORDS_SURVEY}")

        overall_reflection = st.text_area(
            "Overall Reflection on the school year (150 words or less)",
            value=reflection_existing, height=150, disabled=teacher_locked, key="fe_overall_reflection"
        )
        reflection_wc = count_words(overall_reflection)
        st.caption(f"Word count: {reflection_wc}/{FINAL_EVAL_MAX_WORDS_REFLECTION}")

        too_many_words = (
            survey_wc > FINAL_EVAL_MAX_WORDS_SURVEY
            or reflection_wc > FINAL_EVAL_MAX_WORDS_REFLECTION
        )
        if too_many_words:
            st.warning("Buttons are disabled until both sections are within the word limit.")

        col1, col2 = st.columns(2)

        def _build_teacher_record(submitted_flag=False):
            now_str = now_ist_str()
            return {
                "Timestamp": safe_text(record.get("Timestamp", now_str)) or now_str,
                "Last Edited On": now_str,
                "Teacher Email": teacher_email,
                "Teacher Name": teacher_name,
                "Appraiser": appraiser,
                "Subject Area": subject_area,
                "Student Survey Feedback": student_survey_feedback,
                "Overall Reflection": overall_reflection,
                "Teacher Submitted": "Yes" if submitted_flag else safe_text(record.get("Teacher Submitted", "")),
                "Teacher Submitted On": now_str if submitted_flag else safe_text(record.get("Teacher Submitted On", "")),
                "Appraiser Started": safe_text(record.get("Appraiser Started", "")),
                "Appraiser Completed": safe_text(record.get("Appraiser Completed", "")),
                "Appraiser Completed On": safe_text(record.get("Appraiser Completed On", "")),
                "A Rating": safe_text(record.get("A Rating", "")),
                "B Rating": safe_text(record.get("B Rating", "")),
                "C Rating": safe_text(record.get("C Rating", "")),
                "D Rating": safe_text(record.get("D Rating", "")),
                "E Rating": safe_text(record.get("E Rating", "")),
                "F Rating": safe_text(record.get("F Rating", "")),
                "Overall Rating": safe_text(record.get("Overall Rating", "")),
                "Overall Comments": safe_text(record.get("Overall Comments", "")),
                "Evaluator Sign Off": safe_text(record.get("Evaluator Sign Off", "")),
                "Evaluator Sign Off Date": safe_text(record.get("Evaluator Sign Off Date", "")),
                "Teacher Sign Off": safe_text(record.get("Teacher Sign Off", "")),
                "Teacher Sign Off Date": safe_text(record.get("Teacher Sign Off Date", "")),
            }

        with col1:
            if st.button("💾 Save", disabled=teacher_locked or too_many_words):
                save_final_eval_record(_build_teacher_record(submitted_flag=False))
                st.success("Saved.")
                _rerun()

        with col2:
            if st.button("✅ Submit to appraiser", disabled=teacher_locked or too_many_words):
                save_final_eval_record(_build_teacher_record(submitted_flag=True))
                st.success("Submitted. Your appraiser can now complete their section.")
                _rerun()

    # ── Appraiser Review ──
    st.divider()
    st.markdown("### Appraiser Review")

    refreshed = get_teacher_final_eval_record(teacher_email)

    if not t_submitted:
        st.info("Submit your section above first — the appraiser review will appear here once you submit.")

    elif not a_completed:
        st.info(f"Your section has been submitted. {appraiser} will complete their section shortly.")

    elif a_completed and not ev_signed:
        # Appraiser completed but hasn't signed off yet — show ratings to teacher
        st.info(
            f"**{appraiser}** has completed your evaluation. "
            "You will be able to view the full details after your in-person meeting and appraiser sign-off."
        )

    elif ev_signed:
        # Appraiser has signed off — teacher can now see the full review
        render_final_evaluation_review_panel(refreshed, heading=f"Review by {appraiser}")

        if ev_signed:
            st.success(f"✅ **{appraiser}** signed off on {fmt_ist(refreshed.get('Evaluator Sign Off Date', ''))}")

        if not t_signed:
            st.info(
                "The evaluation has been discussed and signed off by your appraiser. "
                "Please sign off below after the meeting."
            )
            st.caption(
                "Your signature indicates that you have seen and discussed the evaluation; "
                "it does not necessarily denote agreement with the report."
            )
            if st.button(f"✍️ {teacher_name} — Sign Off"):
                now_str = now_ist_str()
                refreshed["Last Edited On"] = now_str
                refreshed["Teacher Sign Off"] = "Yes"
                refreshed["Teacher Sign Off Date"] = now_str
                save_final_eval_record(refreshed)
                st.success("Sign-off completed.")
                _rerun()

        if t_signed:
            st.success(f"✅ **{teacher_name}** signed off on {fmt_ist(refreshed.get('Teacher Sign Off Date', ''))}")
            st.caption(
                "The teacher's signature indicates that he or she has seen and discussed the evaluation; "
                "it does not necessarily denote agreement with the report."
            )

# =========================
# Page: Admin Panel
# =========================
if tab == "Admin" and i_am_admin:
    st.header("👩‍💼 Admin Panel")

    me = users_df[users_df["Email"] == st.session_state.auth_email].iloc[0]
    my_name = me.get("Name", st.session_state.auth_email)
    my_role = me.get("Role", "").strip().lower()
    my_first = my_name.split()[0].strip().lower()

    has_campus_col = "Campus" in users_df.columns
    my_campus = str(me.get("Campus", "")).strip() if has_campus_col else ""
    campus_series = (
        users_df["Campus"].astype(str).str.strip()
        if has_campus_col and my_campus else None
    )

    if my_role == "sadmin":
        if campus_series is not None:
            mask = (users_df["Role"] == "user") & (campus_series == my_campus)
            assigned = users_df[mask]
            st.info(f"Super Admin access: viewing **all teachers** in the **{my_campus}** campus.")
        else:
            assigned = users_df[users_df["Role"] == "user"]
    else:
        def matches_appraiser(cell):
            if pd.isna(cell):
                return False
            appraisers = [a.strip().lower() for a in str(cell).split(",")]
            return my_first in appraisers

        if not users_df.empty:
            base_mask = users_df["Appraiser"].apply(matches_appraiser)
            if campus_series is not None:
                base_mask = base_mask & (campus_series == my_campus)
            assigned = users_df[base_mask]
        else:
            assigned = pd.DataFrame()

    resp_df = load_responses_df()

    if assigned.empty:
        st.info("No teachers found for your role in the Users sheet.")
    else:
        # ── Summary ──
        if admin_view_mode == "Summary of Teachers":
            st.subheader("📋 Summary of Teachers")
            summary_rows = []
            initial_submitted_count = 0
            final_submitted_count = 0
            total_count = len(assigned)

            for _, teacher in assigned.iterrows():
                t_email = teacher["Email"].strip().lower()
                t_name = teacher["Name"]
                submissions = resp_df[resp_df["Email"] == t_email] if not resp_df.empty else pd.DataFrame()
                if not submissions.empty:
                    if "Assessment Cycle" not in submissions.columns:
                        submissions = submissions.copy()
                        submissions["Assessment Cycle"] = "Initial"
                    else:
                        submissions = submissions.copy()
                        submissions["Assessment Cycle"] = submissions["Assessment Cycle"].replace("", "Initial")

                initial_subs = submissions[submissions["Assessment Cycle"] == "Initial"] if not submissions.empty else pd.DataFrame()
                final_subs = submissions[submissions["Assessment Cycle"] == "Final"] if not submissions.empty else pd.DataFrame()
                initial_status = "✅ Submitted" if not initial_subs.empty else "❌ Not Submitted"
                final_status = "✅ Submitted" if not final_subs.empty else "❌ Not Submitted"
                last_initial_date = initial_subs["Timestamp"].max() if not initial_subs.empty else "-"
                last_final_date = final_subs["Timestamp"].max() if not final_subs.empty else "-"
                if not initial_subs.empty:
                    initial_submitted_count += 1
                if not final_subs.empty:
                    final_submitted_count += 1

                summary_rows.append({
                    "Teacher": t_name, "Email": t_email,
                    "Initial Status": initial_status, "Final Status": final_status,
                    "Teacher Final Eval": "✅ Submitted" if teacher_final_eval_completed(t_email) else "❌ Pending",
                    "Appraiser Final Eval": "✅ Completed" if appraiser_final_eval_completed(t_email) else "❌ Pending",
                    "Last Initial": last_initial_date, "Last Final": last_final_date,
                })

            summary_df = pd.DataFrame(summary_rows)
            st.markdown(
                f"**Initial:** {initial_submitted_count}/{total_count} submitted "
                f"({round((initial_submitted_count/total_count)*100, 1) if total_count else 0}%)"
            )
            st.progress(initial_submitted_count / total_count if total_count else 0)
            st.markdown(
                f"**Final:** {final_submitted_count}/{total_count} submitted "
                f"({round((final_submitted_count/total_count)*100, 1) if total_count else 0}%)"
            )
            st.progress(final_submitted_count / total_count if total_count else 0)
            st.dataframe(summary_df, use_container_width=True)

        # ── Grid ──
        if admin_view_mode == "Self-Assessment Grid":
            st.subheader("📊 Submissions Grid (My Appraisees)")
            if not resp_df.empty:
                appraisee_emails = assigned["Email"].str.strip().str.lower().tolist()
                df = resp_df[resp_df["Email"].str.strip().str.lower().isin(appraisee_emails)]
                if not df.empty:
                    mapping = {
                        "Highly Effective": "HE", "Effective": "E",
                        "Improvement Necessary": "IN", "Does Not Meet Standards": "DNMS"
                    }
                    df = df.replace(mapping)
                    styled_df = df.style.map(highlight_ratings, subset=df.columns[4:])
                    st.dataframe(styled_df, use_container_width=True)
                    st.download_button(
                        "📥 Download Grid (CSV)",
                        data=df.to_csv(index=False).encode("utf-8"),
                        file_name=f"{st.session_state.auth_name}_appraisees_grid.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No rubric submissions yet from your appraisees.")

        # ── Individual view ──
        if admin_view_mode == "View Teacher Self-Assessment":
            st.subheader("🔎 View Individual Submissions")
            teacher_choice = st.selectbox("Select a teacher", assigned["Name"].tolist())

            if teacher_choice:
                teacher_email = assigned.loc[assigned["Name"] == teacher_choice, "Email"].iloc[0]
                rows = resp_df[resp_df["Email"] == teacher_email] if not resp_df.empty else pd.DataFrame()

                latest_initial, latest_final, comparison_df = build_initial_final_comparison(rows)

                col1, col2 = st.columns(2)
                with col1:
                    if latest_initial is not None and not latest_initial.empty:
                        st.info(f"Initial submitted: {safe_text(latest_initial.iloc[0].get('Timestamp', ''))}")
                    else:
                        st.warning("No Initial submission found.")
                with col2:
                    if latest_final is not None and not latest_final.empty:
                        st.info(f"Final submitted: {safe_text(latest_final.iloc[0].get('Timestamp', ''))}")
                    else:
                        st.warning("No Final submission found.")

                # ── Comparison with reflections ──
                st.subheader(f"Initial vs Final Comparison — {teacher_choice}")
                if not comparison_df.empty:
                    display_df = comparison_df[["Domain", "Strand", "Explanation", "Initial", "Final", "Trend"]].copy()
                    initial_rec = latest_initial.iloc[0].to_dict() if latest_initial is not None and not latest_initial.empty else None
                    final_rec = latest_final.iloc[0].to_dict() if latest_final is not None and not latest_final.empty else None
                    render_grouped_comparison(
                        display_df,
                        key_prefix=f"admin_cmp_{teacher_email}",
                        initial_record=initial_rec,
                        final_record=final_rec
                    )

                    appraiser_name = safe_text(
                        rows.sort_values("Timestamp", ascending=False).head(1).iloc[0].get("Appraiser", "")
                    )
                    printable_html = build_printable_comparison_html(
                        teacher_name=teacher_choice, teacher_email=teacher_email,
                        appraiser=appraiser_name, latest_initial=latest_initial,
                        latest_final=latest_final, display_df=display_df
                    )

                st.divider()

                if rows.empty:
                    st.warning(f"No submission found for {teacher_choice}.")
                else:
                    st.subheader("Final Evaluation")
                    fe_record = get_teacher_final_eval_record(teacher_email)

                    # ── Guard: teacher must have submitted Final Eval first ──
                    if not teacher_final_eval_completed(teacher_email):
                        st.info(
                            f"⏳ **{teacher_choice}** has not yet submitted their Final Evaluation section. "
                            "The appraiser section will become available once they submit."
                        )
                    else:
                        st.success(f"✅ {teacher_choice} has submitted their section.")
                        st.write(f"**Subject Area:** {safe_text(fe_record.get('Subject Area', ''))}")
                        st.write("**Student Survey Feedback:**")
                        st.info(safe_text(fe_record.get("Student Survey Feedback", "")))
                        st.write("**Overall Reflection:**")
                        st.info(safe_text(fe_record.get("Overall Reflection", "")))

                        if teacher_signed_off_final_eval(teacher_email):
                            st.divider()
                            render_final_evaluation_review_panel(fe_record, heading="Final Signed-Off Review")
                            if evaluator_signed_off(teacher_email):
                                ev_name = title_case_name(fe_record.get("Appraiser", my_name))
                                st.success(f"✅ **{ev_name}** signed off on {fmt_ist(fe_record.get('Evaluator Sign Off Date', ''))}")
                            if teacher_signed_off_final_eval(teacher_email):
                                st.success(f"✅ **{teacher_choice}** signed off on {fmt_ist(fe_record.get('Teacher Sign Off Date', ''))}")

                            final_doc_record = fe_record.copy()
                            final_doc_record["Teacher Name"] = teacher_choice
                            final_doc_record["Appraiser"] = title_case_name(fe_record.get("Appraiser", my_name))
                            final_docx = generate_final_evaluation_docx(final_doc_record)
                            st.download_button(
                                "📄 Download Final Evaluation Summary (DOCX)",
                                data=final_docx,
                                file_name=f"{teacher_choice}_final_evaluation_summary.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"{teacher_email}_final_eval_docx"
                            )

                        else:
                            # Appraiser section
                            appraiser_locked = (
                                not is_before_deadline(FINAL_EVAL_APPRAISER_DEADLINE)
                                or teacher_signed_off_final_eval(teacher_email)
                            )
                            st.caption(f"Your deadline (IST): {FINAL_EVAL_APPRAISER_DEADLINE.strftime('%d %b %Y, %I:%M %p')}")

                            st.markdown("#### Your Domain Ratings")
                            domain_values = {}
                            cols_ab = st.columns(2)
                            for idx, (rating_col, label) in enumerate(final_eval_domain_rows()):
                                existing = safe_text(fe_record.get(rating_col, ""))
                                default_index = FINAL_EVAL_RATINGS.index(existing) if existing in FINAL_EVAL_RATINGS else 0
                                with cols_ab[idx % 2]:
                                    domain_values[rating_col] = st.selectbox(
                                        label, FINAL_EVAL_RATINGS, index=default_index,
                                        disabled=appraiser_locked,
                                        key=f"{teacher_email}_{rating_col}"
                                    )

                            existing_overall = safe_text(fe_record.get("Overall Rating", ""))
                            default_overall_index = FINAL_EVAL_RATINGS.index(existing_overall) if existing_overall in FINAL_EVAL_RATINGS else 0
                            overall_rating = st.selectbox(
                                "Overall Rating", FINAL_EVAL_RATINGS, index=default_overall_index,
                                disabled=appraiser_locked, key=f"{teacher_email}_overall_rating"
                            )

                            st.markdown("#### Overall Comments")
                            overall_comments = st.text_area(
                                "Overall Comments (150 words or less)",
                                value=safe_text(fe_record.get("Overall Comments", "")),
                                height=150, disabled=appraiser_locked,
                                key=f"{teacher_email}_overall_comments"
                            )
                            comments_wc = count_words(overall_comments)
                            st.caption(f"Word count: {comments_wc}/{FINAL_EVAL_MAX_WORDS_COMMENTS}")

                            col_a, col_b = st.columns(2)

                            def _build_appraiser_record(completed=False):
                                now_str = now_ist_str()
                                updated = fe_record.copy()
                                updated["Last Edited On"] = now_str
                                updated["Appraiser Started"] = "Yes"
                                if completed:
                                    updated["Appraiser Completed"] = "Yes"
                                    updated["Appraiser Completed On"] = now_str
                                for k, v in domain_values.items():
                                    updated[k] = v
                                updated["Overall Rating"] = overall_rating
                                updated["Overall Comments"] = overall_comments
                                return updated

                            with col_a:
                                if st.button(
                                    "💾 Save",
                                    disabled=appraiser_locked or comments_wc > FINAL_EVAL_MAX_WORDS_COMMENTS,
                                    key=f"{teacher_email}_save_appraiser_eval"
                                ):
                                    save_final_eval_record(_build_appraiser_record(completed=False))
                                    st.success("Saved.")
                                    _rerun()

                            with col_b:
                                if st.button(
                                    "✅ Submit Appraiser Section",
                                    disabled=appraiser_locked or comments_wc > FINAL_EVAL_MAX_WORDS_COMMENTS,
                                    key=f"{teacher_email}_submit_appraiser_eval"
                                ):
                                    save_final_eval_record(_build_appraiser_record(completed=True))
                                    st.success("Appraiser section submitted.")
                                    _rerun()

                            refreshed_fe = get_teacher_final_eval_record(teacher_email)

                            if (appraiser_final_eval_completed(teacher_email)
                                    and not evaluator_signed_off(teacher_email)
                                    and not appraiser_locked):
                                st.info(
                                    "⚠️ Only click **Appraiser Sign Off** after the evaluation has been "
                                    "discussed with the teacher in the meeting. Once signed off, "
                                    "the evaluation becomes visible to the teacher."
                                )
                                if st.button(f"✍️ {my_name} — Sign Off", key=f"{teacher_email}_evaluator_signoff"):
                                    now_str = now_ist_str()
                                    refreshed_fe["Last Edited On"] = now_str
                                    refreshed_fe["Evaluator Sign Off"] = "Yes"
                                    refreshed_fe["Evaluator Sign Off Date"] = now_str
                                    save_final_eval_record(refreshed_fe)
                                    st.success("Sign-off completed.")
                                    _rerun()

                            if evaluator_signed_off(teacher_email):
                                st.success(f"✅ **{my_name}** signed off on {fmt_ist(refreshed_fe.get('Evaluator Sign Off Date', ''))}")

# =========================
# Page: Super Admin Panel
# =========================
if tab == "Super Admin" and i_am_sadmin:
    st.header("🏫 Super Admin Panel")

    my_campus = str(st.session_state.get("auth_campus", "") or "").strip()
    has_campus_col = "Campus" in users_df.columns
    campus_series = (
        users_df["Campus"].astype(str).str.strip()
        if has_campus_col and my_campus else None
    )

    if campus_series is not None:
        assigned = users_df[(users_df["Role"] == "user") & (campus_series == my_campus)]
        st.info(f"Viewing **all teachers** in the **{my_campus}** campus.")
    else:
        assigned = users_df[users_df["Role"] == "user"]
        st.info("Viewing **all teachers** in the school.")

    resp_df = load_responses_df()

    if assigned.empty:
        st.info("No teachers found for this campus.")
    else:
        summary_rows = []
        initial_submitted_count = 0
        final_submitted_count = 0
        total_count = len(assigned)

        for _, teacher in assigned.iterrows():
            t_email = teacher["Email"].strip().lower()
            t_name = teacher["Name"]
            submissions = resp_df[resp_df["Email"] == t_email] if not resp_df.empty else pd.DataFrame()
            if not submissions.empty:
                if "Assessment Cycle" not in submissions.columns:
                    submissions = submissions.copy()
                    submissions["Assessment Cycle"] = "Initial"
                else:
                    submissions = submissions.copy()
                    submissions["Assessment Cycle"] = submissions["Assessment Cycle"].replace("", "Initial")

            initial_subs = submissions[submissions["Assessment Cycle"] == "Initial"] if not submissions.empty else pd.DataFrame()
            final_subs = submissions[submissions["Assessment Cycle"] == "Final"] if not submissions.empty else pd.DataFrame()
            initial_status = "✅ Submitted" if not initial_subs.empty else "❌ Not Submitted"
            final_status = "✅ Submitted" if not final_subs.empty else "❌ Not Submitted"
            last_initial_date = initial_subs["Timestamp"].max() if not initial_subs.empty else "-"
            last_final_date = final_subs["Timestamp"].max() if not final_subs.empty else "-"
            if not initial_subs.empty:
                initial_submitted_count += 1
            if not final_subs.empty:
                final_submitted_count += 1

            summary_rows.append({
                "Teacher": t_name, "Email": t_email,
                "Initial Status": initial_status, "Final Status": final_status,
                "Teacher Final Eval": "✅ Submitted" if teacher_final_eval_completed(t_email) else "❌ Pending",
                "Appraiser Final Eval": "✅ Completed" if appraiser_final_eval_completed(t_email) else "❌ Pending",
                "Last Initial": last_initial_date, "Last Final": last_final_date,
            })

        summary_df = pd.DataFrame(summary_rows)

        if sadmin_view_mode == "Summary of Teachers":
            st.subheader("📋 Summary of Teachers")
            st.markdown(
                f"**Initial:** {initial_submitted_count}/{total_count} submitted "
                f"({round((initial_submitted_count/total_count)*100, 1) if total_count else 0}%)"
            )
            st.progress(initial_submitted_count / total_count if total_count else 0)
            st.markdown(
                f"**Final:** {final_submitted_count}/{total_count} submitted "
                f"({round((final_submitted_count/total_count)*100, 1) if total_count else 0}%)"
            )
            st.progress(final_submitted_count / total_count if total_count else 0)
            st.dataframe(summary_df, use_container_width=True)

        if sadmin_view_mode == "Self-Assessment Grid":
            st.subheader("📊 Submissions Grid (Campus)")
            if not resp_df.empty:
                teacher_emails = assigned["Email"].str.strip().str.lower().tolist()
                df = resp_df[resp_df["Email"].str.strip().str.lower().isin(teacher_emails)]
                if not df.empty:
                    mapping = {
                        "Highly Effective": "HE", "Effective": "E",
                        "Improvement Necessary": "IN", "Does Not Meet Standards": "DNMS"
                    }
                    df = df.replace(mapping)
                    styled_df = df.style.map(highlight_ratings, subset=df.columns[4:])
                    st.dataframe(styled_df, use_container_width=True)
                    st.download_button(
                        "📥 Download Campus Grid (CSV)",
                        data=df.to_csv(index=False).encode("utf-8"),
                        file_name=f"{my_campus or 'campus'}_submissions_grid.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No rubric submissions yet for this campus.")

        if sadmin_view_mode == "View Teacher Self-Assessment":
            st.subheader("🔎 View Individual Submissions")
            teacher_choice = st.selectbox(
                "Select a teacher", assigned["Name"].tolist(), key="sadmin_teacher_choice"
            )

            if teacher_choice:
                teacher_email = assigned.loc[assigned["Name"] == teacher_choice, "Email"].iloc[0]
                rows = resp_df[resp_df["Email"] == teacher_email] if not resp_df.empty else pd.DataFrame()
                latest_initial, latest_final, comparison_df = build_initial_final_comparison(rows)

                st.subheader(f"Initial vs Final Comparison — {teacher_choice}")
                col1, col2 = st.columns(2)
                with col1:
                    if latest_initial is not None and not latest_initial.empty:
                        st.info(f"Initial submitted: {safe_text(latest_initial.iloc[0].get('Timestamp', ''))}")
                    else:
                        st.warning("No Initial submission found.")
                with col2:
                    if latest_final is not None and not latest_final.empty:
                        st.info(f"Final submitted: {safe_text(latest_final.iloc[0].get('Timestamp', ''))}")
                    else:
                        st.warning("No Final submission found.")

                if not comparison_df.empty:
                    display_df = comparison_df[["Domain", "Strand", "Explanation", "Initial", "Final", "Trend"]].copy()
                    initial_rec = latest_initial.iloc[0].to_dict() if latest_initial is not None and not latest_initial.empty else None
                    final_rec = latest_final.iloc[0].to_dict() if latest_final is not None and not latest_final.empty else None
                    render_grouped_comparison(
                        display_df,
                        key_prefix=f"sadmin_cmp_{teacher_email}",
                        initial_record=initial_rec,
                        final_record=final_rec
                    )

                st.divider()

                if rows.empty:
                    st.warning(f"No submission found for {teacher_choice}.")
                else:
                    st.subheader("Final Evaluation")
                    fe_record = get_teacher_final_eval_record(teacher_email)
                    sadmin_name = st.session_state.auth_name

                    if not teacher_final_eval_completed(teacher_email):
                        st.info(
                            f"⏳ **{teacher_choice}** has not yet submitted their Final Evaluation section."
                        )
                    else:
                        st.success(f"✅ {teacher_choice} has submitted their section.")
                        st.write(f"**Subject Area:** {safe_text(fe_record.get('Subject Area', ''))}")
                        st.write("**Student Survey Feedback:**")
                        st.info(safe_text(fe_record.get("Student Survey Feedback", "")))
                        st.write("**Overall Reflection:**")
                        st.info(safe_text(fe_record.get("Overall Reflection", "")))

                        if teacher_signed_off_final_eval(teacher_email):
                            st.divider()
                            render_final_evaluation_review_panel(fe_record, heading="Final Signed-Off Review")
                            if evaluator_signed_off(teacher_email):
                                ev_name = title_case_name(fe_record.get("Appraiser", sadmin_name))
                                st.success(f"✅ **{ev_name}** signed off on {fmt_ist(fe_record.get('Evaluator Sign Off Date', ''))}")
                            if teacher_signed_off_final_eval(teacher_email):
                                st.success(f"✅ **{teacher_choice}** signed off on {fmt_ist(fe_record.get('Teacher Sign Off Date', ''))}")

                            final_doc_record = fe_record.copy()
                            final_doc_record["Teacher Name"] = teacher_choice
                            final_doc_record["Appraiser"] = title_case_name(fe_record.get("Appraiser", sadmin_name))
                            final_docx = generate_final_evaluation_docx(final_doc_record)
                            st.download_button(
                                "📄 Download Final Evaluation Summary (DOCX)",
                                data=final_docx,
                                file_name=f"{teacher_choice}_final_evaluation_summary.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"{teacher_email}_sadmin_final_eval_docx"
                            )

                        else:
                            appraiser_locked = (
                                not is_before_deadline(FINAL_EVAL_APPRAISER_DEADLINE)
                                or teacher_signed_off_final_eval(teacher_email)
                            )
                            st.caption(f"Your deadline (IST): {FINAL_EVAL_APPRAISER_DEADLINE.strftime('%d %b %Y, %I:%M %p')}")

                            st.markdown("#### Your Domain Ratings")
                            domain_values = {}
                            cols_ab = st.columns(2)
                            for idx, (rating_col, label) in enumerate(final_eval_domain_rows()):
                                existing = safe_text(fe_record.get(rating_col, ""))
                                default_index = FINAL_EVAL_RATINGS.index(existing) if existing in FINAL_EVAL_RATINGS else 0
                                with cols_ab[idx % 2]:
                                    domain_values[rating_col] = st.selectbox(
                                        label, FINAL_EVAL_RATINGS, index=default_index,
                                        disabled=appraiser_locked,
                                        key=f"{teacher_email}_sadmin_{rating_col}"
                                    )

                            existing_overall = safe_text(fe_record.get("Overall Rating", ""))
                            default_overall_index = FINAL_EVAL_RATINGS.index(existing_overall) if existing_overall in FINAL_EVAL_RATINGS else 0
                            overall_rating = st.selectbox(
                                "Overall Rating", FINAL_EVAL_RATINGS, index=default_overall_index,
                                disabled=appraiser_locked, key=f"{teacher_email}_sadmin_overall_rating"
                            )

                            st.markdown("#### Overall Comments")
                            overall_comments = st.text_area(
                                "Overall Comments (150 words or less)",
                                value=safe_text(fe_record.get("Overall Comments", "")),
                                height=150, disabled=appraiser_locked,
                                key=f"{teacher_email}_sadmin_overall_comments"
                            )
                            comments_wc = count_words(overall_comments)
                            st.caption(f"Word count: {comments_wc}/{FINAL_EVAL_MAX_WORDS_COMMENTS}")

                            col_a, col_b = st.columns(2)

                            def _build_sadmin_appraiser_record(completed=False):
                                now_str = now_ist_str()
                                updated = fe_record.copy()
                                updated["Last Edited On"] = now_str
                                updated["Appraiser Started"] = "Yes"
                                if completed:
                                    updated["Appraiser Completed"] = "Yes"
                                    updated["Appraiser Completed On"] = now_str
                                for k, v in domain_values.items():
                                    updated[k] = v
                                updated["Overall Rating"] = overall_rating
                                updated["Overall Comments"] = overall_comments
                                return updated

                            with col_a:
                                if st.button(
                                    "💾 Save",
                                    disabled=appraiser_locked or comments_wc > FINAL_EVAL_MAX_WORDS_COMMENTS,
                                    key=f"{teacher_email}_sadmin_save_appraiser_eval"
                                ):
                                    save_final_eval_record(_build_sadmin_appraiser_record(completed=False))
                                    st.success("Saved.")
                                    _rerun()

                            with col_b:
                                if st.button(
                                    "✅ Submit Appraiser Section",
                                    disabled=appraiser_locked or comments_wc > FINAL_EVAL_MAX_WORDS_COMMENTS,
                                    key=f"{teacher_email}_sadmin_submit_appraiser_eval"
                                ):
                                    save_final_eval_record(_build_sadmin_appraiser_record(completed=True))
                                    st.success("Appraiser section submitted.")
                                    _rerun()

                            refreshed_fe = get_teacher_final_eval_record(teacher_email)

                            if (appraiser_final_eval_completed(teacher_email)
                                    and not evaluator_signed_off(teacher_email)
                                    and not appraiser_locked):
                                st.info(
                                    "⚠️ Only click **Sign Off** after the evaluation has been discussed "
                                    "with the teacher. Once signed off, the evaluation becomes visible to them."
                                )
                                if st.button(f"✍️ {sadmin_name} — Sign Off", key=f"{teacher_email}_sadmin_evaluator_signoff"):
                                    now_str = now_ist_str()
                                    refreshed_fe["Last Edited On"] = now_str
                                    refreshed_fe["Evaluator Sign Off"] = "Yes"
                                    refreshed_fe["Evaluator Sign Off Date"] = now_str
                                    save_final_eval_record(refreshed_fe)
                                    st.success("Sign-off completed.")
                                    _rerun()

                            if evaluator_signed_off(teacher_email):
                                st.success(f"✅ **{sadmin_name}** signed off on {fmt_ist(refreshed_fe.get('Evaluator Sign Off Date', ''))}")

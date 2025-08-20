# app.py
import time
from datetime import datetime

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Try to import HttpError; fall back gracefully if googleapiclient isn't present
try:
    from googleapiclient.errors import HttpError  # type: ignore
except Exception:  # pragma: no cover
    class HttpError(Exception):
        pass

# =========================
# UI CONFIG (must be first)
# =========================
st.set_page_config(page_title="OIS Teacher Self‑Assessment", layout="wide")

# =========================
# CONFIG
# =========================
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
ENABLE_REFLECTIONS = True  # set to False if you want to hide reflection boxes

# =========================
# DOMAINS & SUB-STRANDS (exact from rubric)
# =========================
DOMAINS = {
    "A: Planning and Preparation for Learning": [
        ("A1", "Expertise"),
        ("A2", "Goals"),
        ("A3", "Units"),
        ("A4", "Assessments"),
        ("A5", "Anticipation"),
        ("A6", "Lessons"),
        ("A7", "Materials"),
        ("A8", "Differentiation"),
        ("A9", "Environment"),
    ],
    "B: Classroom Management": [
        ("B1", "Expectations"),
        ("B2", "Relationships"),
        ("B3", "Social Emotional"),
        ("B4", "Routines"),
        ("B5", "Responsibility"),
        ("B6", "Repertoire"),
        ("B7", "Prevention"),
        ("B8", "Incentives"),
    ],
    "C: Delivery of Instruction": [
        ("C1", "Expectations"),
        ("C2", "Mindset"),
        ("C3", "Framing"),
        ("C4", "Connections"),
        ("C5", "Clarity"),
        ("C6", "Repertoire"),
        ("C7", "Engagement"),
        ("C8", "Differentiation"),
        ("C9", "Nimbleness"),
    ],
    "D: Monitoring, Assessment, and Follow-Up": [
        ("D1", "Criteria"),
        ("D2", "Diagnosis"),
        ("D3", "Goals"),
        ("D4", "Feedback"),
        ("D5", "Recognition"),
        ("D6", "Analysis"),
        ("D7", "Tenacity"),
        ("D8", "Support"),
        ("D9", "Reflection"),
    ],
    "E: Family and Community Outreach": [
        ("E1", "Respect"),
        ("E2", "Belief"),
        ("E3", "Expectations"),
        ("E4", "Communication"),
        ("E5", "Involving"),
        ("E6", "Responsiveness"),
        ("E7", "Reporting"),
        ("E8", "Outreach"),
        ("E9", "Resources"),
    ],
    "F: Professional Responsibility": [
        ("F1", "Language"),
        ("F2", "Reliability"),
        ("F3", "Professionalism"),
        ("F4", "Judgement"),
        ("F5", "Teamwork"),
        ("F6", "Leadership"),
        ("F7", "Openness"),
        ("F8", "Collaboration"),
        ("F9", "Growth"),
    ],
}

# Rating scale (exact rubric wording)
RATINGS = [
    "Highly Effective",
    "Effective",
    "Improvement Necessary",
    "Does Not Meet Standards",
]

# =========================
# Small retry/backoff for Sheets calls (handles 429/5xx)
# =========================
def with_backoff(fn, *args, **kwargs):
    """Retry gspread/api calls briefly on 429/5xx."""
    max_attempts = 5
    delay = 0.6  # seconds
    last_exc = None
    for _ in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except HttpError as e:  # googleapiclient
            status = getattr(e, "status_code", None)
            if status in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay *= 2
                last_exc = e
                continue
            raise
        except gspread.exceptions.APIError as e:  # gspread-wrapped
            msg = str(e).lower()
            if any(code in msg for code in ["429", "500", "502", "503", "504"]):
                time.sleep(delay)
                delay *= 2
                last_exc = e
                continue
            raise
        except Exception as e:
            # Non-HTTP transient error: try once more with backoff
            time.sleep(delay)
            delay *= 2
            last_exc = e
            continue
    if last_exc:
        raise last_exc
    return fn(*args, **kwargs)

# =========================
# ONE-TIME SHEETS CONNECTION
# =========================
def connect_sheets():
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
    client = gspread.authorize(creds)
    try:
        ss = client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error("⚠️ Could not access Google Sheet. Please confirm the service account has **Editor** access and the Sheet ID is correct.")
        st.caption(f"Debug info: {e}")
        st.stop()
    return ss

SS = connect_sheets()
RESP_WS = SS.worksheet("Responses")
USERS_WS = SS.worksheet("Users")

# =========================
# HEADER MANAGEMENT (safe, non-destructive)
# =========================
def expected_headers():
    headers = ["Timestamp", "Email", "Name", "Appraiser"]
    for domain, items in DOMAINS.items():
        for code, label in items:
            headers.append(f"{code} {label}")
        if ENABLE_REFLECTIONS:
            headers.append(f"{domain} Reflection")
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
            "Submissions will still append, but columns may be misaligned if the rubric changed. "
            "To update safely, export data, fix headers offline, and re-import."
        )
    return True

ensure_headers_once()

# =========================
# USERS: read ONCE per server process (auto‑detect headers)
# =========================
def _pick_col(candidates: list[str], cols: list[str]):
    """Return the first column from 'cols' that matches any of 'candidates' case-insensitively."""
    norm_map = {c.strip().lower(): c for c in cols}
    for want in candidates:
        key = want.strip().lower()
        if key in norm_map:
            return norm_map[key]
    # fallback: partial contains
    for c in cols:
        cl = c.strip().lower()
        if any(w in cl for w in candidates):
            return c
    return None

@st.cache_resource
def load_users_once_df():
    """
    Load Users with header auto-detection (no KeyError if sheet uses different header names or order).
    Looks for columns that map to Email, Name, Appraiser.
    """
    records = with_backoff(USERS_WS.get_all_records)
    if not records:
        return pd.DataFrame(columns=["Email", "Name", "Appraiser"])

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["Email", "Name", "Appraiser"])

    cols = list(df.columns)

    # Try to find header names (case-insensitive, flexible)
    email_header = _pick_col(
        ["email", "school email", "work email", "ois email", "e-mail"],
        cols,
    )
    name_header = _pick_col(
        ["name", "full name", "teacher name", "staff name"],
        cols,
    )
    appraiser_header = _pick_col(
        ["appraiser", "line manager", "manager", "appraiser name", "supervisor"],
        cols,
    )

    # Build standardized frame
    out = pd.DataFrame()
    if email_header:
        out["Email"] = df[email_header].astype(str).str.strip().str.lower()
    else:
        out["Email"] = ""
        st.warning("Users sheet: could not detect an **Email** column. Expected something like 'Email' or 'School Email'.")

    if name_header:
        out["Name"] = df[name_header].astype(str).str.strip()
    else:
        out["Name"] = ""
        st.warning("Users sheet: could not detect a **Name** column. Expected something like 'Name' or 'Teacher Name'.")

    if appraiser_header:
        out["Appraiser"] = df[appraiser_header].astype(str).str.strip().replace({"": "Not Assigned"})
    else:
        out["Appraiser"] = "Not Assigned"
        # Non-blocking; many sheets don't have this initially

    return out

users_df = load_users_once_df()

# =========================
# UI
# =========================
st.title("🌟 OIS Teacher Self‑Assessment 2025‑26")

st.sidebar.header("Teacher Login")
email_input = st.sidebar.text_input("School email (e.g., firstname.lastname@oberoi-is.org)").strip()

# Optional: quick debug of detected headers
with st.sidebar.expander("Debug: Users headers", expanded=False):
    if not users_df.empty:
        st.write(list(users_df.columns))
    else:
        st.write("No users loaded (empty sheet or unreadable).")

user_row = None
if email_input:
    # gentle domain hint (non-blocking)
    if "@" in email_input and not email_input.lower().endswith("@oberoi-is.org"):
        st.sidebar.info("Note: this looks like a non‑OIS address. If that’s intentional, ignore this.")

    email_lc = email_input.lower()
    if not users_df.empty and "Email" in users_df.columns:
        match = users_df[users_df["Email"] == email_lc]
    else:
        match = pd.DataFrame()

    if not match.empty:
        user_row = match.iloc[0]
        appraiser = user_row.get("Appraiser", "Not Assigned")
        st.sidebar.success(f"Welcome **{user_row.get('Name', '')}**")
        st.sidebar.info(f"Your appraiser: **{appraiser}**")
    else:
        st.sidebar.error("Email not found in Users sheet (or Email column not detected).")

if user_row is not None:
    st.header("📋 Self‑Assessment")

    selections: dict[str, str] = {}
    reflections: dict[str, str] = {}
    total_items = sum(len(v) for v in DOMAINS.values())

    # All inputs live inside a form → no reruns / no API calls until Submit
    with st.form("self_assessment_form", clear_on_submit=False):
        for domain, items in DOMAINS.items():
            with st.expander(domain, expanded=False):
                for code, label in items:
                    key = f"{code}-{label}"
                    selections[f"{code} {label}"] = st.radio(
                        f"{code} — {label}",
                        RATINGS,
                        index=None,
                        key=key,
                    ) or ""
                if ENABLE_REFLECTIONS:
                    reflections[domain] = st.text_area(
                        f"{domain} Reflection (optional)",
                        key=f"refl-{domain}",
                        placeholder="Notes / evidence / next steps (optional)",
                    )

        # progress (computed locally; no API)
        selected_count = sum(1 for v in selections.values() if v)
        st.progress(selected_count / total_items if total_items else 0.0)
        st.caption(f"Progress: {selected_count}/{total_items} sub‑strands completed")

        submitted = st.form_submit_button("✅ Submit")

    if submitted:
        if selected_count < total_items:
            st.warning("Please rate **all** sub‑strands before submitting.")
        else:
            # Append‑only write (single API call, with backoff)
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                email_input,
                user_row.get("Name", ""),
                user_row.get("Appraiser", "Not Assigned"),
            ]
            for domain, items in DOMAINS.items():
                for code, label in items:
                    row.append(selections[f"{code} {label}"])
                if ENABLE_REFLECTIONS:
                    row.append(reflections.get(domain, ""))

            try:
                with_backoff(RESP_WS.append_row, row, value_input_option="USER_ENTERED")
                st.success("🎉 Submitted. Thank you!")
            except Exception as e:
                st.error("⚠️ Could not submit right now. Please try again shortly.")
                st.caption(f"Debug info: {e}")
else:
    st.info("Enter your school email in the sidebar to begin.")

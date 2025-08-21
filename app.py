
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
# RERUN helper (Streamlit API changed)
# =========================
def _rerun():
    try:
        st.rerun()  # Streamlit >=1.32
    except AttributeError:
        st.experimental_rerun()  # Older versions

# =========================
# UI CONFIG (must be first)
# =========================
st.set_page_config(page_title="OIS Teacher Self‑Assessment", layout="wide")

# =========================
# CONFIG
# =========================
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
ENABLE_REFLECTIONS = True  # set False to hide reflection boxes

# Optional: list of admin emails (lowercase) in .streamlit/secrets.toml
ADMINS_FROM_SECRETS = set([e.strip().lower() for e in st.secrets.get("admins", [])])

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
                time.sleep(delay); delay *= 2; last_exc = e; continue
            raise
        except gspread.exceptions.APIError as e:  # gspread-wrapped
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
# ONE-TIME SHEETS CONNECTION (cached)
# =========================
@st.cache_resource
def get_worksheets():
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
    client = gspread.authorize(creds)
    try:
        ss = client.open_by_key(SPREADSHEET_ID)
        resp_ws = ss.worksheet("Responses")
        users_ws = ss.worksheet("Users")
        return resp_ws, users_ws
    except Exception as e:
        st.error("⚠️ Could not access Google Sheet. Ensure the service account has **Editor** access and the Sheet ID is correct.")
        st.caption(f"Debug info: {e}")
        st.stop()

RESP_WS, USERS_WS = get_worksheets()

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
    norm_map = {c.strip().lower(): c for c in cols}
    for want in candidates:
        key = want.strip().lower()
        if key in norm_map: return norm_map[key]
    for c in cols:
        cl = c.strip().lower()
        if any(w in cl for w in candidates): return c
    return None

@st.cache_resource
def load_users_once_df():
    records = with_backoff(USERS_WS.get_all_records)
    if not records:
        return pd.DataFrame(columns=["Email", "Name", "Appraiser", "Role"])
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["Email", "Name", "Appraiser", "Role"])

    cols = list(df.columns)

    email_header = _pick_col(["email","school email","work email","ois email","e-mail"], cols)
    name_header = _pick_col(["name","full name","teacher name","staff name"], cols)
    appraiser_header = _pick_col(["appraiser","line manager","manager","appraiser name","supervisor"], cols)
    role_header = _pick_col(["role","access","admin"], cols)

    out = pd.DataFrame()
    out["Email"] = df[email_header].astype(str).str.strip().str.lower() if email_header else ""
    out["Name"] = df[name_header].astype(str).str.strip() if name_header else ""
    out["Appraiser"] = (df[appraiser_header].astype(str).str.strip().replace({"": "Not Assigned"})
                        if appraiser_header else "Not Assigned")
    out["Role"] = df[role_header].astype(str).str.strip().str.lower() if role_header else ""
    return out

users_df = load_users_once_df()

# =========================
# RESPONSES cache (for 'My submission' and Admin)
# =========================
@st.cache_data(ttl=180)  # slightly longer to reduce bursts
def load_responses_df():
    vals = with_backoff(RESP_WS.get_all_values)
    if not vals:
        return pd.DataFrame()
    header, rows = vals[0], vals[1:]
    df = pd.DataFrame(rows, columns=header) if rows else pd.DataFrame(columns=header)
    # normalize
    if "Email" in df.columns:
        df["Email"] = df["Email"].astype(str).str.lower()
    return df

def user_has_submission(email: str) -> bool:
    if not email:
        return False
    df = load_responses_df()
    return (not df.empty) and ("Email" in df.columns) and (not df[df["Email"] == email.strip().lower()].empty)

# =========================
# AUTH: Login / Logout
# =========================

# ---- Sidebar: Login box ----
st.sidebar.header("Account")
if st.session_state.auth_email:
    st.sidebar.success(f"Logged in as **{st.session_state.auth_name or st.session_state.auth_email}**")
    if st.sidebar.button("Logout"):
        st.session_state.auth_email = ""
        st.session_state.auth_name = ""
        st.session_state.submitted = False
        _rerun()
else:
    email_input = st.sidebar.text_input("School email (e.g., firstname.lastname@oberoi-is.org)").strip().lower()
    login = st.sidebar.button("Login")
    if login:
        if email_input and not users_df.empty and "Email" in users_df.columns:
            match = users_df[users_df["Email"] == email_input]
            if not match.empty:
                st.session_state.auth_email = email_input
                st.session_state.auth_name = match.iloc[0].get("Name","")
                st.success("Logged in.")
                _rerun()
            else:
                st.sidebar.error("Email not found in Users sheet.")

# =========================
# Sidebar: Live progress (no API calls)
# =========================
total_items = sum(len(v) for v in DOMAINS.values())
def current_progress_from_session() -> int:
    count = 0
    for _, items in DOMAINS.items():
        for code, label in items:
            if st.session_state.get(f"{code}-{label}"):
                count += 1
    return count

with st.sidebar.expander("Progress", expanded=True):
    done = current_progress_from_session()
    st.progress(done / total_items if total_items else 0.0)
    st.caption(f"{done}/{total_items} sub‑strands completed")

# Main Nav
st.title("🌟 OIS Teacher Self‑Assessment 2025‑26")

if not st.session_state.auth_email:
    st.info("Please log in from the sidebar to continue.")
    st.stop()

already_submitted = user_has_submission(st.session_state.auth_email)
i_am_admin = is_admin(st.session_state.auth_email)

# If the teacher already submitted, hide the Self‑Assessment tab (admins still see it)
if already_submitted and not i_am_admin:
    st.success("Submission on file. You can view it under **My Submission**.")
    nav_options = ["My Submission"]
else:
    nav_options = ["Self‑Assessment", "My Submission"]

if i_am_admin:
    nav_options.append("Admin")

tab = st.sidebar.radio("Menu", nav_options, index=0)

# =========================
# Page: Self‑Assessment
# =========================
if already_submitted and not i_am_admin:
    st.info("You’ve already submitted your self‑assessment. You can view or download it in **My Submission**.")
    st.stop()

if tab == "Self‑Assessment":
    # Welcome
    me = users_df[users_df["Email"] == st.session_state.auth_email].iloc[0] if not users_df.empty else {}
    appraiser = me.get("Appraiser","Not Assigned") if isinstance(me, pd.Series) else "Not Assigned"
    st.sidebar.info(f"Your appraiser: **{appraiser}**")

    # Selections are just direct widgets (outside a form) so the sidebar progress updates live.
    selections = {}
    reflections = {}
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

    # Submit
    selected_count = sum(1 for v in selections.values() if v)
    col1, col2 = st.columns([1,3])
    with col1:
        submit = st.button("✅ Submit")
    with col2:
        st.write(f"**Progress:** {selected_count}/{total_items} completed")

    if submit:
        if selected_count < total_items:
            st.warning("Please rate **all** sub‑strands before submitting.")
        else:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                st.session_state.auth_email,
                st.session_state.auth_name,
                appraiser,
            ]
            for domain, items in DOMAINS.items():
                for code, label in items:
                    row.append(selections[f"{code} {label}"])
                if ENABLE_REFLECTIONS:
                    row.append(reflections.get(domain, ""))

            try:
                with_backoff(RESP_WS.append_row, row, value_input_option="USER_ENTERED")
                # make new submission visible immediately
                load_responses_df.clear()
                st.session_state.submitted = True
                st.success("🎉 Submitted. Thank you! See **My Submission** to review your responses.")
            except Exception as e:
                st.error("⚠️ Could not submit right now. Please try again shortly.")
                st.caption(f"Debug info: {e}")

# =========================
# Page: My Submission (teacher view)
# =========================
if tab == "My Submission":
    df = load_responses_df()
    my = df[df["Email"] == st.session_state.auth_email] if not df.empty and "Email" in df.columns else pd.DataFrame()

    # auto-refresh (handles stale cache after recent submit)
    if my.empty:
        load_responses_df.clear()
        df = load_responses_df()
        my = df[df["Email"] == st.session_state.auth_email] if not df.empty and "Email" in df.columns else pd.DataFrame()

    st.subheader("My Submission")
    if my.empty:
        st.info("No submission found yet.")
    else:
        my_sorted = my.sort_values("Timestamp", ascending=False)
        latest = my_sorted.head(1)
        st.dataframe(latest, use_container_width=True)
        csv = my_sorted.to_csv(index=False).encode("utf-8")
        st.download_button("Download my submissions (CSV)", data=csv, file_name="my_self_assessment.csv", mime="text/csv")

    if st.button("🔄 Refresh"):
        load_responses_df.clear()
        _rerun()

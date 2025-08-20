# app.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# =========================
# CONFIG
# =========================
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
ENABLE_REFLECTIONS = True  # set to False if you want to hide reflection boxes

# =========================
# DOMAINS & SUB-STRANDS (exact from rubric)
# code and short label -> "A1 Expertise" etc. are used as sheet headers
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
# ONE-TIME SHEETS CONNECTION
# =========================
def connect_sheets():
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
    client = gspread.authorize(creds)
    try:
        ss = client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error("⚠️ Could not access Google Sheet. Please confirm the service account has **Editor** access.")
        st.caption(f"Debug info: {e}")
        st.stop()
    return ss

SS = connect_sheets()
RESP_WS = SS.worksheet("Responses")
USERS_WS = SS.worksheet("Users")

# =========================
# CACHING (quota‑friendly)
# =========================
@st.cache_data(ttl=300)  # cache Users for 5 minutes shared by all users
def load_users_cached():
    return USERS_WS.get_all_records()

# Optional: cached admin data view (if you add an admin page later)
@st.cache_data(ttl=120)
def load_responses_cached():
    return RESP_WS.get_all_records()

# =========================
# HEADERS (done once per app lifetime)
# =========================
@st.cache_resource
def ensure_headers_once():
    expected = ["Timestamp", "Email", "Name", "Appraiser"]
    for domain, items in DOMAINS.items():
        for code, label in items:
            expected.append(f"{code} {label}")
        if ENABLE_REFLECTIONS:
            expected.append(f"{domain} Reflection")
    current = RESP_WS.row_values(1)
    if current != expected:
        if current:
            RESP_WS.delete_rows(1)
        RESP_WS.insert_row(expected, 1)
    return True

ensure_headers_once()

# =========================
# UI
# =========================
st.set_page_config(page_title="OIS Teacher Self‑Assessment", layout="wide")
st.title("🌟 OIS Teacher Self‑Assessment 2025‑26")

users_df = pd.DataFrame(load_users_cached())

st.sidebar.header("Teacher Login")
email = st.sidebar.text_input("School email").strip()

user_row = None
if email:
    match = users_df[users_df["Email"].str.lower() == email.lower()]
    if not match.empty:
        user_row = match.iloc[0]
        appraiser = user_row.get("Appraiser", "Not Assigned")
        st.sidebar.success(f"Welcome **{user_row['Name']}**")
        st.sidebar.info(f"Your appraiser: **{appraiser}**")
    else:
        st.sidebar.error("Email not found in Users sheet.")

if user_row is not None:
    st.header("📋 Self‑Assessment")
    selections = {}
    reflections = {}

    total_items = sum(len(v) for v in DOMAINS.values())
    selected_count = 0

    for domain, items in DOMAINS.items():
        with st.expander(domain, expanded=False):
            for code, label in items:
                key = f"{code}-{label}"
                choice = st.radio(
                    f"{code} — {label}",
                    RATINGS,
                    index=None,  # no default selection
                    key=key,
                )
                if choice:
                    selected_count += 1
                selections[f"{code} {label}"] = choice or ""
            if ENABLE_REFLECTIONS:
                reflections[domain] = st.text_area(
                    f"{domain} Reflection (optional)",
                    key=f"refl-{domain}",
                    placeholder="Notes / evidence / next steps (optional)",
                )

    st.progress(selected_count / total_items if total_items else 0.0)
    st.caption(f"Progress: {selected_count}/{total_items} sub‑strands completed")

    if st.button("✅ Submit"):
        if selected_count < total_items:
            st.warning("Please rate **all** sub‑strands before submitting.")
        else:
            # Append‑only write (no re‑read)
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                email,
                user_row["Name"],
                user_row.get("Appraiser", "Not Assigned"),
            ]
            for domain, items in DOMAINS.items():
                for code, label in items:
                    row.append(selections[f"{code} {label}"])
                if ENABLE_REFLECTIONS:
                    row.append(reflections.get(domain, ""))

            try:
                RESP_WS.append_row(row, value_input_option="USER_ENTERED")
                st.success("🎉 Submitted. Thank you!")
            except Exception as e:
                st.error("⚠️ Could not submit right now. Please try again shortly.")
                st.caption(f"Debug info: {e}")

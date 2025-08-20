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
ENABLE_REFLECTIONS = True  # set False if you want to hide reflection boxes

# Authenticate via Streamlit Secrets
creds = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
client = gspread.authorize(creds)

# Safer open with clear error
try:
    ss = client.open_by_key(SPREADSHEET_ID)
except Exception as e:
    st.error("⚠️ Could not access Google Sheet. Please confirm the service account has **Editor** access.")
    st.caption(f"Debug info: {e}")
    st.stop()

RESP_WS = ss.worksheet("Responses")
USERS_WS = ss.worksheet("Users")

# =========================
# DOMAINS & SUB-STRANDS (exact from your rubric)
# Each sub-strand is (code, short label)
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

# Ratings (exact rubric wording)
RATINGS = [
    "Highly Effective",
    "Effective",
    "Improvement Necessary",
    "Does Not Meet Standards",
]

# =========================
# CACHING (quota-friendly)
# =========================
@st.cache_data(ttl=180)  # 3 minutes
def load_users():
    return USERS_WS.get_all_records()

@st.cache_data(ttl=180)
def load_admin_view():
    return RESP_WS.get_all_records()

# =========================
# SHEET HEADER MANAGEMENT
# =========================
def ensure_headers():
    expected = ["Timestamp", "Email", "Name", "Appraiser"]
    for domain, items in DOMAINS.items():
        for code, label in items:
            expected.append(f"{code} {label}")
        if ENABLE_REFLECTIONS:
            expected.append(f"{domain} Reflection")
    current = RESP_WS.row_values(1)
    if current != expected:
        if current:
            RESP_WS.delete_rows(1)  # replace mismatched header row
        RESP_WS.insert_row(expected, 1)

# =========================
# UI
# =========================
st.set_page_config(page_title="OIS Teacher Self-Assessment", layout="wide")
st.title("🌟 OIS Teacher Self‑Assessment 2025‑26")

users_df = pd.DataFrame(load_users())
st.sidebar.header("Teacher Login")
email = st.sidebar.text_input("School email").strip()

user_row = None
if email:
    match = users_df[users_df["Email"].str.lower() == email.lower()]
    if not match.empty:
        user_row = match.iloc[0]
        st.sidebar.success(f"Welcome **{user_row['Name']}**")
        appraiser = user_row.get("Appraiser", "Not Assigned")
        st.sidebar.info(f"Your appraiser: **{appraiser}**")
    else:
        st.sidebar.error("Email not found in the Users sheet.")

if user_row is not None:
    st.header("📋 Self‑Assessment")
    selections = {}
    reflections = {}

    # count for progress
    total_items = sum(len(v) for v in DOMAINS.values())
    selected_count = 0

    for domain, items in DOMAINS.items():
        with st.expander(domain, expanded=False):
            for code, label in items:
                key = f"{code}-{label}"
                choice = st.radio(
                    f"{code} — {label}",
                    RATINGS,
                    index=None,  # no default
                    horizontal=False,
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

    # simple progress
    st.progress(selected_count / total_items if total_items else 0.0)
    st.caption(f"Progress: {selected_count}/{total_items} sub‑strands completed")

    if st.button("✅ Submit"):
        if selected_count < total_items:
            st.warning("Please rate all sub‑strands before submitting.")
        else:
            ensure_headers()
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                email,
                user_row["Name"],
                user_row.get("Appraiser", "Not Assigned"),
            ]
            # ratings in A1..F9 order
            for domain, items in DOMAINS.items():
                for code, label in items:
                    row.append(selections[f"{code} {label}"])
                if ENABLE_REFLECTIONS:
                    row.append(reflections.get(domain, ""))

            try:
                RESP_WS.append_row(row)
                st.success("🎉 Submitted. Thank you!")
            except Exception as e:
                st.error("⚠️ Could not submit right now. Please try again shortly.")
                st.caption(f"Debug info: {e}")

# =========================
# ADMIN (optional, cached view)
# =========================
st.sidebar.divider()
st.sidebar.subheader("Admin Login")
admin_user = st.sidebar.text_input("Admin username")
admin_pass = st.sidebar.text_input("Password", type="password")

ADMINS = {
    "Roma": "ms123",
    "Praanot": "ms456",
    "Kirandeep": "hs123",
    "Manjula": "hs456",
    "Paul": "head123",  # Head of School (can view all)
}

if st.sidebar.button("Login as Admin"):
    if admin_user in ADMINS and admin_pass == ADMINS[admin_user]:
        st.success(f"Admin '{admin_user}' logged in")
        st.header(f"📊 Admin Dashboard — {admin_user}")

        try:
            data = load_admin_view()
            df = pd.DataFrame(data)
        except Exception as e:
            st.error("⚠️ Could not load responses.")
            st.caption(f"Debug info: {e}")
            st.stop()

        if df.empty:
            st.info("No responses yet.")
        else:
            if admin_user != "Paul":
                df = df[df["Appraiser"] == admin_user]
            st.dataframe(df, use_container_width=True)
    else:
        st.sidebar.error("Invalid admin credentials")

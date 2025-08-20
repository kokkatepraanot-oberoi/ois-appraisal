import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# ====== CONFIG ======
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"

# ====== AUTH ======
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
client = gspread.authorize(creds)

# ====== LOAD SHEETS ======
sheet = client.open_by_key(SPREADSHEET_ID)
responses_ws = sheet.worksheet("Responses")
users_ws = sheet.worksheet("Users")

# ====== APP ======
st.set_page_config(page_title="OIS Self-Assessment", layout="wide")
st.title("📊 OIS Self-Assessment")

# Load Users into dataframe
users_data = users_ws.get_all_records()
df_users = pd.DataFrame(users_data)

# ====== Framework: Domains + Sub-strands ======
domains = {
    "A: Planning and Preparation for Learning": [
        "A1 Expertise", "A2 Goals", "A3 Units", "A4 Assessments", "A5 Anticipation",
        "A6 Lessons", "A7 Materials", "A8 Differentiation", "A9 Environment"
    ],
    "B: Classroom Management": [
        "B1 Expectations", "B2 Relationships", "B3 Social Emotional", "B4 Routines",
        "B5 Responsibility", "B6 Repertoire", "B7 Prevention", "B8 Incentives"
    ],
    "C: Delivery of Instruction": [
        "C1 Expectations", "C2 Mindset", "C3 Framing", "C4 Connections", "C5 Clarity",
        "C6 Repertoire", "C7 Engagement", "C8 Differentiation", "C9 Nimbleness"
    ],
    "D: Monitoring, Assessment, and Follow-Up": [
        "D1 Criteria", "D2 Diagnosis", "D3 Goals", "D4 Feedback", "D5 Recognition",
        "D6 Analysis", "D7 Tenacity", "D8 Support", "D9 Reflection"
    ],
    "E: Family and Community Outreach": [
        "E1 Respect", "E2 Belief", "E3 Expectations", "E4 Communication", "E5 Involving",
        "E6 Responsiveness", "E7 Reporting", "E8 Outreach", "E9 Resources"
    ],
    "F: Professional Responsibility": [
        "F1 Language", "F2 Reliability", "F3 Professionalism", "F4 Judgement", "F5 Teamwork",
        "F6 Leadership", "F7 Openness", "F8 Collaboration", "F9 Growth"
    ]
}

rating_options = ["Highly Effective", "Effective", "Improvement Necessary"]

# ====== SESSION STATE for login ======
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "teacher_name" not in st.session_state:
    st.session_state.teacher_name = ""
if "teacher_email" not in st.session_state:
    st.session_state.teacher_email = ""
if "appraiser" not in st.session_state:
    st.session_state.appraiser = ""

# --- Sidebar Login / Logout ---
st.sidebar.header("🔑 Teacher Login")

if not st.session_state.logged_in:
    email_input = st.sidebar.text_input("Enter your OIS Email").strip().lower()
    if st.sidebar.button("Login"):
        user_row = df_users[df_users["Email"].str.lower() == email_input]
        if not user_row.empty:
            st.session_state.logged_in = True
            st.session_state.teacher_email = email_input
            st.session_state.teacher_name = user_row.iloc[0]["Name"]
            st.session_state.appraiser = user_row.iloc[0]["Appraiser"]
        else:
            st.sidebar.error("❌ Email not found in Users sheet.")
else:
    st.sidebar.success(f"✅ {st.session_state.teacher_name}")
    st.sidebar.info(f"📌 Appraiser: {st.session_state.appraiser}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.teacher_email = ""
        st.session_state.teacher_name = ""
        st.session_state.appraiser = ""
        st.rerun()

# ====== Main Content ======
if st.session_state.logged_in:
    st.success(f"Welcome **{st.session_state.teacher_name}** 👋")
    st.info(f"Your appraiser is **{st.session_state.appraiser}**")

    st.subheader("📝 Self-Assessment Form")

    responses = {}
    for domain, strands in domains.items():
        st.markdown(f"### {domain}")
        for strand in strands:
            responses[strand] = st.selectbox(
                strand, ["Select Rating"] + rating_options, key=strand
            )

    # --- Submit ---
    if st.button("Submit Response"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [timestamp, st.session_state.teacher_email,
               st.session_state.teacher_name, st.session_state.appraiser] + [
            responses[s] for domain in domains.values() for s in domain
        ]

        # ensure headers exist
        if not responses_ws.row_values(1):
            headers = ["Timestamp", "Email", "Name", "Appraiser"] + [
                s for domain in domains.values() for s in domain
            ]
            responses_ws.insert_row(headers, 1)

        responses_ws.append_row(row)
        st.success("✅ Response submitted successfully!")

else:
    st.warning("👆 Please login with your OIS email to continue.")

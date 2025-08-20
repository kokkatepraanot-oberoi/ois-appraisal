import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- Google Sheets Setup ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"

# Authenticate with Streamlit secrets
credentials = Credentials.from_service_account_info(
    st.secrets["google"], scopes=SCOPES
)


client = gspread.authorize(credentials)

# Open sheets
# 🔒 Safer opening with error message
try:
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
except Exception as e:
    st.error("⚠️ Could not access Google Sheet. Please confirm the service account has Editor access.")
    st.write(f"Debug info: {str(e)}")  # (optional) shows what went wrong
    st.stop()

responses_ws = spreadsheet.worksheet("Responses")
users_ws = spreadsheet.worksheet("Users")

# --- Ratings ---
RATINGS = [
    "Highly Effective",
    "Effective",
    "Improvement Necessary",
    "Does Not Meet Standards"
]

# --- Domains + Sub-strands (from rubric) ---
DOMAINS = {
    "A: Planning and Preparation for Learning": [
        "A1: Expertise", "A2: Goals", "A3: Units", "A4: Assessments", "A5: Anticipation",
        "A6: Lessons", "A7: Materials", "A8: Differentiation", "A9: Environment"
    ],
    "B: Classroom Management": [
        "B1: Expectations", "B2: Relationships", "B3: Social Emotional", "B4: Routines",
        "B5: Responsibility", "B6: Repertoire", "B7: Prevention", "B8: Incentives"
    ],
    "C: Delivery of Instruction": [
        "C1: Expectations", "C2: Mindset", "C3: Framing", "C4: Connections", "C5: Clarity",
        "C6: Repertoire", "C7: Engagement", "C8: Differentiation", "C9: Nimbleness"
    ],
    "D: Monitoring, Assessment, and Follow-Up": [
        "D1: Criteria", "D2: Diagnosis", "D3: Goals", "D4: Feedback", "D5: Recognition",
        "D6: Analysis", "D7: Tenacity", "D8: Support", "D9: Reflection"
    ],
    "E: Family and Community Outreach": [
        "E1: Respect", "E2: Belief", "E3: Expectations", "E4: Communication", "E5: Involving",
        "E6: Responsiveness", "E7: Reporting", "E8: Outreach", "E9: Resources"
    ],
    "F: Professional Responsibilities": [
        "F1: Language", "F2: Reliability", "F3: Professionalism", "F4: Judgement",
        "F5: Teamwork", "F6: Leadership", "F7: Openness", "F8: Collaboration", "F9: Growth"
    ]
}

# --- Admin credentials ---
ADMINS = {
    "Roma": "ms123",
    "Praanot": "ms456",
    "Kirandeep": "hs123",
    "Manjula": "hs456",
    "Paul": "head123"
}

# --- Helper Functions ---
def get_users():
    """Fetch Users sheet as DataFrame"""
    data = users_ws.get_all_records()
    return pd.DataFrame(data)

def ensure_headers():
    """Ensure Responses sheet has headers"""
    headers = ["Timestamp", "Email", "Name", "Appraiser"]
    for domain, strands in DOMAINS.items():
        for strand in strands:
            headers.append(strand)
        headers.append(f"{domain} Reflection")
    existing = responses_ws.row_values(1)
    if not existing or existing != headers:
        responses_ws.insert_row(headers, 1)

def save_response(email, name, appraiser, ratings_dict, reflections_dict):
    """Save a teacher's self-assessment into Responses sheet"""
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email, name, appraiser]
    for domain, strands in DOMAINS.items():
        for strand in strands:
            row.append(ratings_dict.get(strand, ""))
        row.append(reflections_dict.get(domain, ""))
    responses_ws.append_row(row)

# --- Streamlit App ---
st.title("🌟 OIS Self Assessment 2025-26")

# Load users
users_df = get_users()

# --- Teacher Login ---
st.sidebar.header("Teacher Login")
email = st.sidebar.text_input("Enter your school email:")
user = None

if email:
    match = users_df[users_df["Email"].str.lower() == email.lower()]
    if not match.empty:
        user = match.iloc[0]
        st.sidebar.success(f"Welcome {user['Name']} 👋")
        st.sidebar.info(f"Your Appraiser: **{user['Appraiser']}**")
    else:
        st.sidebar.error("Email not found in Users list.")

# --- Self Assessment Form ---
if user is not None:
    st.header("📋 Self-Assessment Form")
    ratings_dict = {}
    reflections_dict = {}

    for domain, strands in DOMAINS.items():
        with st.expander(domain, expanded=False):
            for strand in strands:
                ratings_dict[strand] = st.radio(
                    strand,
                    RATINGS,
                    index=None,  # no default selection
                    key=strand
                )
            reflections_dict[domain] = st.text_area(
                f"{domain} Reflection (Optional)", ""
            )

    if st.button("✅ Submit My Assessment"):
        ensure_headers()
        save_response(user["Email"], user["Name"], user["Appraiser"], ratings_dict, reflections_dict)
        st.success("Your self-assessment has been submitted successfully!")

# --- Admin Module ---
st.sidebar.subheader("Admin Login")
admin_user = st.sidebar.text_input("Admin Username")
admin_pass = st.sidebar.text_input("Admin Password", type="password")

if st.sidebar.button("Login as Admin"):
    if admin_user in ADMINS and admin_pass == ADMINS[admin_user]:
        st.sidebar.success(f"Admin {admin_user} logged in ✅")
        st.header(f"📊 Appraiser Dashboard - {admin_user}")

        # Load responses
        data = responses_ws.get_all_records()
        df = pd.DataFrame(data)

        if admin_user == "Paul":  # Head of School - sees all
            view_df = df
        else:
            view_df = df[df["Appraiser"] == admin_user]

        st.dataframe(view_df)
    else:
        st.sidebar.error("Invalid admin credentials")

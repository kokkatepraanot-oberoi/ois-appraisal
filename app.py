import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# ==============================
# CONFIG
# ==============================
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
RESPONSE_SHEET = "Responses"
USER_SHEET = "Users"

# Google API Scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Authenticate with Streamlit secrets
credentials = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
client = gspread.authorize(credentials)

# Open Sheets
spreadsheet = client.open_by_key(SPREADSHEET_ID)
response_ws = spreadsheet.worksheet(RESPONSE_SHEET)
user_ws = spreadsheet.worksheet(USER_SHEET)

# ==============================
# DOMAINS & SUB-STRANDS
# ==============================
DOMAINS = {
    "A. Professional Expertise": [
        "A1 Expertise",
        "A2 Goals",
        "A3 Knowledge",
        "A4 Curriculum"
    ],
    "B. Learning Environment": [
        "B1 Engagement",
        "B2 Inclusion",
        "B3 Differentiation"
    ],
    "C. Assessment": [
        "C1 Practices",
        "C2 Feedback",
        "C3 Reporting"
    ],
    "D. Professional Growth": [
        "D1 Reflection",
        "D2 Collaboration",
        "D3 Development"
    ],
    "E. Responsibilities": [
        "E1 Pastoral",
        "E2 Duties",
        "E3 Communication"
    ],
    "F. Contribution": [
        "F1 Community",
        "F2 Innovation",
        "F3 Leadership"
    ]
}

RATINGS = [
    "Does Not Meet Standards",
    "Approaches Standards",
    "Meets Standards",
    "Exceeds Standards"
]

# ==============================
# HELPER FUNCTIONS
# ==============================
def get_user(email):
    """Fetch user info from Users sheet."""
    users = user_ws.get_all_records()
    for u in users:
        if u["Email"].strip().lower() == email.strip().lower():
            return u
    return None

def ensure_headers():
    """Ensure headers exist in the Response sheet."""
    headers = response_ws.row_values(1)
    if not headers:
        cols = ["Timestamp", "Name", "Email", "Appraiser"]
        for d, subs in DOMAINS.items():
            cols.extend(subs)
        cols.append("Reflection")
        response_ws.insert_row(cols, 1)

def save_response(name, email, appraiser, ratings, reflection):
    """Save one submission to Google Sheet."""
    ensure_headers()
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, email, appraiser]
    for d, subs in DOMAINS.items():
        for sub in subs:
            row.append(ratings.get(sub, ""))
    row.append(reflection)
    response_ws.append_row(row)

def has_submitted(email):
    """Check if user already submitted."""
    emails = response_ws.col_values(3)  # Email column
    return email in emails

# ==============================
# STREAMLIT APP
# ==============================
st.set_page_config(page_title="Teacher Self-Assessment", layout="wide")

st.title("📋 Teacher Self-Assessment Form")

email = st.text_input("Enter your school email:")

if email:
    user = get_user(email)
    if not user:
        st.error("❌ Email not found in the system. Please check with Admin.")
    else:
        name = user["Name"]
        appraiser = user.get("Appraiser", "Not Assigned")

        st.success(f"Welcome **{name}** 👋\n\nYour appraiser is: **{appraiser}**")

        if has_submitted(email):
            st.info("✅ You have already submitted your self-assessment. Thank you!")
        else:
            st.write("Please complete all sub-strands. Reflection is optional.")

            responses = {}
            total = sum(len(subs) for subs in DOMAINS.values())
            filled = 0

            for domain, subs in DOMAINS.items():
                st.subheader(domain)
                for sub in subs:
                    choice = st.radio(
                        sub,
                        RATINGS,
                        key=sub,
                        horizontal=True,
                        index=None
                    )
                    if choice:
                        responses[sub] = choice
                        filled += 1

            reflection = st.text_area("Optional Reflection")

            # Progress
            progress = int((filled / total) * 100)
            st.progress(progress / 100)
            st.caption(f"Progress: {filled}/{total} ({progress}%)")

            # Submit
            if st.button("Submit"):
                if filled < total:
                    st.warning("⚠️ Please complete all required sub-strands before submitting.")
                else:
                    save_response(name, email, appraiser, responses, reflection)
                    st.success("🎉 Your self-assessment has been submitted and locked.")


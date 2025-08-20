import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# ==============================
# Google Sheets Setup
# ==============================
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
RESPONSES_SHEET = "Responses"
USERS_SHEET = "Users"

scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

# Load credentials
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

responses_ws = client.open_by_key(SPREADSHEET_ID).worksheet(RESPONSES_SHEET)
users_ws = client.open_by_key(SPREADSHEET_ID).worksheet(USERS_SHEET)

# ==============================
# Load Users into dictionary
# ==============================
users_data = users_ws.get_all_records()
email_to_user = {u["Email"].strip().lower(): u for u in users_data}

# ==============================
# Domain A (for testing)
# ==============================
DOMAIN_A = {
    "title": "Planning and Preparation for Learning",
    "subs": [
        "A1. Expertise",
        "A2. Goals",
        "A3. Units",
        "A4. Assessments",
        "A5. Anticipation"
    ]
}

RATINGS = ["Highly Effective", "Effective", "Improvement Necessary", "Does Not Meet Standards"]

# ==============================
# Streamlit UI
# ==============================
st.title("OIS Self-Assessment Form (Test)")

email = st.text_input("Enter your school email").strip().lower()

name, appraiser = "", ""
if email in email_to_user:
    user = email_to_user[email]
    name = user.get("Name", "")
    appraiser = user.get("Appraiser", "")
    st.success(f"Welcome {name}! Your appraiser is **{appraiser}**.")
else:
    if email:
        st.warning("Email not found in Users sheet. Please check your spelling.")

responses = {}

st.header(f"Domain A: {DOMAIN_A['title']}")
for sub in DOMAIN_A["subs"]:
    responses[sub] = st.radio(
        sub,
        RATINGS,
        index=None,   # no default selection
        horizontal=True
    )

if st.button("Submit"):
    if not email or not name:
        st.error("Please enter a valid email (must match Users sheet).")
    else:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [now, email, name, appraiser] + [responses[sub] if responses[sub] else "" for sub in DOMAIN_A["subs"]]
        
        # Write headers only if empty
        if not responses_ws.get_all_values():
            headers = ["Timestamp", "Email", "Name", "Appraiser"] + DOMAIN_A["subs"]
            responses_ws.append_row(headers)
        
        responses_ws.append_row(row)
        st.success("Response submitted successfully!")


import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# --------------------
# CONFIGURATION
# --------------------

# Google Sheets setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["google"], scopes=SCOPES
)
client = gspread.authorize(creds)

# Spreadsheet IDs from secrets
USERS_SHEET_ID = st.secrets["users_sheet_id"]
RESPONSES_SHEET_ID = st.secrets["responses_sheet_id"]

users_sheet = client.open_by_key(USERS_SHEET_ID).sheet1
responses_sheet = client.open_by_key(RESPONSES_SHEET_ID).sheet1

# Admins from secrets
ADMINS = set([e.strip().lower() for e in st.secrets.get("admins", [])])

# --------------------
# HELPER FUNCTIONS
# --------------------

@st.cache_data(ttl=600)
def load_users():
    data = users_sheet.get_all_records()
    return pd.DataFrame(data)

def append_response(row):
    responses_sheet.append_row(row, value_input_option="USER_ENTERED")

def load_responses():
    data = responses_sheet.get_all_records()
    return pd.DataFrame(data)

# --------------------
# APP
# --------------------

st.title("OIS Appraisal System")

email = st.text_input("Enter your school email:").strip().lower()

if email:
    users_df = load_users()
    user_row = users_df[users_df["Email"].str.lower() == email]

    # Check if email is in users sheet or in admins
    if not user_row.empty or email in ADMINS:
        st.success(f"Logged in as {email}")

        # Admin view
        if email in ADMINS:
            st.subheader("📊 Admin Panel - View Submissions")
            responses_df = load_responses()
            if responses_df.empty:
                st.info("No submissions yet.")
            else:
                # Group by Teacher
                grouped = responses_df.groupby("Teacher")
                for teacher, group in grouped:
                    st.markdown(f"### {teacher}")
                    st.dataframe(group)
        else:
            # Teacher normal view
            st.subheader("Teacher Appraisal Form")
            teacher_name = user_row.iloc[0]["Name"]
            st.write(f"Welcome, {teacher_name}! Please complete your appraisal below.")

            # Example domains - from your working.py
            DOMAINS = {
                "A. Professional Knowledge": [
                    "Demonstrates knowledge of subject matter",
                    "Applies pedagogy effectively",
                    "Incorporates curriculum standards"
                ],
                "B. Instructional Planning": [
                    "Designs effective lesson plans",
                    "Differentiates instruction",
                    "Uses resources efficiently"
                ],
                "C. Classroom Environment": [
                    "Creates a positive learning environment",
                    "Manages student behavior effectively",
                    "Promotes respect and collaboration"
                ],
                "D. Professional Responsibilities": [
                    "Engages in professional growth",
                    "Collaborates with colleagues",
                    "Communicates with families"
                ]
            }

            responses = {}
            for domain, items in DOMAINS.items():
                st.markdown(f"#### {domain}")
                for item in items:
                    rating = st.selectbox(f"{item}", ["1", "2", "3", "4", "5"], key=item)
                    responses[item] = rating

            if st.button("Submit"):
                row = [teacher_name, email] + list(responses.values())
                append_response(row)
                st.success("✅ Response submitted!")

    else:
        st.error("Email not found in users or admins list.")

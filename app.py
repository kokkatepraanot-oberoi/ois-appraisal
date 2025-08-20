import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# -------------------------
# GOOGLE SHEETS CONNECTION
# -------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
responses_ws = client.open_by_key(SPREADSHEET_ID).worksheet("Responses")
users_ws = client.open_by_key(SPREADSHEET_ID).worksheet("Users")

# -------------------------
# APP CONFIG
# -------------------------
st.set_page_config(page_title="OIS Teacher Appraisal", layout="wide")

# Sub-strands for self-assessment
domains = {
    "Domain A: Planning": ["Expertise", "Clarity", "Curriculum"],
    "Domain B: Instruction": ["Engagement", "Strategies", "Technology"],
    "Domain C: Assessment": ["Feedback", "Differentiation", "Data Use"],
    "Domain D: Classroom": ["Environment", "Respect", "Expectations"],
    "Domain E: Professionalism": ["Collaboration", "Ethics", "Reflection"],
    "Domain F: Growth": ["Innovation", "PD", "Leadership"]
}

rating_options = [
    "Highly Effective", "Effective",
    "Improvement Necessary", "Does Not Meet Standards"
]

# -------------------------
# FUNCTIONS
# -------------------------
def get_user_info(email):
    """Look up user info from Users sheet"""
    records = users_ws.get_all_records()
    for row in records:
        if row.get("Email", "").strip().lower() == email.strip().lower():
            return row
    return None

def init_headers():
    """Ensure headers exist in Responses"""
    headers = responses_ws.row_values(1)
    if not headers:
        col_headers = ["Timestamp", "Email", "Name"]
        for domain, subs in domains.items():
            for sub in subs:
                col_headers.append(sub)
        responses_ws.append_row(col_headers)

def save_response(email, name, answers):
    """Append one response row"""
    init_headers()
    row = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           email, name]
    for domain, subs in domains.items():
        for sub in subs:
            row.append(answers.get(f"{domain}-{sub}", ""))
    responses_ws.append_row(row)

def load_responses():
    return responses_ws.get_all_records()

# -------------------------
# LOGIN
# -------------------------
st.sidebar.title("Login")

mode = st.sidebar.radio("Select Mode", ["Teacher", "Admin"])

if mode == "Teacher":
    email = st.sidebar.text_input("Enter your email:")
    if email:
        user = get_user_info(email)
        if not user:
            st.error("Email not found in Users sheet.")
        else:
            st.success(f"Welcome {user['Name']} ({user['Designation']})")

            st.header("Self-Assessment Form")

            answers = {}
            total = sum(len(v) for v in domains.values())
            completed = 0

            with st.form("self_assess"):
                for domain, subs in domains.items():
                    st.subheader(domain)
                    for sub in subs:
                        key = f"{domain}-{sub}"
                        choice = st.radio(
                            sub, rating_options, index=None, key=key, horizontal=True
                        )
                        if choice:
                            answers[key] = choice
                            completed += 1

                progress = int((completed / total) * 100)
                st.progress(progress)
                st.caption(f"{completed}/{total} sub-strands completed ({progress}%)")

                submitted = st.form_submit_button("Submit")
                if submitted:
                    save_response(email, user["Name"], answers)
                    st.success("Your responses have been submitted!")

# -------------------------
# ADMIN DASHBOARD
# -------------------------
if mode == "Admin":
    st.sidebar.subheader("Admin Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    admins = {
        "paul": {"pw": "head123", "scope": "ALL"},
        "roma": {"pw": "ms123", "scope": "MS"},
        "praanot": {"pw": "ms123", "scope": "MS"},
        "kirandeep": {"pw": "hs123", "scope": "HS"},
        "manjula": {"pw": "hs123", "scope": "HS"},
    }

    if username in admins and password == admins[username]["pw"]:
        st.success(f"Welcome Admin {username.title()}")

        data = load_responses()
        if not data:
            st.warning("No responses yet.")
        else:
            import pandas as pd
            df = pd.DataFrame(data)

            scope = admins[username]["scope"]
            if scope == "MS":
                df = df[df["Designation"].str.contains("Secondary", na=False)]
            elif scope == "HS":
                df = df[df["Designation"].str.contains("Secondary", na=False)]
            # Paul has ALL, no filter

            st.dataframe(df)

    elif username and password:
        st.error("Invalid credentials")

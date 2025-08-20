import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# ===== Google Sheets Setup =====
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

credentials = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
client = gspread.authorize(credentials)

responses_ws = client.open_by_key(SPREADSHEET_ID).worksheet("Responses")
users_ws = client.open_by_key(SPREADSHEET_ID).worksheet("Users")

# ===== Load Users =====
users_data = users_ws.get_all_records()
user_lookup = {u["Email"]: u for u in users_data}

# ===== Admin Accounts =====
ADMIN_USERS = {
    "Roma": {"password": "roma123", "role": "Appraiser"},
    "Praanot": {"password": "praanot123", "role": "Appraiser"},
    "Kirandeep": {"password": "kirandeep123", "role": "Appraiser"},
    "Manjula": {"password": "manjula123", "role": "Appraiser"},
    "Paul": {"password": "paul123", "role": "Head of School"},
}

# ===== Strand Headers =====
HEADERS = [
    "Timestamp", "Email", "Name", "Appraiser",
    "A1 Expertise", "A2 Goals", "A3 Units", "A4 Assessments", "A5 Anticipation"
]

# ===== Ensure Headers Exist =====
if not responses_ws.row_values(1):
    responses_ws.append_row(HEADERS)

# ===== Streamlit App =====
st.sidebar.title("OIS Appraisal Portal")
menu = st.sidebar.radio("Navigate", ["Self-Assessment", "Admin Dashboard"])

# ---------- SELF-ASSESSMENT ----------
if menu == "Self-Assessment":
    st.header("Self-Assessment Form")

    # Teacher login (simplified: via email only)
    email = st.text_input("Enter your school email:")
    if email in user_lookup:
        name = user_lookup[email]["Name"]
        appraiser = user_lookup[email].get("Appraiser", "Not Assigned")
        st.success(f"Welcome {name}! Your Appraiser is **{appraiser}**")

        with st.form("self_assessment"):
            a1 = st.selectbox("A1 Expertise", ["Highly Effective", "Effective", "Improvement Necessary"])
            a2 = st.selectbox("A2 Goals", ["Highly Effective", "Effective", "Improvement Necessary"])
            a3 = st.selectbox("A3 Units", ["Highly Effective", "Effective", "Improvement Necessary"])
            a4 = st.selectbox("A4 Assessments", ["Highly Effective", "Effective", "Improvement Necessary"])
            a5 = st.selectbox("A5 Anticipation", ["Highly Effective", "Effective", "Improvement Necessary"])

            submitted = st.form_submit_button("Submit")
            if submitted:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row = [timestamp, email, name, appraiser, a1, a2, a3, a4, a5]
                responses_ws.append_row(row)
                st.success("✅ Your self-assessment has been recorded!")

    elif email:
        st.error("Email not found in Users sheet. Please contact admin.")

# ---------- ADMIN DASHBOARD ----------
elif menu == "Admin Dashboard":
    st.header("Admin Dashboard")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in ADMIN_USERS and ADMIN_USERS[username]["password"] == password:
            st.success(f"Welcome {username}!")

            all_data = responses_ws.get_all_records()

            if ADMIN_USERS[username]["role"] == "Head of School":
                st.info("You can view ALL submissions")
                st.dataframe(all_data)

            else:
                st.info(f"You can view submissions assigned to **{username}**")
                my_data = [r for r in all_data if r.get("Appraiser") == username]
                st.dataframe(my_data)

        else:
            st.error("Invalid login credentials")

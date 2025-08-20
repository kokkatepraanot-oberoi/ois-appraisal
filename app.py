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
st.title("📊 OIS Self-Assessment Test App")

# Load Users into dataframe
users_data = users_ws.get_all_records()
df_users = pd.DataFrame(users_data)

# --- Login ---
st.sidebar.header("🔑 Teacher Login")
email_input = st.sidebar.text_input("Enter your OIS Email").strip().lower()

if email_input:
    user_row = df_users[df_users["Email"].str.lower() == email_input]

    if not user_row.empty:
        teacher_name = user_row.iloc[0]["Name"]
        appraiser = user_row.iloc[0]["Appraiser"]

        st.success(f"✅ Logged in as **{teacher_name}**")
        st.info(f"📌 Your appraiser is **{appraiser}**")

        # --- Form: self-assessment ---
        st.subheader("📝 Submit Your Self-Assessment")

        expertise = st.selectbox("A1. Expertise", ["Highly Effective", "Effective", "Improvement Necessary"])
        clarity = st.selectbox("A2. Goals/Clarity", ["Highly Effective", "Effective", "Improvement Necessary"])

        if st.button("Submit Response"):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            responses_ws.append_row([timestamp, email_input, teacher_name, appraiser, expertise, clarity])
            st.success("✅ Response submitted successfully!")

    else:
        st.error("❌ Email not found in Users sheet. Please check with Admin.")

# --- Admin Debug ---
st.sidebar.markdown("---")
if st.sidebar.checkbox("👀 Show Data (Admin Debug)"):
    st.subheader("Users Sheet")
    st.dataframe(df_users)
    st.subheader("Responses Sheet")
    df_responses = pd.DataFrame(responses_ws.get_all_records())
    st.dataframe(df_responses)

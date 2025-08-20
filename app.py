import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

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

# Responses sheet
responses_ws = sheet.worksheet("Responses")

# Users sheet
users_ws = sheet.worksheet("Users")

# ====== APP ======
st.set_page_config(page_title="OIS Appraisal Test", layout="wide")

st.title("📊 OIS Self-Assessment Test App")

# --- Show Users data
st.subheader("👥 Users Sheet Data")
users_data = users_ws.get_all_records()
if users_data:
    df_users = pd.DataFrame(users_data)
    st.dataframe(df_users)
else:
    st.warning("No data in Users sheet yet.")

# --- Show Responses data
st.subheader("📝 Responses Sheet Data")
responses_data = responses_ws.get_all_records()
if responses_data:
    df_responses = pd.DataFrame(responses_data)
    st.dataframe(df_responses)
else:
    st.warning("No responses yet.")

# --- Quick test: add dummy row
if st.button("➕ Add Dummy Response"):
    responses_ws.append_row(
        ["2025-08-20 17:00", "test@oberoi-is.org", "Test Teacher", "Roma", "Effective"]
    )
    st.success("Dummy response added! Refresh to see it in the sheet.")

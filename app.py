
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Authorize client
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scope)
client = gspread.authorize(creds)

# Use hardcoded ID
SPREADSHEET_ID = "1kqcfmMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

st.title("OIS Appraisal System")

# Example read
data = sheet.get_all_records()
st.write("Current data in sheet:", data)

# Example append
with st.form("appraisal_form"):
    name = st.text_input("Your Name")
    rating = st.slider("Rating", 1, 5)
    submitted = st.form_submit_button("Submit")
    if submitted:
        sheet.append_row([name, rating])
        st.success("✅ Response recorded!")

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import json

# Load Google Service Account credentials from Streamlit secrets
creds_dict = st.secrets["google"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict, 
    scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)

# ✅ Hardcoded Spreadsheet ID
SPREADSHEET_ID = "1kqcfmMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJyp0jpY"
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

st.success("Connected to Google Sheet successfully!")

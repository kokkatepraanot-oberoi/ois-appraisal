import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

credentials = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
client = gspread.authorize(credentials)

SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"

try:
    sheet = client.open_by_key(SPREADSHEET_ID)
    st.write("✅ Connected to:", sheet.title)
    st.write("Worksheets:", [ws.title for ws in sheet.worksheets()])
except Exception as e:
    st.error(f"❌ Could not open spreadsheet: {e}")

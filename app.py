import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# CONFIG
# ----------------------------
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"  # <-- Replace with your actual Sheet ID

# ----------------------------
# CONNECT TO GOOGLE SHEET
# ----------------------------
@st.cache_data
def connect_to_gsheet():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["google"],  # using the [google] section in secrets.toml
            scopes=scope
        )
        gc = gspread.authorize(creds)  # this is your client
        sh = gc.open_by_key(SPREADSHEET_ID)
        return sh
    except Exception as e:
        st.error(f"⚠️ Could not connect to Google Sheets: {e}")
        st.stop()

# ----------------------------
# DEMO USAGE
# ----------------------------
def main():
    st.title("OIS Appraisal")
    sh = connect_to_gsheet()
    st.success("✅ Connected to Google Sheets successfully!")
    st.write("Spreadsheet title:", sh.title)

if __name__ == "__main__":
    main()

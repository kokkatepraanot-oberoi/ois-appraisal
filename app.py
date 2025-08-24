import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from streamlit_oauth import OAuth2Component
import pandas as pd

# =========================
# CONFIG
# =========================
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CLIENT_ID = st.secrets["oauth"]["client_id"]
CLIENT_SECRET = st.secrets["oauth"]["client_secret"]
REDIRECT_URI = st.secrets["oauth"]["redirect_uri"]

# =========================
# Google Sheets connection
# =========================
def get_users_df():
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(SPREADSHEET_ID).worksheet("Users")
    return pd.DataFrame(ws.get_all_records())

users_df = get_users_df()

# =========================
# UI
# =========================
st.set_page_config(page_title="OIS Login", layout="centered")
st.title("🔐 OIS Teacher Appraisal Login")

oauth2 = OAuth2Component(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    revoke_endpoint="https://oauth2.googleapis.com/revoke",
)

if "token" not in st.session_state:
    result = oauth2.authorize_button(
        name="Login with Google",
        icon="https://developers.google.com/identity/images/g-logo.png",
        redirect_uri=REDIRECT_URI,
        scope="openid email profile",
        key="google",
    )
    if result:
        st.session_state.token = result
        st.rerun()
else:
    token = st.session_state.token
    user_info = oauth2.get_user_info(token)
    email = user_info.get("email", "").lower()

    # Verify in Users sheet
    match = users_df[users_df["Email"].str.lower() == email]
    if match.empty:
        st.error("❌ Your email is not registered in the OIS Users sheet.")
        st.stop()

    user_row = match.iloc[0]
    role = user_row.get("Role", "user").lower()
    name = user_row.get("Name", email)

    # Save in session_state (so main.py can pick it up)
    st.session_state.auth_email = email
    st.session_state.auth_name = name
    st.session_state.auth_role = role

    st.success(f"✅ Welcome {name} ({role}) — redirecting…")

    # 🔄 Jump to main.py automatically
    st.switch_page("main.py")

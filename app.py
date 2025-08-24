# login.py
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

# Google OAuth client info (from Google Cloud Console)
CLIENT_ID = st.secrets["oauth"]["client_id"]
CLIENT_SECRET = st.secrets["oauth"]["client_secret"]
REDIRECT_URI = st.secrets["oauth"]["redirect_uri"]  # e.g. https://your-app.streamlit.app

# =========================
# Connect to Users Sheet
# =========================
def get_users_df():
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(SPREADSHEET_ID).worksheet("Users")
    df = pd.DataFrame(ws.get_all_records())
    return df

users_df = get_users_df()

# =========================
# Google Sign-In
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
    # Fetch user info
    token = st.session_state.token
    user_info = oauth2.get_user_info(token)
    email = user_info.get("email", "").lower()

    st.success(f"✅ Logged in as {email}")

    # Check role in Users sheet
    match = users_df[users_df["Email"].str.lower() == email]
    if match.empty:
        st.error("❌ Your email is not registered in the OIS Users sheet.")
    else:
        role = match.iloc[0]["Role"].lower()
        name = match.iloc[0]["Name"]

        st.info(f"Welcome **{name}** ({role})")

        if role == "user":
            st.page_link("app.py", label="Go to Self-Assessment", icon="📝")
        elif role == "admin":
            st.page_link("app.py", label="Go to Admin Panel", icon="👩‍💼")
        elif role == "sadmin":
            st.page_link("app.py", label="Go to Super Admin Dashboard", icon="🏫")

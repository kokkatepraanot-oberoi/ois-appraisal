import streamlit as st
from authlib.integrations.requests_client import OAuth2Session
import requests
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="OIS Teacher Appraisal Login", layout="centered", initial_sidebar_state="collapsed")

# =========================
# CONFIG
# =========================
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CLIENT_ID = st.secrets["oauth"]["client_id"]
CLIENT_SECRET = st.secrets["oauth"]["client_secret"]
REDIRECT_URI = st.secrets["oauth"]["redirect_uri"]

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

# =========================
# Google Sheets: load Users
# =========================
def get_users_df():
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(SPREADSHEET_ID).worksheet("Users")
    return pd.DataFrame(ws.get_all_records())

users_df = get_users_df()

# =========================
# OAuth setup
# =========================
oauth = OAuth2Session(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scope="openid email profile",
    redirect_uri=REDIRECT_URI,
)

st.set_page_config(page_title="OIS Login", layout="centered")
st.title("🔐 OIS Teacher Appraisal Login")

# =========================
# 1. If token already exists in session → reuse it
# =========================
if "token" in st.session_state and st.session_state["token"]:
    token = st.session_state["token"]
    resp = requests.get(USERINFO_ENDPOINT, headers={"Authorization": f"Bearer {token['access_token']}"})
    if resp.status_code == 200:
        user_info = resp.json()
        email = user_info["email"].lower()

        # Lookup in Users sheet
        match = users_df[users_df["Email"].str.lower() == email]
        if match.empty:
            st.error("❌ Your email is not registered in the OIS Users sheet.")
            st.stop()

        row = match.iloc[0]
        role = row.get("Role", "user").lower()
        name = row.get("Name", email)

        # Save session vars for main.py
        st.session_state.auth_email = email
        st.session_state.auth_name = name
        st.session_state.auth_role = role

        st.success(f"✅ Welcome {name} ({role}) — redirecting…")
        st.switch_page("main.py")



    else:
        st.warning("⚠️ Session expired, please log in again.")
        del st.session_state["token"]
        st.rerun()

# =========================
# 2. If callback from Google has ?code= → exchange for token
# =========================
elif "code" in st.experimental_get_query_params():
    code = st.experimental_get_query_params()["code"][0]
    try:
        token = oauth.fetch_token(
            TOKEN_URL,
            code=code,
            grant_type="authorization_code",
        )
        st.session_state["token"] = token
        st.rerun()
    except Exception as e:
        st.error(f"Login failed: {e}")

# =========================
# 3. Otherwise → show login button
# =========================
else:
    auth_url, state = oauth.create_authorization_url(AUTHORIZE_URL)
    st.markdown(f"[👉 Login with Google]({auth_url})")

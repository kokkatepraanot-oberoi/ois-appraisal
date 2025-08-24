import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from authlib.integrations.requests_client import OAuth2Session

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
# OAuth setup
# =========================
authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
token_url = "https://oauth2.googleapis.com/token"
userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"

oauth = OAuth2Session(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scope="openid email profile",
    redirect_uri=REDIRECT_URI,
)

# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="OIS Login", layout="centered")
st.title("🔐 OIS Teacher Appraisal Login")

# ---- 1. If token already stored, skip login
if "token" in st.session_state and st.session_state["token"]:
    token = st.session_state["token"]
    try:
        resp = oauth.get(userinfo_endpoint, token=token)
        user_info = resp.json()
        email = user_info.get("email", "").lower()

        # Verify against Users sheet
        match = users_df[users_df["Email"].str.lower() == email]
        if match.empty:
            st.error("❌ Your email is not registered in the OIS Users sheet.")
            st.stop()

        user_row = match.iloc[0]
        role = user_row.get("Role", "user").lower()
        name = user_row.get("Name", email)

        # Save in session_state for use in main.py
        st.session_state.auth_email = email
        st.session_state.auth_name = name
        st.session_state.auth_role = role

        st.success(f"✅ Welcome back {name} ({role}) — redirecting…")
        st.switch_page("main.py")

    except Exception as e:
        st.warning("⚠️ Session expired, please log in again.")
        del st.session_state["token"]
        st.rerun()

# ---- 2. If token not yet stored, show login link
else:
    auth_url, state = oauth.create_authorization_url(authorize_url)
    st.markdown(f"[Login with Google]({auth_url})")

    # Step 2a: Handle callback (Google redirects with ?code=... in URL)
    query_params = st.experimental_get_query_params()
    if "code" in query_params:
        code = query_params["code"][0]
        try:
            token = oauth.fetch_token(token_url, code=code)
            st.session_state["token"] = token  # persist!
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")

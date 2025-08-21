import streamlit as st
from streamlit_oauth import OAuth2Component
import jwt

st.title("🔐 Google Login Test")

# --- Read secrets ---
try:
    client_id = st.secrets["google_oauth"]["client_id"]
    client_secret = st.secrets["google_oauth"]["client_secret"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
except Exception as e:
    st.error("⚠️ Missing google_oauth config in st.secrets")
    st.stop()

# --- Setup OAuth component ---
oauth2 = OAuth2Component(
    client_id=client_id,
    client_secret=client_secret,
    auth_url="https://accounts.google.com/o/oauth2/auth",
    token_url="https://oauth2.googleapis.com/token",
)

token = oauth2.authorize_button(
    name="Login with Google",
    icon="🔒",
    redirect_uri=redirect_uri,
    scope=["openid", "email", "profile"],
    key="google",
    extras_params={
        "access_type": "offline",   # get refresh token
        "prompt": "consent"         # force refresh token on first login
    }
)

# --- Handle token ---
if token:
    st.success("✅ Login successful!")
    id_token = token.get("id_token")

    if id_token:
        user_info = jwt.decode(id_token, options={"verify_signature": False})
        st.write("👤 User info from Google ID token:", user_info)
    else:
        st.error("No ID token returned.")

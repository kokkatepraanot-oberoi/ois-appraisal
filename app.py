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

from authlib.integrations.requests_client import OAuth2Session

def google_login():
    client_id = st.secrets["google_oauth"]["client_id"]
    client_secret = st.secrets["google_oauth"]["client_secret"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]

    oauth = OAuth2Session(client_id, client_secret, scope="openid email profile", redirect_uri=redirect_uri)

    if "code" not in st.query_params:
        auth_url, state = oauth.create_authorization_url("https://accounts.google.com/o/oauth2/auth",
                                                         access_type="offline", prompt="consent")
        st.markdown(f"[Login with Google]({auth_url})")
        return None
    else:
        token = oauth.fetch_token(
            "https://oauth2.googleapis.com/token",
            authorization_response=st.query_params["code"],
            grant_type="authorization_code"
        )
        from jwt import decode
        user_info = decode(token["id_token"], options={"verify_signature": False})
        return user_info

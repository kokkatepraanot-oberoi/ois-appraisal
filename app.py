from authlib.integrations.requests_client import OAuth2Session
import streamlit as st
import os
import jwt  # from PyJWT

# Load secrets
client_id = st.secrets["google_oauth"]["client_id"]
client_secret = st.secrets["google_oauth"]["client_secret"]
redirect_uri = st.secrets["google_oauth"]["redirect_uri"]

# Google OAuth endpoints
auth_url = "https://accounts.google.com/o/oauth2/auth"
token_url = "https://oauth2.googleapis.com/token"

if "token" not in st.session_state:
    # Build OAuth2 session
    oauth = OAuth2Session(
        client_id,
        client_secret,
        scope="openid email profile",
        redirect_uri=redirect_uri
    )

    # Step 1: Redirect to Google login
    authorization_url, state = oauth.create_authorization_url(auth_url)
    st.markdown(f"[Login with Google]({authorization_url})")

    # Step 2: Once redirected back, capture `code`
    query_params = st.experimental_get_query_params()
    if "code" in query_params:
        code = query_params["code"][0]
        token = oauth.fetch_token(
            token_url,
            code=code
        )
        st.session_state["token"] = token
        st.experimental_rerun()

else:
    token = st.session_state["token"]
    id_token = token.get("id_token")

    if id_token:
        user_info = jwt.decode(id_token, options={"verify_signature": False})
        st.success(f"✅ Logged in as {user_info['email']}")

import streamlit as st
import gspread

# Load secrets
admins = st.secrets["admins"]

# Connect to Google Sheets
gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
sh = gc.open_by_key(st.secrets["spreadsheet_id"])
users_ws = sh.worksheet("Users")

def login(email):
    email = email.strip().lower()

    # ✅ Check if email is admin
    if email in admins:
        st.session_state["user"] = email
        st.session_state["role"] = "admin"
        return True

    # ✅ Otherwise check Users sheet
    try:
        users = users_ws.col_values(1)  # Assuming column A has emails
        if email in [u.strip().lower() for u in users]:
            st.session_state["user"] = email
            st.session_state["role"] = "teacher"
            return True
    except Exception as e:
        st.error(f"Error accessing Users sheet: {e}")
        return False

    return False

# --- UI ---
st.header("Account")
email_input = st.text_input("School email (e.g., firstname.lastname@oberoi-is.org)")
if st.button("Login"):
    if login(email_input):
        st.success(f"Welcome {st.session_state['role'].capitalize()}!")
    else:
        st.error("Email not found in Users sheet or Admin list.")

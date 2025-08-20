import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime

# --- Google Sheets Setup ---
SHEET_NAME = "OIS Self Assessment Responses 2025-26"
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
RESPONSES_TAB = "Responses"
USERS_TAB = "Users"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

sheet = client.open_by_key(SPREADSHEET_ID)
responses_ws = sheet.worksheet(RESPONSES_TAB)
users_ws = sheet.worksheet(USERS_TAB)

# Load data
users_df = pd.DataFrame(users_ws.get_all_records())
responses_df = pd.DataFrame(responses_ws.get_all_records())

# --- Define Sub-strands ---
domains = {
    "Domain A: Planning": ["Expertise", "Curriculum", "Assessment", "Growth"],
    "Domain B: Teaching": ["Instruction", "Engagement", "Differentiation", "Feedback"],
    "Domain C: Learning": ["Environment", "Support", "Inquiry", "Growth"],
    "Domain D: Professionalism": ["Ethics", "Collaboration", "Leadership", "Reflection"],
    "Domain E: Contribution": ["Community", "Innovation", "Service"],
    "Domain F: Growth": ["Development", "Adaptability", "Lifelong Learning"]
}

choices = ["Highly Effective", "Effective", "Improvement Necessary", "Does Not Meet Standards"]

# --- Ensure Headers in Responses sheet ---
expected_headers = ["Timestamp", "Email", "Name"] + [
    f"{domain} - {strand}" for domain, strands in domains.items() for strand in strands
]

existing_headers = responses_ws.row_values(1)
if not existing_headers or existing_headers != expected_headers:
    responses_ws.clear()
    responses_ws.insert_row(expected_headers, 1)

# --- App Mode Switcher ---
mode = st.sidebar.radio("Choose Mode:", ["Self Assessment", "Admin Dashboard"])

# ---------------- SELF ASSESSMENT ---------------- #
if mode == "Self Assessment":
    st.title("OIS Teacher Self Assessment")

    email = st.text_input("Enter your school email address:")
    ratings = {}

    progress_total = sum(len(s) for s in domains.values())
    completed = 0

    if email:
        st.write(f"Welcome: **{email}**")

        for domain, strands in domains.items():
            st.header(domain)
            for strand in strands:
                rating = st.radio(
                    f"{strand}",
                    choices,
                    index=None,  # no default selection
                    key=f"{domain}_{strand}"
                )
                ratings[f"{domain} - {strand}"] = rating
                if rating:
                    completed += 1

        # Progress bar
        st.subheader("Progress")
        st.progress(completed / progress_total)
        st.write(f"{completed}/{progress_total} sub-strands completed ({(completed/progress_total)*100:.1f}%)")

        if st.button("Submit"):
            email_to_name = {row["Email"].strip().lower(): row["Name"] for _, row in users_df.iterrows()}
            name = email_to_name.get(email.strip().lower(), "Unknown")

            row = [
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                email,
                name
            ] + [ratings[col] if ratings[col] else "" for col in expected_headers[3:]]
            responses_ws.append_row(row)
            st.success("✅ Your response has been recorded!")

# ---------------- ADMIN DASHBOARD ---------------- #
elif mode == "Admin Dashboard":
    st.title("OIS Self Assessment - Admin Dashboard")

    st.subheader("🔑 Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if username and password:
        admins = st.secrets["admins"]  # stored securely in secrets.toml
        if username in admins and password == admins[username]:
            st.success(f"✅ Welcome {username}")

            # --- Super Admin (Paul) sees ALL teachers ---
            if username.lower() == "paul":
                assigned_teachers = users_df
                st.info("Super Admin Access: Viewing ALL teachers")
            else:
                assigned_teachers = users_df[users_df["Appraiser"].str.lower() == username.lower()]

            if assigned_teachers.empty:
                st.warning("⚠️ No teachers assigned yet.")
            else:
                teacher = st.selectbox("Select a teacher:", assigned_teachers["Name"])

                if teacher:
                    teacher_email = assigned_teachers[assigned_teachers["Name"] == teacher]["Email"].values[0]
                    teacher_responses = responses_df[responses_df["Email"].str.lower() == teacher_email.lower()]

                    if teacher_responses.empty:
                        st.info("No self-assessment submitted yet.")
                    else:
                        st.subheader(f"📊 Results for {teacher}")
                        st.dataframe(teacher_responses)

                        # Quick summary
                        st.subheader("Summary of Ratings")
                        summary = teacher_responses.iloc[:, 3:].T.value_counts().reset_index()
                        summary.columns = ["Rating", "Count"]
                        st.write(summary)

                        # Download button
                        st.download_button(
                            "⬇️ Download Teacher Report",
                            teacher_responses.to_csv(index=False).encode("utf-8"),
                            f"{teacher}_self_assessment.csv",
                            "text/csv"
                        )
        else:
            st.error("❌ Invalid username or password")

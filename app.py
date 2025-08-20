import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
from io import BytesIO

# --------------------------
# GOOGLE SHEETS CONNECTION
# --------------------------
@st.cache_resource
def connect_to_gsheet():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    try:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scope
        )
    except KeyError:
        st.error("⚠️ Missing [gcp_service_account] in Streamlit secrets. Please set it in your app settings.")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Failed to load service account credentials: {e}")
        st.stop()

    client = gspread.authorize(creds)
    sh = client.open_by_key(SPREADSHEET_ID)
    return sh
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["spreadsheet_id"])

# --------------------------
# DOMAIN MAPPING
# --------------------------
DOMAINS = {
    "A": "Professional Knowledge",
    "B": "Instructional Planning",
    "C": "Classroom Environment",
    "D": "Instruction",
    "E": "Assessment",
    "F": "Professional Responsibilities",
}

# --------------------------
# PDF GENERATOR
# --------------------------
def generate_pdf(user_df, user_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)

    # Title
    pdf.cell(200, 10, "OIS Teacher Self-Assessment 2025-26", ln=True, align="C")
    pdf.ln(10)

    # Teacher Name
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, f"Teacher: {user_name}", ln=True)
    pdf.ln(5)

    # Start grouped sections
    pdf.set_font("Arial", '', 11)
    for col in user_df.columns:
        if col in ["Timestamp", "Email", "Name", "Appraiser"]:
            continue  # Skip metadata

        # Detect domain prefix (A1, B3, etc.)
        prefix = col[0]
        if prefix in DOMAINS:
            # Add section header if first time in domain
            if not hasattr(generate_pdf, "last_domain") or generate_pdf.last_domain != prefix:
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 13)
                pdf.set_text_color(0, 51, 102)  # dark blue for headers
                pdf.cell(0, 8, f"Domain {prefix}: {DOMAINS[prefix]}", ln=True)
                pdf.set_font("Arial", '', 11)
                pdf.set_text_color(0, 0, 0)
                generate_pdf.last_domain = prefix

        # Write question + response
        value = str(user_df[col].values[0])
        pdf.set_font("Arial", 'B', 11)
        pdf.multi_cell(0, 8, f"{col}:", border=0)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 8, f"{value}", border=0)

    # Reset domain tracker
    generate_pdf.last_domain = None

    # Output as BytesIO
    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

# --------------------------
# APP LAYOUT
# --------------------------
st.sidebar.title("Account")

if "user_name" not in st.session_state:
    st.session_state["user_name"] = "Praanot Kokkate"  # temp login simulation
if "user_email" not in st.session_state:
    st.session_state["user_email"] = "praanot.kokkate@oberoi-is.org"

st.sidebar.success(f"Logged in as {st.session_state['user_name']}")

menu = st.sidebar.radio("Menu", ["My Submission"])

if menu == "My Submission":
    st.header("📄 My Submission")

    sh = connect_to_gsheet()
    worksheet = sh.worksheet("Form Responses 1")
    df = pd.DataFrame(worksheet.get_all_records())

    if df.empty:
        st.info("No submissions yet.")
    else:
        user_df = df[df["Email"].str.strip().str.lower() ==
                     st.session_state["user_email"].strip().lower()]

        if not user_df.empty:
            st.success("Here is your submitted self-assessment:")

            # Show table
            st.dataframe(user_df.T.rename(columns={user_df.index[0]: "Response"}))

            # CSV Download
            csv = user_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download My Submission (CSV)",
                data=csv,
                file_name=f"{st.session_state['user_name']}_self_assessment.csv",
                mime="text/csv",
            )

            # PDF Download
            pdf_buffer = generate_pdf(user_df, st.session_state["user_name"])
            st.download_button(
                label="📑 Download My Submission (PDF)",
                data=pdf_buffer,
                file_name=f"{st.session_state['user_name']}_self_assessment.pdf",
                mime="application/pdf",
            )

        else:
            st.warning("No submission found for your account.")

import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from fpdf import FPDF

# -----------------------------
# Google Sheets Connection
# -----------------------------
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def connect_to_gsheet():
    creds = Credentials.from_service_account_info(
        st.secrets["google"], scopes=SCOPE
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(st.secrets["SPREADSHEET_ID"])  # stored in secrets
    return sh

# -----------------------------
# PDF Export Function
# -----------------------------
def generate_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, "OIS Appraisal - Summary Report", ln=True, align="C")
    pdf.ln(10)

    # Group by Teacher
    grouped = df.groupby("Teacher")

    for teacher, group in grouped:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, f"Teacher: {teacher}", ln=True)
        pdf.set_font("Arial", size=10)

        for i, row in group.iterrows():
            row_text = ", ".join([f"{col}: {row[col]}" for col in group.columns])
            pdf.multi_cell(0, 8, row_text)
            pdf.ln(2)

        pdf.ln(5)

    return pdf

# -----------------------------
# App Layout
# -----------------------------
st.set_page_config(page_title="OIS Appraisal", layout="wide")

st.title("📊 OIS Appraisal")

# Sidebar Menu
menu = st.sidebar.radio("Navigation", ["Home", "View Responses", "Admin Dashboard", "Generate PDF"])

# -----------------------------
# Load Data
# -----------------------------
try:
    sh = connect_to_gsheet()
    worksheet = sh.sheet1
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error(f"⚠️ Could not connect to Google Sheets: {e}")
    st.stop()

# -----------------------------
# Home
# -----------------------------
if menu == "Home":
    st.success("✅ Connected to Google Sheets successfully!")
    st.write(f"Spreadsheet title: **{sh.title}**")
    st.write("Use the sidebar to navigate between options.")

# -----------------------------
# View Responses
# -----------------------------
elif menu == "View Responses":
    st.subheader("All Responses")
    st.dataframe(df)

    st.subheader("Responses Grouped by Teacher")
    if "Teacher" in df.columns:
        for teacher, group in df.groupby("Teacher"):
            st.markdown(f"### 👩‍🏫 {teacher}")
            st.dataframe(group)
    else:
        st.warning("No 'Teacher' column found in the sheet.")

# -----------------------------
# Admin Dashboard
# -----------------------------
elif menu == "Admin Dashboard":
    st.subheader("🔑 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "roma123":
            st.success("✅ Login successful!")
            st.subheader("📌 Admin Panel")
            st.write("Here admins can view submissions and generate reports.")

            st.dataframe(df)

            st.subheader("Summary by Teacher")
            if "Teacher" in df.columns:
                st.table(df.groupby("Teacher").size())
        else:
            st.error("❌ Invalid username or password.")

# -----------------------------
# Generate PDF
# -----------------------------
elif menu == "Generate PDF":
    st.subheader("📄 Generate PDF Report")

    if st.button("Create PDF"):
        pdf = generate_pdf(df)
        pdf.output("ois_appraisal_report.pdf")

        with open("ois_appraisal_report.pdf", "rb") as f:
            st.download_button(
                "⬇️ Download Report",
                f,
                file_name="ois_appraisal_report.pdf",
                mime="application/pdf"
            )

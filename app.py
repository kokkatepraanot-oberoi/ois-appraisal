
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF

# --------------------
# GOOGLE SHEETS SETUP
# --------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["google"], scope
)

client = gspread.authorize(creds)

SPREADSHEET_ID = "1kqcfmMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
sheet = client.open_by_key(st.secrets["SPREADSHEET_ID"]).sheet1


# --------------------
# STREAMLIT UI SETUP
# --------------------
st.set_page_config(page_title="OIS Appraisal System", layout="wide")

# Sidebar Menu
menu = ["Submit Response", "Admin Dashboard"]
choice = st.sidebar.selectbox("Menu", menu)

# --------------------
# USER SUBMISSION PAGE
# --------------------
if choice == "Submit Response":
    st.title("Teacher Appraisal Form")

    teacher_name = st.text_input("Your Name")
    domain = st.selectbox("Domain", ["A. Professional Knowledge", "B. Instructional Planning", "C. Classroom Environment", "D. Instructional Delivery", "E. Professional Responsibilities"])
    rating = st.slider("Rating (1–5)", 1, 5)
    comments = st.text_area("Comments")

    if st.button("Submit"):
        sheet.append_row([teacher_name, domain, rating, comments])
        st.success("✅ Response submitted successfully!")

# --------------------
# ADMIN DASHBOARD
# --------------------
elif choice == "Admin Dashboard":
    st.title("🔐 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if username == "admin" and password == "roma123":
        st.success("Welcome Admin!")
        st.subheader("📊 Appraisal Summary")

        # Load data from Google Sheet
        data = pd.DataFrame(sheet.get_all_records())

        if not data.empty:
            # Group by Teacher
            grouped = data.groupby("Your Name").agg({"Rating (1–5)": "mean"}).reset_index()
            st.dataframe(grouped)

            # Show full data
            st.subheader("All Responses")
            st.dataframe(data)

            # PDF Export
            def generate_pdf(df):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="Appraisal Summary Report", ln=True, align="C")

                for i, row in df.iterrows():
                    pdf.cell(200, 10, txt=f"{row['Your Name']} | {row['Domain']} | {row['Rating (1–5)']} | {row['Comments']}", ln=True)

                return pdf.output(dest="S").encode("latin1")

            if st.button("Download PDF Report"):
                pdf_bytes = generate_pdf(data)
                st.download_button("📥 Download PDF", pdf_bytes, file_name="appraisal_summary.pdf", mime="application/pdf")

        else:
            st.warning("No data found in the sheet.")

    else:
        st.info("Enter admin credentials to access the dashboard.")

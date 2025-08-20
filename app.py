
import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import datetime

# ----------------------------
# GOOGLE SHEETS SETUP
# ----------------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google.json", scope)
client = gspread.authorize(creds)

# Replace with your own Google Sheet ID
SHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
USERS_SHEET = "Users"
RESPONSES_SHEET = "Responses"

# ----------------------------
# APP STATE & SESSION INIT
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

# ----------------------------
# PDF GENERATION
# ----------------------------
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Appraisal Report", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_teacher_pdf(df, teacher_name):
    pdf = PDF()
    pdf.add_page()

    # Cover Page
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 10, "OIS Appraisal Report", ln=True, align="C")
    pdf.ln(20)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Teacher: {teacher_name}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.add_page()

    # Responses Table
    pdf.set_font("Arial", "B", 12)
    col_width = pdf.w / (len(df.columns) + 1)
    row_height = pdf.font_size * 1.5

    for col in df.columns:
        pdf.cell(col_width, row_height, str(col), border=1, align="C")
    pdf.ln(row_height)

    pdf.set_font("Arial", "", 11)
    for i in range(len(df)):
        for col in df.columns:
            pdf.cell(col_width, row_height, str(df.iloc[i][col]), border=1)
        pdf.ln(row_height)

    return pdf.output(dest="S").encode("latin-1")

def generate_admin_pdf(df):
    pdf = PDF()
    pdf.add_page()

    # Cover Page
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 10, "OIS Appraisal - Full Report", ln=True, align="C")
    pdf.ln(20)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.add_page()

    # All responses table
    pdf.set_font("Arial", "B", 12)
    col_width = pdf.w / (len(df.columns) + 1)
    row_height = pdf.font_size * 1.5
    for col in df.columns:
        pdf.cell(col_width, row_height, str(col), border=1, align="C")
    pdf.ln(row_height)

    pdf.set_font("Arial", "", 11)
    for i in range(len(df)):
        for col in df.columns:
            pdf.cell(col_width, row_height, str(df.iloc[i][col]), border=1)
        pdf.ln(row_height)

    # Grouped by Teacher
    for teacher, group in df.groupby("Teacher"):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Teacher: {teacher}", ln=True, align="L")
        pdf.ln(5)

        pdf.set_font("Arial", "B", 12)
        for col in group.columns:
            pdf.cell(col_width, row_height, str(col), border=1, align="C")
        pdf.ln(row_height)

        pdf.set_font("Arial", "", 11)
        for i in range(len(group)):
            for col in group.columns:
                pdf.cell(col_width, row_height, str(group.iloc[i][col]), border=1)
            pdf.ln(row_height)

    return pdf.output(dest="S").encode("latin-1")

# ----------------------------
# LOGIN SYSTEM
# ----------------------------
def login(username, password):
    # Admins
    admins = {
        "roma": "roma123",
        "praanot": "roma123",
        "kirandeep": "roma123",
        "manjula": "roma123",
        "drpaul": "roma123"
    }
    if username.lower() in admins and password == admins[username.lower()]:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = "admin"
        return True

    # Teachers from Users sheet
    users_ws = client.open_by_key(SHEET_ID).worksheet(USERS_SHEET)
    users = users_ws.get_all_records()
    for u in users:
        if u["Username"].lower() == username.lower() and u["Password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = "teacher"
            return True

    return False

# ----------------------------
# MAIN APP
# ----------------------------
st.sidebar.title("📊 OIS Appraisal System")

if not st.session_state.logged_in:
    st.sidebar.subheader("Login")
    uname = st.sidebar.text_input("Username")
    pwd = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if not login(uname, pwd):
            st.sidebar.error("Invalid credentials")

else:
    menu = st.sidebar.radio("Navigation", ["Home", "Self Assessment", "My Submission", "Admin Panel", "Logout"])

    if menu == "Home":
        st.title("Welcome to the OIS Appraisal System")
        st.write(f"Hello **{st.session_state.username}**! Use the sidebar to navigate.")

    elif menu == "Self Assessment":
        if st.session_state.role == "teacher":
            responses_ws = client.open_by_key(SHEET_ID).worksheet(RESPONSES_SHEET)
            df = pd.DataFrame(responses_ws.get_all_records())

            if df.empty or st.session_state.username not in df["Teacher"].values:
                st.subheader("Fill Self Assessment")
                q1 = st.radio("A. Professional Knowledge", ["1", "2", "3", "4", "5"])
                q2 = st.radio("B. Instructional Planning", ["1", "2", "3", "4", "5"])
                q3 = st.radio("C. Classroom Environment", ["1", "2", "3", "4", "5"])
                comments = st.text_area("Additional Comments")
                if st.button("Submit"):
                    new_row = [st.session_state.username, q1, q2, q3, comments, str(datetime.datetime.now())]
                    responses_ws.append_row(new_row)
                    st.success("Submitted successfully!")
            else:
                st.info("You have already submitted your self-assessment.")

    elif menu == "My Submission":
        if st.session_state.role == "teacher":
            responses_ws = client.open_by_key(SHEET_ID).worksheet(RESPONSES_SHEET)
            df = pd.DataFrame(responses_ws.get_all_records())
            my_df = df[df["Teacher"].str.lower() == st.session_state.username.lower()]
            if not my_df.empty:
                st.subheader("My Submission")
                st.dataframe(my_df)
                pdf_bytes = generate_teacher_pdf(my_df, st.session_state.username)
                st.download_button("📥 Download My Report (PDF)", data=pdf_bytes, file_name="my_report.pdf")
            else:
                st.info("No submission found.")

    elif menu == "Admin Panel":
        if st.session_state.role == "admin":
            st.subheader("Admin Panel - All Submissions")
            responses_ws = client.open_by_key(SHEET_ID).worksheet(RESPONSES_SHEET)
            df = pd.DataFrame(responses_ws.get_all_records())
            if not df.empty:
                st.dataframe(df)
                pdf_bytes = generate_admin_pdf(df)
                st.download_button("📥 Download Full Report (PDF)", data=pdf_bytes, file_name="all_reports.pdf")
            else:
                st.info("No submissions yet.")

    elif menu == "Logout":
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.experimental_rerun()

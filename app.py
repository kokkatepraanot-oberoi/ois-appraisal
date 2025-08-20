import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="OIS Teacher Appraisal", layout="wide")

# ---- Google Sheets Setup ----
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)

# Replace this with your actual Google Sheet name
SHEET_NAME = "OIS Self Assessment Responses 2025-26"
sheet = client.open(SHEET_NAME).sheet1

# ---- Login ----
st.sidebar.header("Login")
user_email = st.sidebar.text_input("Enter your school email (@oberoi-is.org):")

if not user_email:
    st.warning("Please enter your email to continue")
    st.stop()

st.success(f"Welcome {user_email}!")

# ---- Domain A ----
st.header("Domain A: Planning & Preparation")
ratings = ["Highly Effective", "Effective", "Improvement Necessary", "Does Not Meet Standards"]

expertise = st.radio("A - Expertise", ratings, key="A_expertise")
goals = st.radio("A - Goals", ratings, key="A_goals")
units = st.radio("A - Units", ratings, key="A_units")
domain_a_reflection = st.text_area("Domain A Reflection")

# ---- Submit ----
if st.button("Submit Self-Assessment"):
    data = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_email,
        expertise,
        goals,
        units,
        domain_a_reflection
    ]
    sheet.append_row(data)
    st.success("✅ Your self-assessment has been saved to Google Sheets!")

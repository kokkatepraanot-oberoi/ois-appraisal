import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="OIS Teacher Self-Assessment 2025-26", layout="wide")

# ---- Google Sheets Setup ----
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)

SHEET_NAME = "OIS Self Assessment Responses 2025-26"
sheet = client.open(SHEET_NAME).sheet1

# ---- Login ----
st.sidebar.header("Login")
user_email = st.sidebar.text_input("Enter your school email (@oberoi-is.org):")

if not user_email:
    st.warning("Please enter your email to continue")
    st.stop()

st.success(f"Welcome {user_email}!")

ratings = ["Highly Effective", "Effective", "Improvement Necessary", "Does Not Meet Standards"]

# ---- Domain structure ----
domains = {
    "A: Planning & Preparation": [
        "Expertise","Goals","Units","Assessments","Anticipation",
        "Lessons","Materials","Differentiation","Environment"
    ],
    "B: Classroom Management": [
        "Expectations","Relationships","Social Emotional","Routines",
        "Responsibility","Repertoire","Prevention","Incentives"
    ],
    "C: Delivery of Instruction": [
        "Expectations","Mindset","Framing","Connections","Clarity",
        "Repertoire","Engagement","Differentiation","Nimbleness"
    ],
    "D: Monitoring, Assessment & Follow-Up": [
        "Criteria","Diagnosis","Goals","Feedback","Recognition",
        "Analysis","Tenacity","Support","Reflection"
    ],
    "E: Family & Community Outreach": [
        "Respect","Belief","Expectations","Communication","Involving",
        "Responsiveness","Reporting","Outreach","Resources"
    ],
    "F: Professional Responsibility": [
        "Language","Reliability","Professionalism","Judgement",
        "Teamwork","Leadership","Openness","Collaboration","Growth"
    ]
}

responses = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User": user_email}

# ---- Loop over Domains ----
for domain, substrands in domains.items():
    with st.expander(domain, expanded=True):
        st.markdown(f"## {domain}")  # Big domain header
        for sub in substrands:
            st.markdown(f"**{sub}**")   # Make sub-strand bold & bigger
            responses[f"{domain.split(':')[0]}_{sub}"] = st.radio(
                "Select rating:", ratings, key=f"{domain}_{sub}", horizontal=True
            )
        # Optional reflection
        responses[f"{domain.split(':')[0]}_Reflection"] = st.text_area(
            f"{domain} Reflection (optional)", key=f"{domain}_reflection"
        )

# ---- Overall reflection ----
st.markdown("## Overall Reflection")
responses["Overall_Reflection"] = st.text_area("Summarize key strengths, growth areas, and initial goal ideas (optional).")

# ---- Submit ----
if st.button("Submit Self-Assessment"):
    # Convert dict to row
    data = [responses.get(col, "") for col in responses.keys()]
    # Append header if sheet empty
    if len(sheet.get_all_values()) == 0:
        sheet.append_row(list(responses.keys()))
    sheet.append_row(data)
    st.success("✅ Your self-assessment has been saved to Google Sheets!")

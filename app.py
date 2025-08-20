import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="OIS Teacher Appraisal", layout="wide")

# ---- Simulated login ----
st.sidebar.header("Login")
user_email = st.sidebar.text_input("Enter your school email (@oberoi-is.org):")

if not user_email:
    st.warning("Please enter your email to continue")
    st.stop()

st.success(f"Welcome {user_email}!")

# ---- Domain A Example ----
st.header("Domain A: Planning & Preparation")
ratings = ["Highly Effective", "Effective", "Improvement Necessary", "Does Not Meet Standards"]

expertise = st.radio("A - Expertise", ratings, key="A_expertise")
goals = st.radio("A - Goals", ratings, key="A_goals")
units = st.radio("A - Units", ratings, key="A_units")
domain_a_reflection = st.text_area("Domain A Reflection")

# ---- Submit ----
if st.button("Submit Self-Assessment"):
    data = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "User": user_email,
        "A_Expertise": expertise,
        "A_Goals": goals,
        "A_Units": units,
        "A_Reflection": domain_a_reflection,
    }

    # Save to CSV locally (Streamlit Cloud will create a file)
    df = pd.DataFrame([data])
    df.to_csv("responses.csv", mode="a", header=not pd.io.common.file_exists("responses.csv"), index=False)

    st.success("✅ Your self-assessment has been saved!")

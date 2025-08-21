
# app.py
import time
from datetime import datetime

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Try to import HttpError; fall back gracefully if googleapiclient isn't present
try:
    from googleapiclient.errors import HttpError  # type: ignore
except Exception:  # pragma: no cover
    class HttpError(Exception):
        pass

# =========================
# RERUN helper (Streamlit API changed)
# =========================
def _rerun():
    try:
        st.rerun()  # Streamlit >=1.32
    except AttributeError:
        st.experimental_rerun()  # Older versions

# =========================
# UI CONFIG (must be first)
# =========================
st.set_page_config(page_title="OIS Teacher Self‑Assessment", layout="wide")

# =========================
# CONFIG
# =========================
SPREADSHEET_ID = "1kqcfnMx4KhqQvFljsTwSOcmuEHnkLAdwp_pUJypOjpY"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
ENABLE_REFLECTIONS = True  # set False to hide reflection boxes

# Optional: list of admin emails (lowercase) in .streamlit/secrets.toml
ADMINS_FROM_SECRETS = set([e.strip().lower() for e in st.secrets.get("admins", [])])

# =========================
# DOMAINS & SUB-STRANDS (exact from rubric)
# =========================
DOMAINS = {
    "A: Planning and Preparation for Learning": [
        ("A1", "Expertise"),
        ("A2", "Goals"),
        ("A3", "Units"),
        ("A4", "Assessments"),
        ("A5", "Anticipation"),
        ("A6", "Lessons"),
        ("A7", "Materials"),
        ("A8", "Differentiation"),
        ("A9", "Environment"),
    ],
    "B: Classroom Management": [
        ("B1", "Expectations"),
        ("B2", "Relationships"),
        ("B3", "Social Emotional"),
        ("B4", "Routines"),
        ("B5", "Responsibility"),
        ("B6", "Repertoire"),
        ("B7", "Prevention"),
        ("B8", "Incentives"),
    ],
    "C: Delivery of Instruction": [
        ("C1", "Expectations"),
        ("C2", "Mindset"),
        ("C3", "Framing"),
        ("C4", "Connections"),
        ("C5", "Clarity"),
        ("C6", "Repertoire"),
        ("C7", "Engagement"),
        ("C8", "Differentiation"),
        ("C9", "Nimbleness"),
    ],
    "D: Monitoring, Assessment, and Follow-Up": [
        ("D1", "Criteria"),
        ("D2", "Diagnosis"),
        ("D3", "Goals"),
        ("D4", "Feedback"),
        ("D5", "Recognition"),
        ("D6", "Analysis"),
        ("D7", "Tenacity"),
        ("D8", "Support"),
        ("D9", "Reflection"),
    ],
    "E: Family and Community Outreach": [
        ("E1", "Respect"),
        ("E2", "Belief"),
        ("E3", "Expectations"),
        ("E4", "Communication"),
        ("E5", "Involving"),
        ("E6", "Responsiveness"),
        ("E7", "Reporting"),
        ("E8", "Outreach"),
        ("E9", "Resources"),
    ],
    "F: Professional Responsibility": [
        ("F1", "Language"),
        ("F2", "Reliability"),
        ("F3", "Professionalism"),
        ("F4", "Judgement"),
        ("F5", "Teamwork"),
        ("F6", "Leadership"),
        ("F7", "Openness"),
        ("F8", "Collaboration"),
        ("F9", "Growth"),
    ],
}

# Rating scale (exact rubric wording)
RATINGS = [
    "Highly Effective",
    "Effective",
    "Improvement Necessary",
    "Does Not Meet Standards",
]

# =========================
# Small retry/backoff for Sheets calls (handles 429/5xx)
# =========================
def with_backoff(fn, *args, **kwargs):
    """Retry gspread/api calls briefly on 429/5xx."""
    max_attempts = 5
    delay = 0.6  # seconds
    last_exc = None
    for _ in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except HttpError as e:  # googleapiclient
            status = getattr(e, "status_code", None)
            if status in (429, 500, 502, 503, 504):
                time.sleep(delay); delay *= 2; last_exc = e; continue
            raise
        except gspread.exceptions.APIError as e:  # gspread-wrapped
            msg = str(e).lower()
            if any(code in msg for code in ["429", "500", "502", "503", "504"]):
                time.sleep(delay); delay *= 2; last_exc = e; continue
            raise
        except Exception as e:
            time.sleep(delay); delay *= 2; last_exc = e; continue
    if last_exc:
        raise last_exc
    return fn(*args, **kwargs)

# =========================
# ONE-TIME SHEETS CONNECTION (cached)
# =========================
@st.cache_resource
# =========================
# Google Sheet Connections
# =========================
def get_worksheets():
    client = gspread.authorize(
        Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
    )
    sh = client.open_by_key(SPREADSHEET_ID)

    resp_ws = sh.worksheet("Responses")
    users_ws = sh.worksheet("Users")
    try:
        drafts_ws = sh.worksheet("Drafts")
    except gspread.exceptions.WorksheetNotFound:
        # Create if missing
        drafts_ws = sh.add_worksheet(title="Drafts", rows="1000", cols="100")
        drafts_ws.update([["Email"]])  # initialize header
    return resp_ws, users_ws, drafts_ws

RESP_WS, USERS_WS, DRAFTS_WS = get_worksheets()

# =========================
# DRAFT HELPERS
# =========================
def save_draft(email, form_data):
    """Update or append a draft for this teacher only."""
    try:
        # Get all drafts (lightweight, header + values)
        all_drafts = DRAFTS_WS.get_all_records()
        emails = [row["Email"] for row in all_drafts]

        row_data = [email] + [form_data.get(f, "") for f in form_data.keys()]

        if email in emails:
            # Update existing row (Google Sheets is 1-indexed and has a header row)
            row_num = emails.index(email) + 2  
            DRAFTS_WS.update(f"A{row_num}", [row_data])
        else:
            # Append new row
            if not all_drafts:  
                # If sheet is empty except header, add header first
                headers = ["Email"] + list(form_data.keys())
                DRAFTS_WS.append_row(headers, value_input_option="USER_ENTERED")
            DRAFTS_WS.append_row(row_data, value_input_option="USER_ENTERED")

        return True
    except Exception as e:
        st.error(f"⚠️ Could not save draft: {e}")
        return False


def load_draft(email):
    """Load teacher's draft if exists."""
    try:
        all_drafts = pd.DataFrame(DRAFTS_WS.get_all_records())
        user_draft = all_drafts[all_drafts["Email"] == email]
        if not user_draft.empty:
            return dict(user_draft.iloc[0])
    except Exception:
        return {}
    return {}

# =========================
# HEADER MANAGEMENT (safe, non-destructive)
# =========================
def expected_headers():
    headers = ["Timestamp", "Email", "Name", "Appraiser"]
    for domain, items in DOMAINS.items():
        for code, label in items:
            headers.append(f"{code} {label}")
        if ENABLE_REFLECTIONS:
            headers.append(f"{domain} Reflection")
    return headers

@st.cache_resource
def ensure_headers_once():
    exp = expected_headers()
    current = with_backoff(RESP_WS.row_values, 1)
    if not current:
        with_backoff(RESP_WS.insert_row, exp, 1)
        return True
    if current != exp:
        st.warning(
            "The existing header row in **Responses** does not match the current rubric. "
            "Submissions will still append, but columns may be misaligned if the rubric changed. "
            "To update safely, export data, fix headers offline, and re-import."
        )
    return True

ensure_headers_once()

# =========================
# USERS: read ONCE per server process (auto‑detect headers)
# =========================
def _pick_col(candidates: list[str], cols: list[str]):
    norm_map = {c.strip().lower(): c for c in cols}
    for want in candidates:
        key = want.strip().lower()
        if key in norm_map: return norm_map[key]
    for c in cols:
        cl = c.strip().lower()
        if any(w in cl for w in candidates): return c
    return None

@st.cache_resource
def load_users_once_df():
    records = with_backoff(USERS_WS.get_all_records)
    if not records:
        return pd.DataFrame(columns=["Email", "Name", "Appraiser", "Role", "Password"])
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["Email", "Name", "Appraiser", "Role", "Password"])

    cols = list(df.columns)

    email_header = _pick_col(["email","school email","work email","ois email","e-mail"], cols)
    name_header = _pick_col(["name","full name","teacher name","staff name"], cols)
    appraiser_header = _pick_col(["appraiser","line manager","manager","appraiser name","supervisor"], cols)
    role_header = _pick_col(["role","access","admin"], cols)
    password_header = _pick_col(["password","pwd","pass"], cols)   # 👈 NEW

    out = pd.DataFrame()
    out["Email"] = df[email_header].astype(str).str.strip().str.lower() if email_header else ""
    out["Name"] = df[name_header].astype(str).str.strip() if name_header else ""
    out["Appraiser"] = (df[appraiser_header].astype(str).str.strip().replace({"": "Not Assigned"})
                        if appraiser_header else "Not Assigned")
    out["Role"] = df[role_header].astype(str).str.strip().str.lower() if role_header else ""
    out["Password"] = df[password_header].astype(str).str.strip() if password_header else ""  # 👈 NEW

    return out


users_df = load_users_once_df()

# =========================
# RESPONSES cache (for 'My submission' and Admin)
# =========================
@st.cache_data(ttl=180)  # slightly longer to reduce bursts
def load_responses_df():
    vals = with_backoff(RESP_WS.get_all_values)
    if not vals:
        return pd.DataFrame()
    header, rows = vals[0], vals[1:]
    df = pd.DataFrame(rows, columns=header) if rows else pd.DataFrame(columns=header)
    # normalize
    if "Email" in df.columns:
        df["Email"] = df["Email"].astype(str).str.lower()
    return df

def user_has_submission(email: str) -> bool:
    if not email:
        return False
    df = load_responses_df()
    return (not df.empty) and ("Email" in df.columns) and (not df[df["Email"] == email.strip().lower()].empty)

# =========================
# Authentication & Roles
# =========================
def authenticate_user(email, password):
    email = email.strip().lower()

    # Look up in Users sheet
    user_row = users_df[users_df["Email"].str.lower() == email]
    if user_row.empty:
        return None, None  # not found

    role = user_row.iloc[0]["Role"].strip().lower()

    # Admin check
    if role == "admin":
        return ("admin", user_row.iloc[0]) if password == "OIS2025" else (None, None)

    # Superadmin check
    if role == "sadmin":
        return ("sadmin", user_row.iloc[0]) if password == "SOIS2025" else (None, None)

    # Teacher check — validate against Password column
    if role == "user":
        stored_pw = str(user_row.iloc[0].get("Password", "")).strip()
        entered_pw = str(password).strip()

        if stored_pw and entered_pw and stored_pw == entered_pw:
            return "user", user_row.iloc[0]
        else:
            st.warning(f"Debug → Entered: '{entered_pw}', Stored: '{stored_pw}'")
            return None, None


# =========================
# AUTH: Login / Logout
# =========================
if "auth_email" not in st.session_state:
    st.session_state.auth_email = ""
if "auth_name" not in st.session_state:
    st.session_state.auth_name = ""
if "auth_role" not in st.session_state:
    st.session_state.auth_role = ""
if "submitted" not in st.session_state:
    st.session_state.submitted = False

st.sidebar.header("Account")

if st.session_state.auth_email:
    st.sidebar.success(
        f"Logged in as **{st.session_state.auth_name or st.session_state.auth_email}** "
        f"({st.session_state.auth_role})"
    )
    if st.sidebar.button("Logout"):
        st.session_state.auth_email = ""
        st.session_state.auth_name = ""
        st.session_state.auth_role = ""
        st.session_state.submitted = False
        _rerun()
else:
    email_input = st.sidebar.text_input(
        "School email (e.g., firstname.lastname@oberoi-is.org)"
    ).strip().lower()
    password_input = st.sidebar.text_input(
        "Password (Admins/Super Admins only)", type="password"
    )

    if st.sidebar.button("Login"):
        role, me = authenticate_user(email_input, password_input)

        if role:
            st.session_state.auth_email = email_input
            st.session_state.auth_name = me.get("Name", "")
            st.session_state.auth_role = role
            st.sidebar.success(f"✅ {role.capitalize()} login successful.")
            _rerun()
        else:
            st.sidebar.error("❌ Invalid email or password.")


# =========================
# Sidebar: Live progress (no API calls)
# =========================
total_items = sum(len(v) for v in DOMAINS.values())
def current_progress_from_session() -> int:
    count = 0
    for _, items in DOMAINS.items():
        for code, label in items:
            if st.session_state.get(f"{code}-{label}"):
                count += 1
    return count

with st.sidebar.expander("Progress", expanded=True):
    done = current_progress_from_session()
    st.progress(done / total_items if total_items else 0.0)
    st.caption(f"{done}/{total_items} sub‑strands completed")

# Main Nav
st.title("🌟 OIS Teacher Self‑Assessment 2025‑26")

if not st.session_state.auth_email:
    st.info("Please log in from the sidebar to continue.")
    st.stop()

already_submitted = user_has_submission(st.session_state.auth_email)
role = users_df.loc[users_df["Email"] == st.session_state.auth_email, "Role"].iloc[0].lower()

i_am_admin = role == "admin"
i_am_sadmin = role == "sadmin"

if i_am_sadmin:
    nav_options = ["Super Admin"]
elif i_am_admin:
    nav_options = ["Admin"]
else:
    if already_submitted:
        nav_options = ["My Submission"]
    else:
        nav_options = ["Self-Assessment", "My Submission"]

tab = st.sidebar.radio("Menu", nav_options, index=0)


# =========================
# Page: Self-Assessment (teachers who haven't submitted yet)
# =========================
if tab == "Self-Assessment":
    if already_submitted and not i_am_admin:
        # Auto-redirect teachers with submissions to My Submission
        st.success("✅ You’ve already submitted your self-assessment. Redirecting to your submission...")
        tab = "My Submission"
    else:
        # Welcome + Appraiser info
        me = users_df[users_df["Email"] == st.session_state.auth_email].iloc[0] if not users_df.empty else {}
        appraiser = me.get("Appraiser","Not Assigned") if isinstance(me, pd.Series) else "Not Assigned"
        st.sidebar.info(f"Your appraiser: **{appraiser}**")

        # 🔹 Load draft if exists
        draft_data = load_draft(st.session_state.auth_email) or {}
        if draft_data:
            st.info("💾 A saved draft was found and preloaded. You can continue where you left off.")

        # Selections (direct widgets so sidebar progress updates live)
        selections = {}
        reflections = {}
        for domain, items in DOMAINS.items():
            with st.expander(domain, expanded=False):
                for code, label in items:
                    key = f"{code}-{label}"
                    saved_value = draft_data.get(f"{code} {label}", "")
                    selections[f"{code} {label}"] = st.radio(
                        f"{code} — {label}",
                        RATINGS,
                        index=RATINGS.index(saved_value) if saved_value in RATINGS else None,
                        key=key,
                    ) or ""
                if ENABLE_REFLECTIONS:
                    saved_refl = draft_data.get(f"Reflection-{domain}", "")
                    reflections[domain] = st.text_area(
                        f"{domain} Reflection (optional)",
                        key=f"refl-{domain}",
                        placeholder="Notes / evidence / next steps (optional)",
                        value=saved_refl,
                    )

        # Submit button + progress
        selected_count = sum(1 for v in selections.values() if v)
        col1, col2 = st.columns([1,3])
        with col1:
            submit = st.button("✅ Submit", disabled=(selected_count < total_items))
            save_draft_btn = st.button("💾 Save Draft Now")
        with col2:
            st.write(f"**Progress:** {selected_count}/{total_items} completed")

        # Handle Save Draft
        if save_draft_btn:
            draft_payload = {}
            for domain, items in DOMAINS.items():
                for code, label in items:
                    draft_payload[f"{code} {label}"] = selections[f"{code} {label}"]
                if ENABLE_REFLECTIONS:
                    draft_payload[f"Reflection-{domain}"] = reflections.get(domain, "")
            save_draft(st.session_state.auth_email, draft_payload)
            st.success("✅ Draft saved successfully!")

        # Handle Submit
        if submit:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                st.session_state.auth_email,
                st.session_state.auth_name,
                appraiser,
            ]
            for domain, items in DOMAINS.items():
                for code, label in items:
                    row.append(selections[f"{code} {label}"])
                if ENABLE_REFLECTIONS:
                    row.append(reflections.get(domain, ""))

            try:
                with_backoff(RESP_WS.append_row, row, value_input_option="USER_ENTERED")
                load_responses_df.clear()
                st.session_state.submitted = True
                st.success("🎉 Submitted. Thank you! See **My Submission** to review your responses.")
            except Exception as e:
                st.error("⚠️ Could not submit right now. Please try again shortly.")
                st.caption(f"Debug info: {e}")


# =========================
# Page: My Submission (teachers see their data here)
# =========================
if tab == "My Submission":
    df = load_responses_df()
    my = df[df["Email"] == st.session_state.auth_email] if not df.empty and "Email" in df.columns else pd.DataFrame()

    # auto-refresh if cache stale
    if my.empty:
        load_responses_df.clear()
        df = load_responses_df()
        my = df[df["Email"] == st.session_state.auth_email] if not df.empty and "Email" in df.columns else pd.DataFrame()

    st.subheader("My Submission")

    if my.empty:
        st.info("No submission found yet.")
    else:
        my_sorted = my.sort_values("Timestamp", ascending=False)
        latest = my_sorted.head(1)

        st.success("✅ You have already submitted your self-assessment. Here is your latest submission:")
        st.dataframe(latest, use_container_width=True)

        # download button with all submissions
        csv = my_sorted.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download my submissions (CSV)",
            data=csv,
            file_name="my_self_assessment.csv",
            mime="text/csv"
        )

    if st.button("🔄 Refresh"):
        load_responses_df.clear()
        _rerun()




# =========================
# Page: Admin Panel (Admin & Super Admin)
# =========================
if tab == "Admin" and i_am_admin:
    st.header("👩‍💼 Admin Panel")

    me = users_df[users_df["Email"] == st.session_state.auth_email].iloc[0]
    my_name = me.get("Name", st.session_state.auth_email)
    my_role = me.get("Role", "").strip().lower()
    my_first = my_name.split()[0].strip().lower()

    # Admins only see their assigned teachers, Super Admin sees all
    if my_role == "sadmin":
        assigned = users_df[users_df["Role"] == "user"]  # all teachers
        st.info("Super Admin access: viewing **all teachers** in the school.")
    else:
        assigned = users_df[
            users_df["Appraiser"].str.strip().str.lower() == my_first
        ] if not users_df.empty else pd.DataFrame()

    if assigned.empty:
        st.info("No teachers found for your role in the Users sheet.")
    else:
        st.subheader("📋 Summary of Teachers")

        resp_df = load_responses_df()
        summary_rows = []

        submitted_count = 0
        total_count = len(assigned)

        for _, teacher in assigned.iterrows():
            teacher_email = teacher["Email"].strip().lower()
            teacher_name = teacher["Name"]

            submissions = resp_df[resp_df["Email"] == teacher_email] if not resp_df.empty else pd.DataFrame()
            if submissions.empty:
                status = "❌ Not Submitted"
                last_date = "-"
            else:
                status = "✅ Submitted"
                last_date = submissions["Timestamp"].max()
                submitted_count += 1

            summary_rows.append({
                "Teacher": teacher_name,
                "Email": teacher_email,
                "Status": status,
                "Last Submission": last_date,
            })

        summary_df = pd.DataFrame(summary_rows)

        # Compact progress display
        col1, col2 = st.columns([1,2])
        with col1:
            st.markdown(
                f"**Progress:** {submitted_count}/{total_count} submitted  "
                f"({round((submitted_count/total_count)*100,1)}%)"
            )
        with col2:
            st.progress(submitted_count / total_count if total_count else 0)

        st.dataframe(summary_df, use_container_width=True)

        # Dropdown for deep dive
        st.divider()
        st.subheader("🔎 View Individual Submissions")

        teacher_choice = st.selectbox("Select a teacher", assigned["Name"].tolist())

        if teacher_choice:
            teacher_email = assigned.loc[assigned["Name"] == teacher_choice, "Email"].iloc[0]
            rows = resp_df[resp_df["Email"] == teacher_email] if not resp_df.empty else pd.DataFrame()

            if rows.empty:
                st.warning(f"No submission found for {teacher_choice}.")
            else:
                st.subheader(f"Latest submission for {teacher_choice}")
                latest = rows.sort_values("Timestamp", ascending=False).head(1)
                st.dataframe(latest, use_container_width=True)

                csv = rows.to_csv(index=False).encode("utf-8")
                st.download_button(
                    f"⬇️ Download all submissions for {teacher_choice}",
                    data=csv,
                    file_name=f"{teacher_choice}_submissions.csv",
                    mime="text/csv"
                )

    if st.button("🔄 Refresh Admin Data"):
        load_responses_df.clear()
        _rerun()

# =========================
# Page: Super Admin Panel
# =========================
if tab == "Super Admin" and i_am_sadmin:
    st.header("🏫 Super Admin Panel — Whole School View")

    assigned = users_df[users_df["Role"] == "user"]  # all teachers
    resp_df = load_responses_df()
    summary_rows = []

    submitted_count = 0
    total_count = len(assigned)

    for _, teacher in assigned.iterrows():
        teacher_email = teacher["Email"].strip().lower()
        teacher_name = teacher["Name"]

        submissions = resp_df[resp_df["Email"] == teacher_email] if not resp_df.empty else pd.DataFrame()
        if submissions.empty:
            status = "❌ Not Submitted"
            last_date = "-"
        else:
            status = "✅ Submitted"
            last_date = submissions["Timestamp"].max()
            submitted_count += 1

        summary_rows.append({
            "Teacher": teacher_name,
            "Email": teacher_email,
            "Status": status,
            "Last Submission": last_date,
        })

    summary_df = pd.DataFrame(summary_rows)

    # Compact progress display
    col1, col2 = st.columns([1,2])
    with col1:
        st.markdown(
            f"**Progress:** {submitted_count}/{total_count} submitted  "
            f"({round((submitted_count/total_count)*100,1)}%)"
        )
    with col2:
        st.progress(submitted_count / total_count if total_count else 0)

    st.subheader("📋 Summary of All Teachers")
    st.dataframe(summary_df, use_container_width=True)

    # Optional: download summary
    csv = summary_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Whole School Summary (CSV)",
        data=csv,
        file_name="whole_school_summary.csv",
        mime="text/csv"
    )

# =========================
# Super Admin: Whole-School Submissions
# =========================
if tab == "Super Admin" and i_am_sadmin:
    st.subheader("📊 Detailed Whole-School Submissions")

    # Fetch all responses
    df = load_responses_df()

    if df.empty:
        st.info("No submissions found yet.")
    else:
        # Remove reflections & goals for compactness
        reflection_cols = [c for c in df.columns if "Reflection" in c or "Goal" in c or "Comment" in c]
        df = df.drop(columns=reflection_cols, errors="ignore")

        # Reset index for numbering
        df.index = df.index + 1
        df.index.name = "No."

        # Replace full text with acronyms
        mapping = {
            "Highly Effective": "HE",
            "Effective": "E",
            "Improvement Necessary": "IN",
            "Does Not Meet Standards": "DNMS"
        }
        df = df.replace(mapping)

        # Apply colors
        def highlight_ratings(val):
            colors = {
                "HE": "background-color: #a8e6a1;",   # green
                "E": "background-color: #d0f0fd;",    # blue
                "IN": "background-color: #fff3b0;",   # yellow
                "DNMS": "background-color: #f8a5a5;"  # red
            }
            return colors.get(val, "")

        styled_df = df.style.applymap(highlight_ratings, subset=df.columns[4:])

        st.dataframe(styled_df, use_container_width=True)

        # Download option
        st.download_button(
            "⬇️ Download all submissions (CSV)",
            df.to_csv(index=True).encode("utf-8"),
            "all_submissions.csv",
            "text/csv"
        )



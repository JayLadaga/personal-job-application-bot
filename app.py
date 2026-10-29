import streamlit as st
import sqlite3, json, re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "applications.db"
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

def db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, company TEXT DEFAULT '', location TEXT DEFAULT '',
        url TEXT DEFAULT '', source TEXT DEFAULT '', work_type TEXT DEFAULT '',
        notes TEXT DEFAULT '', status TEXT DEFAULT 'Saved',
        created_at TEXT NOT NULL, UNIQUE(url)
    )""")
    con.commit()
    return con

def get_jobs():
    con = db()
    rows = con.execute("SELECT id,title,company,location,url,source,work_type,status,created_at,notes FROM jobs ORDER BY id DESC").fetchall()
    con.close()
    return rows

def add_job(title, company, location, url, source, work_type, notes):
    con = db()
    try:
        con.execute("INSERT INTO jobs(title,company,location,url,source,work_type,notes,status,created_at) VALUES(?,?,?,?,?,?,?,'Saved',?)",
                    (title, company, location, url, source, work_type, notes, datetime.now().isoformat(timespec="minutes")))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()

def update_status(job_id, status):
    con = db()
    con.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    con.commit()
    con.close()

st.set_page_config(page_title="Personal Job Application Bot", page_icon="🎯", layout="wide")
st.markdown("""
<style>
.stApp { background: #17191c; color: #f0f2f4; }
section[data-testid="stSidebar"] { background: #22262b; }
div[data-testid="stMetric"] { background:#24282e; padding:16px; border:1px solid #454b53; border-radius:12px; }
h1,h2,h3 { color:#e8edf2; }
.small-note { color:#b8c0c9; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Personal Job Application Bot")
st.caption("Local-first job search and application tracker • Charcoal & silver")

with st.sidebar:
    st.header("Job preferences")
    st.info("Current profile defaults are based on your instructions. You can change them anytime.")
    industries = st.multiselect("Target areas", ["Gaming / game development", "Any other suitable industry"],
                                default=["Gaming / game development", "Any other suitable industry"])
    work_modes = st.multiselect("Work arrangement", ["On-site", "Hybrid", "Remote"],
                                default=["On-site", "Hybrid", "Remote"])
    radius = st.number_input("On-site radius (miles)", min_value=1, max_value=100, value=1)
    area = st.text_input("Local search center", "Miami Lakes, FL")
    education = st.selectbox("Education", ["High school diploma", "GED", "Other"], index=0)
    experience = st.selectbox("Experience level", ["No experience / entry-level", "Some experience", "Any"], index=0)
    daily_limit = st.selectbox("Daily application target", ["As many suitable jobs as practical", "10", "25", "50"],
                               index=0)
    st.markdown("---")
    st.caption("Remote roles can be searched nationwide; the radius applies to on-site roles.")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Resume", "Find jobs", "Application tracker"])

with tab1:
    jobs = get_jobs()
    total = len(jobs)
    applied = sum(1 for j in jobs if j[7] in ("Applied", "Submitted"))
    interviews = sum(1 for j in jobs if j[7] == "Interview")
    c1,c2,c3 = st.columns(3)
    c1.metric("Saved jobs", total)
    c2.metric("Applications submitted", applied)
    c3.metric("Interviews", interviews)
    st.subheader("Your configured search")
    st.write(f"**Industries:** {', '.join(industries) if industries else 'Choose at least one'}")
    st.write(f"**Location:** On-site/hybrid roles within {radius} mile(s) of {area}; remote roles may be nationwide.")
    st.write(f"**Target qualifications:** {education}; {experience}.")
    st.warning("This starter version does not silently submit applications. It helps organize jobs and open official application pages. Reliable auto-submission requires a separate, permitted integration for each employer platform, and some forms require your review or CAPTCHA.")
    st.markdown("### Suggested workflow")
    st.markdown("1. Upload your resume.  2. Search using the links in **Find jobs**.  3. Save suitable roles.  4. Open the employer's official application page and complete any required verification.  5. Track the result here.")

with tab2:
    st.subheader("Upload your resume")
    resume = st.file_uploader("Choose a PDF, DOCX, or TXT resume", type=["pdf","docx","txt"])
    if resume:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", resume.name)
        dest = UPLOAD_DIR / safe_name
        dest.write_bytes(resume.getvalue())
        st.success(f"Resume saved locally as {safe_name}")
        st.caption("Your resume stays in this app folder unless you choose to share it with a job site.")
    st.subheader("Applicant profile")
    st.write("Add the details needed by application forms. For safety, this starter app does not store passwords, Social Security numbers, banking details, or identity documents.")
    with st.form("profile"):
        full_name = st.text_input("Full name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        diploma = st.text_input("High school / graduation year (optional)")
        skills = st.text_area("Skills and tools you can honestly claim")
        authorization = st.selectbox("Authorized to work in the United States?", ["Choose", "Yes", "No", "Prefer to answer per application"])
        submitted = st.form_submit_button("Save profile locally")
        if submitted:
            profile = {"full_name":full_name, "email":email, "phone":phone, "education":diploma,
                        "skills":skills, "work_authorization":authorization}
            (APP_DIR / "profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
            st.success("Profile saved locally.")

with tab3:
    st.subheader("Search suitable openings")
    st.write("These searches open current listings on external sites. Use the site's filters and confirm the exact work location and requirements before applying.")
    queries = [
        ("All entry-level jobs", f'"entry level" OR "no experience"'),
        ("Game tester / QA", '"game tester" OR "QA tester" OR "quality assurance"'),
        ("Game development", '"game developer" OR "game design" OR "game development"'),
        ("Customer service", '"customer service" OR "support representative"'),
        ("Retail / store associate", '"retail associate" OR "store associate"'),
        ("Warehouse / production", '"warehouse associate" OR "production associate"'),
        ("Office / data entry", '"data entry" OR "office assistant" OR "administrative assistant"')
    ]
    sites = [
        ("Indeed", "https://www.indeed.com/jobs?q={q}&l={loc}&radius={rad}"),
        ("LinkedIn", "https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}"),
        ("Google Jobs search", "https://www.google.com/search?q={q}+jobs+near+{loc}"),
        ("Employ Florida", "https://www.employflorida.com/"),
        ("Dice (tech / QA)", "https://www.dice.com/jobs?q={q}&location={loc}")
    ]
    for label, query in queries:
        st.markdown(f"**{label}**")
        cols = st.columns(len(sites))
        for col, (site, template) in zip(cols, sites):
            if site == "Employ Florida":
                url = template
            else:
                url = template.format(q=quote_plus(query), loc=quote_plus(area), rad=radius)
            col.link_button(site, url, use_container_width=True)
    st.markdown("---")
    st.subheader("Save a job to your tracker")
    with st.form("add_job"):
        title = st.text_input("Job title *")
        company = st.text_input("Company")
        location = st.text_input("Job location", area)
        url = st.text_input("Official application or listing URL *")
        source = st.selectbox("Found on", ["Indeed","LinkedIn","Company career page","Google Jobs","Employ Florida","Other"])
        work_type = st.selectbox("Work type", ["On-site","Hybrid","Remote","Unknown"])
        notes = st.text_area("Notes / requirements")
        save = st.form_submit_button("Save job")
        if save:
            if title.strip() and url.strip():
                if add_job(title.strip(), company.strip(), location.strip(), url.strip(), source, work_type, notes.strip()):
                    st.success("Job saved.")
                else:
                    st.warning("That URL is already in your tracker.")
            else:
                st.error("Please enter a job title and URL.")

with tab4:
    st.subheader("Application tracker")
    jobs = get_jobs()
    if not jobs:
        st.info("No jobs saved yet. Use Find jobs to search and add roles.")
    else:
        status_options = ["Saved","Ready to apply","Applied","Submitted","Interview","Rejected","No response","Not suitable"]
        for row in jobs:
            job_id,title,company,location,url,source,work_type,status,created_at,notes = row
            with st.container(border=True):
                a,b = st.columns([3,1])
                with a:
                    st.markdown(f"### {title}")
                    st.write(" • ".join(x for x in [company, location, work_type, source, created_at[:10]] if x))
                    if notes: st.caption(notes)
                    st.link_button("Open listing / application", url)
                with b:
                    new_status = st.selectbox("Status", status_options, index=status_options.index(status) if status in status_options else 0, key=f"status_{job_id}")
                    if st.button("Update", key=f"update_{job_id}"):
                        update_status(job_id, new_status)
                        st.rerun()

import streamlit as st
from PyPDF2 import PdfReader
# --- Task 4 imports ---
from anthropic import Anthropic
import os
from dotenv import load_dotenv
import time
import threading
import pandas as pd

# --- Custom CSS for styling ---
def apply_custom_css():
    st.markdown("""
    <style>
    .stApp {
        max-width: 900px;
        margin: 0 auto;
        background: #f8fafc;
    }
    .banner {
        background: linear-gradient(90deg, #fbbf24 0%, #f59e42 100%);
        color: #fff;
        padding: 1.5rem 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        box-shadow: 0 2px 16px rgba(0,0,0,0.07);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .banner-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .banner-desc {
        font-size: 1.1rem;
        font-weight: 400;
        opacity: 0.95;
    }
    .card {
        background: #fff;
        border-radius: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        padding: 1.5rem 2rem;
        margin-bottom: 2rem;
    }
    .analyze-btn {
        background: linear-gradient(90deg, #fbbf24 0%, #f59e42 100%);
        color: #fff;
        font-weight: 600;
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        transition: box-shadow 0.2s;
    }
    .analyze-btn:disabled {
        background: #f3f4f6;
        color: #bbb;
        box-shadow: none;
    }
    .result-table {
        margin-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()

# --- Banner/Header ---
st.markdown(
    '''<div class="banner">
        <div>
            <div class="banner-title">Sun Interview Qualifier</div>
            <div class="banner-desc">AI-powered resume analyzer for HR recruiters. Upload resumes, provide a job description, and get instant candidate analysis!</div>
        </div>
        <div style="font-size:2.5rem;opacity:0.7;">🌞</div>
    </div>''', unsafe_allow_html=True
)

# --- Job Description Input Card ---
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("Job Description Input")
jd_tabs = st.tabs(["Paste Text", "Upload PDF"])
job_description = ""

with jd_tabs[0]:
    jd_text = st.text_area("Paste the job description here", key="jd_text", help="Paste the full job description for the position.")
    if jd_text:
        job_description = jd_text

with jd_tabs[1]:
    jd_pdf = st.file_uploader("Upload a Job Description PDF", type=["pdf"], key="jd_pdf", accept_multiple_files=False, help="Upload a PDF file containing the job description.")
    if jd_pdf:
        reader = PdfReader(jd_pdf)
        jd_pdf_text = ""
        for page in reader.pages:
            jd_pdf_text += page.extract_text() or ""
        job_description = jd_pdf_text
        if jd_pdf_text:
            st.success("PDF extracted successfully.")

# Store in session state
if job_description:
    st.session_state["job_description"] = job_description

# Validation and Preview
if not job_description:
    st.warning("Please provide a job description (paste text or upload PDF).", icon="⚠️")
else:
    st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
    st.text_area("Extracted/Entered Job Description", job_description, height=200, key="jd_preview")

st.markdown('</div>', unsafe_allow_html=True)

# --- Resume Upload Card ---
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("Resume Upload")
uploaded_files = st.file_uploader(
    "Upload one or more PDF resumes",
    type=["pdf"],
    accept_multiple_files=True,
    key="resume_upload",
    help="Upload PDF resumes for analysis."
)

resume_texts = []
resume_names = []
if uploaded_files:
    for uploaded_file in uploaded_files:
        st.write(f"**{uploaded_file.name}**")
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        resume_texts.append(text)
        resume_names.append(uploaded_file.name)
        st.text_area("Extracted Text", text, height=200, key=f"resume_{uploaded_file.name}")

st.markdown('</div>', unsafe_allow_html=True)

# --- Analysis Trigger and Progress Bar ---
load_dotenv()
anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

_last_call_time = 0
_rate_limit_lock = threading.Lock()
def rate_limited_call(func):
    def wrapper(*args, **kwargs):
        global _last_call_time
        with _rate_limit_lock:
            now = time.time()
            if now - _last_call_time < 1:
                time.sleep(1 - (now - _last_call_time))
            _last_call_time = time.time()
        return func(*args, **kwargs)
    return wrapper

@rate_limited_call
def analyze_resume(resume_text, job_description):
    prompt = f"""I need you to analyze this resume against a job description. \n\nResume:\n{resume_text}\n\nJob Description:\n{job_description}\n\nPlease provide:\n1. The candidate's full name\n2. A brief analysis of how well the candidate fits the job requirements\n3. A numerical rank from 1-10 (10 being the best fit)\n\nFormat your response as a JSON object with keys: 'candidate_name', 'analysis', and 'rank'."""
    try:
        response = anthropic.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system="You are an expert HR recruiter assistant that analyzes resumes against job descriptions.",
            messages=[{"role": "user", "content": prompt}]
        )
        import json
        import re
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            return {"error": "Could not parse response"}
    except Exception as e:
        return {"error": str(e)}

# --- Stylish Analyze Button and Progress ---
can_analyze = bool(job_description) and bool(resume_texts)
progress_placeholder = st.empty()
results = []

if st.button('Analyze Resumes', key='analyze_btn', disabled=not can_analyze, help="Analyze all uploaded resumes against the job description.",
             args=None):
    with st.spinner('Analyzing resumes... This may take a minute.'):
        for i, (resume_text, resume_name) in enumerate(zip(resume_texts, resume_names)):
            progress = int((i / len(resume_texts)) * 100)
            progress_placeholder.progress(progress, text=f"Analyzing {resume_name} ({i+1}/{len(resume_texts)})...")
            result = analyze_resume(resume_text, job_description)
            result['resume_name'] = resume_name
            results.append(result)
        progress_placeholder.progress(100, text="Analysis complete!")
        st.session_state['analysis_results'] = results

# --- Results Section ---
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("Candidate Analysis Results")

analysis_results = st.session_state.get('analysis_results', [])
def display_results_table(results):
    if not results:
        st.info("No analysis results to display.")
        return
    sorted_results = sorted(results, key=lambda x: x.get('rank', 0), reverse=True)
    df = pd.DataFrame([
        {
            'S.No': i+1,
            'Resume Name': r.get('resume_name', 'Unknown'),
            'Candidate Name': r.get('candidate_name', 'Unknown'),
            'Analysis': r.get('analysis', 'No analysis available'),
            'Rank': r.get('rank', 0)
        } for i, r in enumerate(sorted_results)
    ])
    st.dataframe(df, use_container_width=True, height=400)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name="candidate_analysis_results.csv",
        mime="text/csv",
        key="download_csv_btn"
    )

display_results_table(analysis_results)
st.markdown('</div>', unsafe_allow_html=True) 
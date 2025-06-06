import streamlit as st
from PyPDF2 import PdfReader
# --- Task 4 imports ---
from anthropic import Anthropic
import os
from dotenv import load_dotenv
import time
import threading
import pandas as pd
import logging
import datetime

# --- Load Custom CSS from styles.css ---
def load_custom_css():
    try:
        with open('styles.css', 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception as e:
        st.warning(f'Could not load custom CSS: {e}')

load_custom_css()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# --- Centralized Error Display Helper ---
def show_error(message, suggestion=None):
    st.error(message)
    if suggestion:
        st.info(suggestion)

# --- File Validation Helper ---
def is_valid_pdf(file):
    if file is None:
        return False
    if hasattr(file, 'type') and file.type != 'application/pdf':
        return False
    if not file.name.lower().endswith('.pdf'):
        return False
    return True

# --- Banner/Header ---
st.markdown(
    '''<div class="banner">
        <div>
            <div class="banner-title">Sun Interview Qualifier</div>
            <div class="banner-desc">AI-powered resume analyzer for HR recruiters.<br>Upload resumes, provide a job description, and get instant candidate analysis!<br><span style="font-size:1rem;opacity:0.9;">Modern UI/UX inspired by 21st.dev</span></div>
        </div>
        <div style="font-size:3rem;opacity:0.9;">🌞</div>
        <!-- Future navigation or links can go here -->
    </div>''', unsafe_allow_html=True
)

# --- Job Description Input Card ---
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Job Description Input</div>', unsafe_allow_html=True)
jd_tabs = st.tabs(["Paste Text", "Upload PDF"])
job_description = ""

with jd_tabs[0]:
    jd_text = st.text_area("Paste the job description here", key="jd_text", help="Paste the full job description for the position.")
    if jd_text:
        job_description = jd_text

with jd_tabs[1]:
    jd_pdf = st.file_uploader("Upload a Job Description PDF", type=["pdf"], key="jd_pdf", accept_multiple_files=False, help="Upload a PDF file containing the job description.")
    if jd_pdf:
        if not is_valid_pdf(jd_pdf):
            show_error("Invalid file type. Please upload a PDF file.")
        else:
            try:
                reader = PdfReader(jd_pdf)
                jd_pdf_text = ""
                for page in reader.pages:
                    jd_pdf_text += page.extract_text() or ""
                job_description = jd_pdf_text
                if jd_pdf_text:
                    st.success("PDF extracted successfully.")
            except Exception as e:
                logger.error(f"Error extracting text from job description PDF: {e}")
                show_error("Failed to extract text from the uploaded PDF.", suggestion="Please check the file or try another PDF.")

# Store in session state
if job_description:
    st.session_state["job_description"] = job_description

# Validation and Preview
if not job_description:
    show_error("Please provide a job description (paste text or upload PDF).")
st.markdown('</div>', unsafe_allow_html=True)

# --- Resume Upload Card ---
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Resume Upload</div>', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "Upload one or more PDF resumes",
    type=["pdf"],
    accept_multiple_files=True,
    key="resume_upload",
    help="Upload PDF resumes for analysis."
)

# --- Session Management ---
def initialize_session_state():
    if 'uploaded_resumes' not in st.session_state:
        st.session_state.uploaded_resumes = []
    if 'job_description' not in st.session_state:
        st.session_state.job_description = ""
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []
    if 'last_active' not in st.session_state:
        st.session_state.last_active = datetime.datetime.now()
    if 'step' not in st.session_state:
        st.session_state.step = 1  # For future multi-step workflow

# Call at the top of the app
initialize_session_state()

# --- Session Timeout (30 min inactivity) ---
now = datetime.datetime.now()
if (now - st.session_state.last_active).total_seconds() > 1800:
    st.session_state.uploaded_resumes = []
    st.session_state.job_description = ""
    st.session_state.analysis_results = []
    st.session_state.step = 1
    st.session_state.last_active = now
    st.info("Session expired due to inactivity. All data has been cleared.")
else:
    st.session_state.last_active = now

# --- Clear Session Button ---
with st.sidebar:
    if st.button("Clear Session", help="Reset all uploaded files, job description, and results."):
        st.session_state.uploaded_resumes = []
        st.session_state.job_description = ""
        st.session_state.analysis_results = []
        st.session_state.step = 1
        st.session_state.last_active = datetime.datetime.now()
        st.success("Session cleared!")

resume_texts = []
resume_names = []
if uploaded_files:
    st.session_state.uploaded_resumes = uploaded_files
    for uploaded_file in uploaded_files:
        if not is_valid_pdf(uploaded_file):
            show_error(f"{uploaded_file.name} is not a valid PDF file.", suggestion="Please upload only PDF resumes.")
            continue
        st.write(f"**{uploaded_file.name}**")
        try:
            reader = PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            resume_texts.append(text)
            resume_names.append(uploaded_file.name)
        except Exception as e:
            logger.error(f"Error extracting text from {uploaded_file.name}: {e}")
            show_error(f"Failed to extract text from {uploaded_file.name}.", suggestion="Please check the file or try another PDF.")
else:
    # If no new uploads, try to restore from session
    if st.session_state.uploaded_resumes:
        for uploaded_file in st.session_state.uploaded_resumes:
            resume_names.append(uploaded_file.name)
            # Can't re-extract text from file-like object after upload, so skip text

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
            show_error("Could not parse response from the AI.", suggestion="Please try again or check the API response format.")
            return {"error": "Could not parse response"}
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        show_error("An error occurred while analyzing the resume.", suggestion="Please check your API key, network connection, or try again later.")
        return {"error": str(e)}

# --- Stylish Analyze Button and Progress ---
can_analyze = bool(job_description) and bool(resume_texts)
progress_placeholder = st.empty()
results = []

if st.button('Analyze Resumes', key='analyze_btn', disabled=not can_analyze, help="Analyze all uploaded resumes against the job description.",
             args=None, type="primary"):
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
st.markdown('<div class="section-title">Candidate Analysis Results</div>', unsafe_allow_html=True)

analysis_results = st.session_state.get('analysis_results', [])

def display_results_table(results):
    if not results:
        st.info("No analysis results to display.")
        return
    # Sort results by rank (highest first)
    sorted_results = sorted(results, key=lambda x: x.get('rank', 0), reverse=True)
    df = pd.DataFrame([
        {
            'S.No': i+1,
            'Resume Name': r.get('resume_name', 'Unknown'),
            'Candidate Name': r.get('candidate_name', 'Unknown'),
            'Analysis': r.get('analysis', 'No analysis available'),
            'Raw Score': r.get('rank', 0)  # Keep the original score for reference
        } for i, r in enumerate(sorted_results)
    ])
    # Assign new ranks: 1 (best) to N (worst)
    df['Rank'] = range(1, len(df) + 1)
    # Move 'Rank' column before 'Raw Score'
    cols = df.columns.tolist()
    cols.insert(cols.index('Raw Score'), cols.pop(cols.index('Rank')))
    df = df[cols]
    # Add a badge for top 3 candidates
    def badge(rank):
        if rank == 1:
            return '🥇'
        elif rank == 2:
            return '🥈'
        elif rank == 3:
            return '🥉'
        else:
            return ''
    df['Top'] = df['Rank'].apply(badge)
    # Move 'Top' to the front
    cols = ['Top'] + [c for c in df.columns if c != 'Top']
    df = df[cols]
    # Conditional formatting: highlight top 3 candidates
    def highlight_top(row):
        if row['Rank'] <= 3:
            return ['background-color: #ffe082'] * len(row)
        return [''] * len(row)
    styled_df = df.style.apply(highlight_top, axis=1)
    # Display the styled table, ensure scrollability on small screens
    st.markdown('<div style="overflow-x:auto;">', unsafe_allow_html=True)
    try:
        st.dataframe(styled_df, use_container_width=True, height=400)
    except Exception:
        st.dataframe(df, use_container_width=True, height=400)
    st.markdown('</div>', unsafe_allow_html=True)
    # CSV download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name="candidate_analysis_results.csv",
        mime="text/csv",
        key="download_csv_btn"
    )
    st.caption("Top 3 candidates are highlighted and marked with badges.")

display_results_table(analysis_results) 
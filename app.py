import streamlit as st
from PyPDF2 import PdfReader
# --- Task 4 imports ---
from anthropic import Anthropic
import os
from dotenv import load_dotenv
import time
import threading

st.title("Sun Interview Qualifier")
st.write("Project setup is complete! Ready to start building features.")

# --- Job Description Input (Task 3) ---
jd_tabs = st.tabs(["Paste Text", "Upload PDF"])
job_description = ""

with jd_tabs[0]:
    jd_text = st.text_area("Paste the job description here", key="jd_text")
    if jd_text:
        job_description = jd_text

with jd_tabs[1]:
    jd_pdf = st.file_uploader("Upload a Job Description PDF", type=["pdf"], key="jd_pdf", accept_multiple_files=False)
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
    st.warning("Please provide a job description (paste text or upload PDF).")
else:
    st.subheader("Job Description Preview")
    st.text_area("Extracted/Entered Job Description", job_description, height=200, key="jd_preview")

# --- Resume Upload (existing code) ---
uploaded_files = st.file_uploader(
    "Upload one or more PDF resumes",
    type=["pdf"],
    accept_multiple_files=True,
    key="resume_upload"
) 

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.write(f"**{uploaded_file.name}**")
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        st.text_area("Extracted Text", text, height=200, key=f"resume_{uploaded_file.name}")

# --- Task 4: Anthropic API Integration ---
load_dotenv()
anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Simple rate limiter: allow 1 call per second
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
    prompt = f"""I need you to analyze this resume against a job description. 
    
Resume:
{resume_text}

Job Description:
{job_description}

Please provide:
1. The candidate's full name
2. A brief analysis of how well the candidate fits the job requirements
3. A numerical rank from 1-10 (10 being the best fit)

Format your response as a JSON object with keys: 'candidate_name', 'analysis', and 'rank'."""
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
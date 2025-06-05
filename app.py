import streamlit as st
from PyPDF2 import PdfReader

st.title("Sun Interview Qualifier")
st.write("Project setup is complete! Ready to start building features.")

uploaded_files = st.file_uploader(
    "Upload one or more PDF resumes",
    type=["pdf"],
    accept_multiple_files=True
) 

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.write(f"**{uploaded_file.name}**")
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        st.text_area("Extracted Text", text, height=200) 
# Sun Interview Qualifier

## Overview
Sun Interview Qualifier is an AI-powered Streamlit web app for HR recruiters. It allows uploading multiple PDF resumes and a job description (text or PDF), analyzes candidate fit using the Anthropic API, and displays ranked results in a modern, user-friendly interface.

## Features
- Upload multiple PDF resumes
- Input job description (paste text or upload PDF)
- Analyze resumes against job description using Anthropic API (Claude 3 Opus)
- Sortable, downloadable results table with candidate analysis and rank
- Comprehensive error handling and session management
- Modern, responsive UI/UX

## Installation
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd sun_interview_qualifier
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your `.env` file with your Anthropic API key:
   ```env
   ANTHROPIC_API_KEY=your_api_key_here
   ```

## Usage
1. Run the app:
   ```bash
   streamlit run app.py
   ```
2. Open the provided local URL in your browser.
3. Upload resumes and provide a job description.
4. Click "Analyze Resumes" to view ranked results.

### Screenshots
> _Add screenshots of the UI here._

## Troubleshooting
- **PDF extraction errors:** Ensure files are valid PDFs and not password-protected.
- **API errors:** Check your API key and network connection.
- **Session expired:** If inactive for 30 minutes, session data will be cleared for security.

## Anthropic API Usage
- The app uses the Anthropic Claude 3 Opus model for resume analysis.
- API key is required in the `.env` file.
- Rate limits depend on your Anthropic account; the app rate-limits requests to 1/sec.

## Sample Data
- _Add sample resumes and job descriptions in the `samples/` folder for testing._

## License
MIT
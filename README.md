# AI Resume Screener

An AI-powered Resume Screening and Candidate Ranking Web Application built with Python, NLP, and Machine Learning.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/aasimansari1/Resume-Screening)

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![spaCy](https://img.shields.io/badge/spaCy-3.7-orange)
![scikit--learn](https://img.shields.io/badge/scikit--learn-1.4-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Multi-format Resume Upload** — PDF and DOCX support, multiple files at once
- **NLP Information Extraction** — Name, email, phone, LinkedIn, GitHub, skills, education, experience, certifications
- **AI Scoring Engine** — TF-IDF + Cosine Similarity, Skills Match, Experience Score, Education Score
- **ATS Compatibility Scoring** — Keyword density, section structure, contact completeness
- **Candidate Ranking Dashboard** — Interactive charts (bar, radar, doughnut, pie) via Chart.js
- **Candidate Detail View** — Score breakdown, matched/missing skills, education & experience timeline
- **AI Interview Questions** — Auto-generated behavioral, technical, and role-specific questions
- **Resume Improvement Suggestions** — Prioritized actionable tips per candidate
- **Export Reports** — CSV and PDF (color-coded) ranking reports
- **Dark Mode** — Toggle between light and dark themes
- **Search & Filter** — Filter by score, search by name/email/skill, table/card view toggle
- **Admin Authentication** — Flask-Login session-based auth

## Scoring Algorithm

| Component | Weight | Description |
|---|---|---|
| Semantic Match (TF-IDF) | 35% | Cosine similarity between resume and JD |
| Skills Match | 35% | Jaccard overlap of extracted vs required skills |
| Experience | 20% | Years of experience vs required |
| Education | 10% | Degree level scoring |

## Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | Flask 3.0, Flask-Login |
| NLP | spaCy (en_core_web_sm), NLTK |
| ML / Vectorization | scikit-learn (TF-IDF, Cosine Similarity) |
| PDF Parsing | pdfplumber, PyPDF2 |
| DOCX Parsing | docx2txt, python-docx |
| Data | pandas, numpy |
| Report Generation | ReportLab |
| Frontend | Bootstrap 5, Chart.js, Font Awesome |

## Quick Start

```bash
git clone https://github.com/aasimansari1/Resume-Screening.git
cd Resume-Screening

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

python app.py
# Open http://localhost:5000
```

Default login: **admin** / **admin123**

## Configuration

Copy `.env.example` to `.env` and edit:

```env
SECRET_KEY=your-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password

# Optional email notifications
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your-app-password
```

## Project Structure

```
ai-resume-screener/
├── app.py                # Flask routes, auth, exports
├── resume_parser.py      # NLP parsing engine (336 skills DB)
├── rank_candidates.py    # Scoring, ranking, interview Q gen
├── config.py             # App configuration
├── requirements.txt
├── .env.example
├── templates/
│   ├── base.html         # Sidebar layout
│   ├── index.html        # Upload & Analyze
│   ├── dashboard.html    # Analytics charts
│   ├── candidates.html   # Ranked table + card view
│   ├── candidate_detail.html  # Profile + suggestions
│   └── login.html
└── static/
    ├── css/style.css
    └── js/main.js
```

## Screenshots

| Page | Description |
|---|---|
| Login | Dark gradient login with feature preview |
| Upload | Drag & drop resumes + JD textarea |
| Dashboard | KPI cards + 5 Chart.js visualizations |
| Candidates | Ranked table with score badges and donut ring |
| Detail | Profile ring, skills analysis, radar chart, interview Qs |

## License

MIT

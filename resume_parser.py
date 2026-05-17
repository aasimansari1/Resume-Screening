import re
import os
import logging
from pathlib import Path

import nltk
import numpy as np

# Download required NLTK data silently
for pkg in ['punkt', 'stopwords', 'averaged_perceptron_tagger', 'maxent_ne_chunker', 'words', 'punkt_tab']:
    try:
        nltk.download(pkg, quiet=True)
    except Exception:
        pass

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import docx2txt
    DOCX2TXT_AVAILABLE = True
except ImportError:
    DOCX2TXT_AVAILABLE = False

try:
    import spacy
    try:
        NLP = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except OSError:
        SPACY_AVAILABLE = False
        NLP = None
except ImportError:
    SPACY_AVAILABLE = False
    NLP = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Comprehensive skills database
# ---------------------------------------------------------------------------
SKILLS_DATABASE = {
    "programming_languages": [
        "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "Ruby",
        "PHP", "Go", "Golang", "Rust", "Swift", "Kotlin", "Scala", "R", "MATLAB",
        "Perl", "Bash", "Shell", "PowerShell", "Dart", "Lua", "Haskell", "Elixir",
        "Clojure", "F#", "Groovy", "Julia", "COBOL", "Fortran", "Assembly", "VBA",
        "Objective-C", "Solidity", "Terraform HCL"
    ],
    "web_frameworks": [
        "Django", "Flask", "FastAPI", "Spring", "Spring Boot", "Express.js",
        "Node.js", "React", "Angular", "Vue.js", "Vue", "Next.js", "Nuxt.js",
        "Svelte", "Laravel", "Rails", "Ruby on Rails", "ASP.NET", "jQuery",
        "Bootstrap", "Tailwind CSS", "REST API", "RESTful", "GraphQL", "gRPC",
        "Tornado", "Pyramid", "Bottle", "Starlette", "Hapi.js", "Koa.js",
        "Ember.js", "Backbone.js", "Gatsby", "Remix", "SvelteKit"
    ],
    "ml_ai": [
        "TensorFlow", "PyTorch", "Keras", "scikit-learn", "sklearn", "XGBoost",
        "LightGBM", "CatBoost", "OpenCV", "Hugging Face", "Transformers", "spaCy",
        "NLTK", "BERT", "GPT", "LLM", "Computer Vision", "NLP",
        "Natural Language Processing", "Deep Learning", "Machine Learning",
        "Neural Networks", "CNN", "RNN", "LSTM", "GAN", "Reinforcement Learning",
        "Feature Engineering", "Model Deployment", "MLOps", "AutoML",
        "Random Forest", "SVM", "Support Vector Machine", "Gradient Boosting",
        "PCA", "Dimensionality Reduction", "Transfer Learning", "Fine-tuning",
        "Prompt Engineering", "RAG", "Vector Database", "Embeddings", "Langchain"
    ],
    "data_science": [
        "Pandas", "NumPy", "SciPy", "Matplotlib", "Seaborn", "Plotly", "Bokeh",
        "Tableau", "Power BI", "Jupyter", "Google Colab", "Statistical Analysis",
        "Data Analysis", "Data Visualization", "A/B Testing", "Hypothesis Testing",
        "Regression", "Classification", "Clustering", "Time Series", "Forecasting",
        "ETL", "Data Pipeline", "Feature Selection", "Data Cleaning",
        "Data Wrangling", "Data Mining", "Business Intelligence", "Analytics",
        "Spark", "Apache Spark", "Hadoop", "Hive", "Pig", "Kafka", "Flink"
    ],
    "databases": [
        "MySQL", "PostgreSQL", "SQLite", "MongoDB", "Redis", "Cassandra",
        "DynamoDB", "Firebase", "Elasticsearch", "Oracle", "SQL Server",
        "MariaDB", "CouchDB", "Neo4j", "InfluxDB", "BigQuery", "Snowflake",
        "Redshift", "SQL", "NoSQL", "PL/SQL", "T-SQL", "Supabase", "PlanetScale",
        "CockroachDB", "TimescaleDB", "Pinecone", "Weaviate", "Qdrant"
    ],
    "cloud_devops": [
        "AWS", "Amazon Web Services", "Azure", "Microsoft Azure", "GCP",
        "Google Cloud", "Docker", "Kubernetes", "K8s", "Terraform", "Ansible",
        "Jenkins", "CircleCI", "GitHub Actions", "GitLab CI", "Helm",
        "Prometheus", "Grafana", "Nginx", "Apache", "Linux", "Ubuntu",
        "CI/CD", "DevOps", "SRE", "Infrastructure as Code", "IaC",
        "Serverless", "Lambda", "ECS", "EKS", "GKE", "CloudFormation",
        "Pulumi", "Vault", "Consul", "Istio", "Service Mesh", "ArgoCD", "Flux"
    ],
    "tools": [
        "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Confluence", "Slack",
        "VS Code", "IntelliJ", "PyCharm", "Eclipse", "Postman", "Swagger",
        "Figma", "Photoshop", "Illustrator", "Excel", "Word", "PowerPoint",
        "Notion", "Trello", "Asana", "Linear", "Datadog", "New Relic",
        "Sentry", "PagerDuty", "Splunk", "ELK Stack", "Logstash", "Kibana"
    ],
    "networking_security": [
        "TCP/IP", "HTTP", "HTTPS", "DNS", "VPN", "Firewall", "SSL", "TLS",
        "OAuth", "JWT", "Cybersecurity", "Penetration Testing", "OWASP",
        "Network Security", "Cryptography", "PKI", "SIEM", "SOC",
        "Vulnerability Assessment", "Security Audit", "Compliance", "GDPR",
        "HIPAA", "ISO 27001", "NIST", "Zero Trust"
    ],
    "mobile": [
        "Android", "iOS", "React Native", "Flutter", "Xamarin", "Ionic",
        "Swift", "Kotlin", "Mobile Development", "App Development",
        "Cross-Platform", "PWA", "Progressive Web App"
    ],
    "soft_skills": [
        "Leadership", "Communication", "Teamwork", "Team Player", "Problem Solving",
        "Critical Thinking", "Project Management", "Agile", "Scrum", "Kanban",
        "Time Management", "Presentation", "Mentoring", "Collaboration",
        "Creativity", "Adaptability", "Analytical", "Detail-Oriented",
        "Self-Motivated", "Fast Learner", "Multi-tasking", "Decision Making",
        "Stakeholder Management", "Client Facing", "Cross-functional"
    ],
    "finance_business": [
        "Financial Analysis", "Accounting", "Budgeting", "Forecasting",
        "Excel", "Financial Modeling", "Valuation", "M&A", "Investment",
        "Risk Management", "Compliance", "Audit", "Tax", "QuickBooks",
        "SAP", "Oracle Financials", "CRM", "Salesforce", "HubSpot", "ERP"
    ]
}

# Flat list of all skills for fast lookup
ALL_SKILLS = []
SKILLS_LOWER_MAP = {}
for category, skills in SKILLS_DATABASE.items():
    for skill in skills:
        ALL_SKILLS.append(skill)
        SKILLS_LOWER_MAP[skill.lower()] = skill

EDUCATION_KEYWORDS = {
    "phd": ["phd", "ph.d", "ph.d.", "doctor of philosophy", "doctorate", "doctoral"],
    "masters": ["master", "m.s.", "ms ", "m.s ", "mba", "m.eng", "m.tech", "m.sc",
                 "master of science", "master of arts", "master of business"],
    "bachelors": ["bachelor", "b.s.", "b.sc", "b.a.", "b.e.", "b.tech", "b.eng",
                  "undergraduate", "bachelor of science", "bachelor of arts",
                  "bachelor of engineering", "bachelor of technology"],
    "associate": ["associate", "a.s.", "a.a.", "a.a.s."],
    "diploma": ["diploma", "certificate program", "post-graduate diploma"],
    "highschool": ["high school", "secondary school", "ged", "hsc", "ssc"]
}

EXPERIENCE_SECTION_HEADERS = [
    "experience", "work experience", "professional experience", "employment",
    "work history", "career history", "positions held", "employment history",
    "professional background", "job history"
]

EDUCATION_SECTION_HEADERS = [
    "education", "academic background", "educational background", "qualifications",
    "academic qualifications", "degrees", "university", "college"
]

CERT_SECTION_HEADERS = [
    "certifications", "certificates", "certification", "professional certifications",
    "licenses", "accreditations", "credentials"
]

SKILLS_SECTION_HEADERS = [
    "skills", "technical skills", "core competencies", "competencies",
    "technologies", "tools", "programming languages", "expertise"
]

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(filepath: str) -> str:
    text = ""
    # Try pdfplumber first (handles complex layouts better)
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"pdfplumber failed for {filepath}: {e}")

    # Fallback to PyPDF2
    if PYPDF2_AVAILABLE:
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.warning(f"PyPDF2 failed for {filepath}: {e}")

    return text


def extract_text_from_docx(filepath: str) -> str:
    if DOCX2TXT_AVAILABLE:
        try:
            return docx2txt.process(filepath)
        except Exception as e:
            logger.warning(f"docx2txt failed for {filepath}: {e}")

    # Fallback using python-docx
    try:
        from docx import Document
        doc = Document(filepath)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        logger.warning(f"python-docx failed for {filepath}: {e}")

    return ""


def extract_text(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext == '.pdf':
        return extract_text_from_pdf(filepath)
    elif ext in ('.docx', '.doc'):
        return extract_text_from_docx(filepath)
    else:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# NLP helpers
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return text.strip()


def extract_email(text: str) -> str:
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, text)
    return matches[0] if matches else ""


def extract_phone(text: str) -> str:
    patterns = [
        r'\+?1?\s?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}',
        r'\+?(\d[\s\-.]?){10,13}',
        r'\(\d{3}\)\s?\d{3}[\-\s]\d{4}'
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            phone = re.sub(r'[^\d+]', '', matches[0] if isinstance(matches[0], str) else ''.join(matches[0]))
            if len(phone) >= 10:
                return matches[0] if isinstance(matches[0], str) else ''.join(matches[0])
    return ""


def extract_linkedin(text: str) -> str:
    pattern = r'(?:linkedin\.com/in/|linkedin\.com/pub/)([a-zA-Z0-9\-]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return f"linkedin.com/in/{match.group(1)}" if match else ""


def extract_github(text: str) -> str:
    pattern = r'github\.com/([a-zA-Z0-9\-]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return f"github.com/{match.group(1)}" if match else ""


def extract_name(text: str) -> str:
    """Extract candidate name using spaCy NER or heuristics."""
    lines = [l.strip() for l in text.split('\n') if l.strip()][:10]

    if SPACY_AVAILABLE and NLP:
        # Analyse first few lines with spaCy
        snippet = " ".join(lines[:5])
        doc = NLP(snippet)
        persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        if persons:
            return persons[0]

    # Heuristic: first non-email, non-phone line with 2-4 words and proper case
    for line in lines[:5]:
        if '@' in line or re.search(r'\d{5,}', line):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            # Skip lines that look like section headers or URLs
            lower = line.lower()
            if not any(h in lower for h in ['resume', 'cv', 'curriculum', 'http', 'www']):
                return line
    return lines[0] if lines else "Unknown"


def extract_skills(text: str) -> list:
    """Extract skills using case-insensitive exact and phrase matching."""
    text_lower = text.lower()
    found = set()

    for skill_lower, skill_original in SKILLS_LOWER_MAP.items():
        # Word boundary matching to avoid partial matches (e.g., "R" in "React")
        if len(skill_lower) <= 2:
            # Short skills: require word boundaries
            pattern = r'\b' + re.escape(skill_lower) + r'\b'
        else:
            pattern = re.escape(skill_lower)

        if re.search(pattern, text_lower):
            found.add(skill_original)

    return sorted(found)


def _split_into_sections(text: str) -> dict:
    """Split resume text into named sections."""
    lines = text.split('\n')
    sections = {}
    current_section = "header"
    buffer = []

    section_all_headers = (
        EXPERIENCE_SECTION_HEADERS + EDUCATION_SECTION_HEADERS +
        CERT_SECTION_HEADERS + SKILLS_SECTION_HEADERS +
        ["summary", "objective", "profile", "about", "projects",
         "publications", "awards", "volunteer", "languages", "interests",
         "references", "additional"]
    )

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower().rstrip(':').strip()

        # Detect section header: short line (< 5 words) that matches known headers
        if lower in section_all_headers or any(lower.startswith(h) for h in section_all_headers):
            if buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = lower.rstrip(':').strip()
            buffer = []
        else:
            buffer.append(stripped)

    if buffer:
        sections[current_section] = "\n".join(buffer)

    return sections


def extract_education(text: str) -> list:
    """Extract education entries from resume text."""
    sections = _split_into_sections(text)
    education_text = ""
    for key in sections:
        if any(h in key for h in ["education", "academic", "qualification", "degree"]):
            education_text += sections[key] + "\n"

    if not education_text:
        education_text = text

    education = []
    lines = education_text.split('\n')

    degree_pattern = '|'.join([
        r'\bph\.?d\b', r'\bdoctorate\b', r'\bdoctoral\b',
        r'\bmaster\b', r'\bm\.s\b', r'\bmba\b', r'\bm\.eng\b', r'\bm\.tech\b',
        r'\bbachelor\b', r'\bb\.s\b', r'\bb\.sc\b', r'\bb\.a\b', r'\bb\.e\b',
        r'\bb\.tech\b', r'\bassociate\b', r'\bdiploma\b'
    ])

    year_pattern = r'\b(19|20)\d{2}\b'

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if re.search(degree_pattern, line_lower):
            # Try to get institution from context
            institution = ""
            years = re.findall(year_pattern, line)
            if not years and i + 1 < len(lines):
                years = re.findall(year_pattern, lines[i + 1])

            # Institution detection
            if SPACY_AVAILABLE and NLP:
                doc = NLP(line)
                orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
                if orgs:
                    institution = orgs[0]

            if not institution:
                # Heuristic: look for "University", "College", "Institute" in nearby lines
                context_lines = lines[max(0, i-1):min(len(lines), i+3)]
                for cl in context_lines:
                    if any(kw in cl.lower() for kw in ["university", "college", "institute", "school"]):
                        institution = cl.strip()
                        break

            # Determine degree level
            level = "Unknown"
            for lvl, keywords in EDUCATION_KEYWORDS.items():
                if any(kw in line_lower for kw in keywords):
                    level = lvl.capitalize()
                    break

            # GPA extraction
            gpa_match = re.search(r'\bgpa[:\s]*([0-9]\.[0-9]{1,2})\b', line_lower)
            gpa = gpa_match.group(1) if gpa_match else ""

            entry = {
                "degree": line.strip(),
                "institution": institution,
                "years": years,
                "level": level,
                "gpa": gpa
            }
            education.append(entry)

    return education[:5]  # Cap to avoid noise


def extract_experience(text: str) -> list:
    """Extract work experience entries."""
    sections = _split_into_sections(text)
    exp_text = ""
    for key in sections:
        if any(h in key for h in EXPERIENCE_SECTION_HEADERS):
            exp_text += sections[key] + "\n"

    if not exp_text:
        exp_text = text

    experiences = []
    lines = exp_text.split('\n')

    date_pattern = (
        r'(?:'
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}'
        r'|(?:0?[1-9]|1[0-2])/\d{4}'
        r'|\d{4}'
        r')'
        r'(?:\s*[-–—]\s*'
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}'
        r'|\s*[-–—]\s*(?:0?[1-9]|1[0-2])/\d{4}'
        r'|\s*[-–—]\s*\d{4}'
        r'|\s*[-–—]\s*(?:present|current|now)'
        r')?'
    )

    current_entry = None
    for line in lines:
        line = line.strip()
        if not line:
            continue

        has_date = re.search(date_pattern, line, re.IGNORECASE)
        if has_date:
            if current_entry:
                experiences.append(current_entry)

            # Try to extract title and company
            title = ""
            company = ""
            if SPACY_AVAILABLE and NLP:
                doc = NLP(line)
                orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
                if orgs:
                    company = orgs[0]

            current_entry = {
                "title": title or line[:80],
                "company": company,
                "duration": has_date.group(0),
                "description": ""
            }
        elif current_entry and line:
            # Continuation of current entry
            if not current_entry["title"] or len(current_entry["title"]) > 80:
                current_entry["title"] = line[:80]
            else:
                current_entry["description"] += " " + line

    if current_entry:
        experiences.append(current_entry)

    return experiences[:10]


def calculate_experience_years(experiences: list) -> float:
    """Estimate total years of experience from experience entries."""
    total_months = 0
    current_year = 2024

    year_pattern = r'\b(19|20)(\d{2})\b'

    for exp in experiences:
        duration_str = exp.get("duration", "") + " " + exp.get("title", "")
        years_found = re.findall(year_pattern, duration_str)

        if len(years_found) >= 2:
            start_year = int(years_found[0][0] + years_found[0][1])
            end_str = years_found[-1][0] + years_found[-1][1]
            end_year = current_year if "present" in duration_str.lower() or "current" in duration_str.lower() else int(end_str)
            months = max(0, (end_year - start_year) * 12)
            total_months += months
        elif len(years_found) == 1:
            start_year = int(years_found[0][0] + years_found[0][1])
            if "present" in duration_str.lower() or "current" in duration_str.lower():
                total_months += (current_year - start_year) * 12
            else:
                total_months += 12  # assume 1 year if only one year found

    return round(total_months / 12, 1)


def extract_certifications(text: str) -> list:
    """Extract certifications from resume."""
    sections = _split_into_sections(text)
    cert_text = ""
    for key in sections:
        if any(h in key for h in ["certif", "licens", "accred", "credential"]):
            cert_text += sections[key] + "\n"

    # Also scan full text for common cert patterns
    cert_keywords = [
        "AWS Certified", "Azure Certified", "Google Certified", "GCP Certified",
        "PMP", "PMI", "CPA", "CFA", "CISSP", "CEH", "CISM", "CISA",
        "CompTIA", "CCNA", "CCNP", "CCIE", "Cisco Certified",
        "Oracle Certified", "Salesforce Certified", "Kubernetes Certified", "CKA",
        "CKAD", "Certified Scrum", "CSM", "CSPO", "SAFe",
        "Microsoft Certified", "MCSA", "MCSE", "Six Sigma", "PCI DSS",
        "ISO", "ITIL", "TOGAF", "Data Science Certificate", "Machine Learning Certificate"
    ]

    found = set()
    search_text = cert_text + "\n" + text

    for cert in cert_keywords:
        if cert.lower() in search_text.lower():
            found.add(cert)

    # Extract lines from cert section that look like certifications
    if cert_text:
        for line in cert_text.split('\n'):
            line = line.strip()
            if 5 < len(line) < 120:
                # Likely a certification entry
                if not any(word in line.lower() for word in ["experience", "education", "skill"]):
                    found.add(line)

    return list(found)[:10]


def extract_languages(text: str) -> list:
    """Extract spoken languages from resume."""
    lang_keywords = [
        "English", "Spanish", "French", "German", "Mandarin", "Chinese",
        "Arabic", "Hindi", "Portuguese", "Russian", "Japanese", "Korean",
        "Italian", "Dutch", "Bengali", "Urdu", "Turkish", "Swedish",
        "Polish", "Ukrainian", "Hebrew", "Greek", "Indonesian", "Malay"
    ]
    sections = _split_into_sections(text)
    lang_text = ""
    for key in sections:
        if "language" in key:
            lang_text = sections[key]
            break

    if not lang_text:
        return []

    found = []
    for lang in lang_keywords:
        if lang.lower() in lang_text.lower():
            # Try to get proficiency level
            pattern = rf'{re.escape(lang)}[:\s]*([a-zA-Z]+)'
            match = re.search(pattern, lang_text, re.IGNORECASE)
            proficiency = match.group(1) if match and match.group(1).lower() not in [lang.lower()] else ""
            found.append({"language": lang, "proficiency": proficiency})

    return found


def get_education_level_score(education: list) -> tuple:
    """Return (score 0-1, label) for highest education level."""
    level_scores = {
        "Phd": 1.0, "Masters": 0.85, "Bachelors": 0.70,
        "Associate": 0.50, "Diploma": 0.40, "Highschool": 0.20, "Unknown": 0.30
    }
    if not education:
        return 0.30, "Unknown"

    best_score = 0.0
    best_label = "Unknown"
    for edu in education:
        lvl = edu.get("level", "Unknown")
        score = level_scores.get(lvl, 0.30)
        if score > best_score:
            best_score = score
            best_label = lvl

    return best_score, best_label


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse_resume(filepath: str) -> dict:
    """
    Parse a resume file and return a structured dictionary with all extracted information.
    """
    text = extract_text(filepath)
    if not text.strip():
        return {
            "error": "Could not extract text from resume",
            "filename": os.path.basename(filepath),
            "filepath": filepath
        }

    cleaned = clean_text(text)

    name = extract_name(cleaned)
    email = extract_email(cleaned)
    phone = extract_phone(cleaned)
    linkedin = extract_linkedin(cleaned)
    github = extract_github(cleaned)
    skills = extract_skills(cleaned)
    education = extract_education(cleaned)
    experience = extract_experience(cleaned)
    certifications = extract_certifications(cleaned)
    languages = extract_languages(cleaned)
    exp_years = calculate_experience_years(experience)
    edu_score, edu_level = get_education_level_score(education)

    # Word count and character metrics
    word_count = len(cleaned.split())
    has_summary = any(k in cleaned.lower() for k in ["summary", "objective", "profile", "about me"])

    return {
        "filename": os.path.basename(filepath),
        "filepath": filepath,
        "raw_text": cleaned,
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "skills": skills,
        "education": education,
        "experience": experience,
        "certifications": certifications,
        "languages": languages,
        "experience_years": exp_years,
        "education_level": edu_level,
        "education_score": edu_score,
        "word_count": word_count,
        "has_summary": has_summary,
        "skill_count": len(skills)
    }


def extract_required_skills_from_jd(jd_text: str) -> list:
    """Extract skills mentioned in a job description."""
    return extract_skills(jd_text)


def preprocess_for_vectorization(text: str) -> str:
    """Tokenize, lowercase, remove stopwords for TF-IDF."""
    try:
        stop_words = set(stopwords.words('english'))
    except Exception:
        stop_words = set()

    tokens = word_tokenize(text.lower())
    filtered = [t for t in tokens if t.isalpha() and t not in stop_words and len(t) > 1]
    return " ".join(filtered)

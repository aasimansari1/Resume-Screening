import re
import logging
import random
from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from resume_parser import preprocess_for_vectorization, extract_required_skills_from_jd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def calculate_tfidf_score(resume_text: str, jd_text: str) -> float:
    """TF-IDF cosine similarity between resume and job description."""
    if not resume_text.strip() or not jd_text.strip():
        return 0.0
    try:
        r_proc = preprocess_for_vectorization(resume_text)
        j_proc = preprocess_for_vectorization(jd_text)
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
        matrix = vectorizer.fit_transform([r_proc, j_proc])
        score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return float(np.clip(score, 0.0, 1.0))
    except Exception as e:
        logger.warning(f"TF-IDF scoring failed: {e}")
        return 0.0


def calculate_skills_score(candidate_skills: list, required_skills: list) -> float:
    """Jaccard-like overlap score between candidate skills and required skills."""
    if not required_skills:
        return 0.5  # Neutral score when no required skills specified

    candidate_lower = {s.lower() for s in candidate_skills}
    required_lower = {s.lower() for s in required_skills}

    matched = candidate_lower & required_lower
    score = len(matched) / len(required_lower) if required_lower else 0.0
    return float(np.clip(score, 0.0, 1.0))


def calculate_experience_score(candidate_years: float, required_years: float = 3.0) -> float:
    """Score based on years of experience relative to requirement."""
    if candidate_years <= 0:
        return 0.2
    if required_years <= 0:
        # No requirement specified — use a sigmoid around 3 years
        required_years = 3.0

    ratio = candidate_years / required_years
    if ratio >= 1.5:
        return 1.0
    elif ratio >= 1.0:
        return 0.85 + (ratio - 1.0) * 0.30
    elif ratio >= 0.7:
        return 0.60 + (ratio - 0.7) * 0.83
    else:
        return max(0.1, ratio * 0.85)


def calculate_ats_score(candidate: dict, jd_keywords: list) -> float:
    """ATS compatibility scoring based on keyword presence and structure."""
    score = 0.0
    max_score = 0.0

    text = candidate.get("raw_text", "").lower()

    # 1. Contact info completeness (20 pts)
    max_score += 20
    if candidate.get("email"):
        score += 8
    if candidate.get("phone"):
        score += 7
    if candidate.get("name") and candidate["name"] != "Unknown":
        score += 5

    # 2. Resume length (15 pts)
    max_score += 15
    word_count = candidate.get("word_count", 0)
    if 300 <= word_count <= 800:
        score += 15
    elif 200 <= word_count < 300 or 800 < word_count <= 1200:
        score += 10
    elif word_count > 1200:
        score += 5

    # 3. Section headers presence (20 pts)
    max_score += 20
    sections = ["experience", "education", "skills", "summary", "objective", "profile"]
    present = sum(1 for s in sections if s in text)
    score += min(20, present * 4)

    # 4. Keyword density from JD (30 pts)
    max_score += 30
    if jd_keywords:
        matched = sum(1 for kw in jd_keywords if kw.lower() in text)
        density = matched / len(jd_keywords)
        score += density * 30

    # 5. Skills section (15 pts)
    max_score += 15
    if candidate.get("skill_count", 0) >= 10:
        score += 15
    elif candidate.get("skill_count", 0) >= 5:
        score += 10
    elif candidate.get("skill_count", 0) > 0:
        score += 5

    return float(np.clip(score / max_score, 0.0, 1.0)) if max_score > 0 else 0.0


def calculate_keyword_match_details(candidate_skills: list, required_skills: list) -> dict:
    """Return matched and missing skills."""
    candidate_lower = {s.lower(): s for s in candidate_skills}
    required_lower = {s.lower(): s for s in required_skills}

    matched = [required_lower[s] for s in required_lower if s in candidate_lower]
    missing = [required_lower[s] for s in required_lower if s not in candidate_lower]
    extra = [candidate_lower[s] for s in candidate_lower if s not in required_lower]

    return {
        "matched": matched,
        "missing": missing,
        "extra": extra[:15],
        "match_count": len(matched),
        "total_required": len(required_skills)
    }


def extract_required_years(jd_text: str) -> float:
    """Extract required years of experience from JD."""
    patterns = [
        r'(\d+)\+?\s*years?\s+of\s+(?:work\s+)?experience',
        r'(\d+)\+?\s*years?\s+experience',
        r'minimum\s+(\d+)\s+years?',
        r'at\s+least\s+(\d+)\s+years?',
        r'(\d+)-\d+\s+years?',
    ]
    for pattern in patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return 3.0  # Default assumption


# ---------------------------------------------------------------------------
# Interview question generation
# ---------------------------------------------------------------------------

BEHAVIORAL_TEMPLATES = [
    "Tell me about a time when you had to {situation}.",
    "Describe a situation where you {situation}.",
    "Give me an example of when you successfully {situation}.",
    "Walk me through a time you had to {situation}.",
]

BEHAVIORAL_SITUATIONS = [
    "worked under tight deadlines",
    "resolved a conflict within your team",
    "took initiative on a challenging project",
    "had to learn a new technology quickly",
    "managed multiple priorities simultaneously",
    "handled a difficult stakeholder",
    "made a critical decision with limited information",
    "mentored a junior team member",
    "failed at something and what you learned",
    "improved a process or workflow",
]

TECHNICAL_TEMPLATES = {
    "python": [
        "Explain the difference between list comprehension and generator expressions.",
        "How do you manage dependencies in a Python project?",
        "Describe your experience with Python's asyncio or threading module.",
        "What is the GIL and how does it affect multithreaded Python programs?",
    ],
    "machine learning": [
        "How do you handle class imbalance in a dataset?",
        "Explain the bias-variance tradeoff.",
        "Describe your approach to feature engineering.",
        "What cross-validation strategies have you used?",
        "How do you evaluate model performance in production?",
    ],
    "deep learning": [
        "Explain the vanishing gradient problem and how to address it.",
        "Compare batch normalization vs layer normalization.",
        "How do you choose an optimizer for a neural network?",
        "Describe your experience fine-tuning pre-trained models.",
    ],
    "sql": [
        "What is the difference between INNER JOIN and LEFT JOIN?",
        "How do you optimize a slow SQL query?",
        "Explain the difference between HAVING and WHERE clauses.",
        "What are window functions and when would you use them?",
    ],
    "aws": [
        "Describe your experience with AWS services — which ones have you used most?",
        "How do you design a fault-tolerant architecture on AWS?",
        "What is the difference between EC2 and Lambda?",
        "How do you manage IAM roles and policies?",
    ],
    "docker": [
        "Explain the difference between an image and a container.",
        "How do you optimize Docker image size?",
        "Describe your experience with Docker Compose.",
        "What is a multi-stage build in Docker?",
    ],
    "react": [
        "Explain the virtual DOM and reconciliation.",
        "What is the difference between state and props?",
        "How do you manage global state in a React application?",
        "Describe your experience with React hooks.",
    ],
    "java": [
        "Explain the difference between an abstract class and an interface.",
        "How does garbage collection work in Java?",
        "Describe your experience with Java streams and lambdas.",
        "What design patterns have you used in Java projects?",
    ],
}

def generate_interview_questions(candidate: dict, jd_text: str) -> list:
    """Generate relevant interview questions for a candidate."""
    questions = []

    # 1. Behavioral questions (3 random)
    situations = random.sample(BEHAVIORAL_SITUATIONS, min(3, len(BEHAVIORAL_SITUATIONS)))
    for situation in situations:
        template = random.choice(BEHAVIORAL_TEMPLATES)
        questions.append({
            "type": "Behavioral",
            "question": template.format(situation=situation)
        })

    # 2. Technical questions based on matched skills
    candidate_skills_lower = [s.lower() for s in candidate.get("skills", [])]
    added_tech = 0
    for skill_key, skill_questions in TECHNICAL_TEMPLATES.items():
        if any(skill_key in s for s in candidate_skills_lower):
            selected = random.sample(skill_questions, min(2, len(skill_questions)))
            for q in selected:
                questions.append({"type": "Technical", "question": q})
                added_tech += 1
        if added_tech >= 6:
            break

    # 3. Experience-based questions
    experiences = candidate.get("experience", [])
    if experiences:
        recent = experiences[0]
        title = recent.get("title", "your previous role")[:60]
        questions.append({
            "type": "Experience",
            "question": f"Can you walk me through your responsibilities in '{title}'?"
        })
        questions.append({
            "type": "Experience",
            "question": "What was the most challenging technical problem you solved in your last position?"
        })

    # 4. Role-specific questions from JD keywords
    jd_lower = jd_text.lower()
    if "leadership" in jd_lower or "team lead" in jd_lower or "manager" in jd_lower:
        questions.append({
            "type": "Leadership",
            "question": "How do you motivate a team during challenging project phases?"
        })
        questions.append({
            "type": "Leadership",
            "question": "Describe your experience managing stakeholder expectations."
        })

    if "startup" in jd_lower or "fast-paced" in jd_lower:
        questions.append({
            "type": "Culture Fit",
            "question": "How do you thrive in ambiguous, fast-changing environments?"
        })

    # 5. General closing question
    questions.append({
        "type": "General",
        "question": "Where do you see yourself in the next 3-5 years, and how does this role fit your career plan?"
    })

    return questions[:12]


# ---------------------------------------------------------------------------
# Resume improvement suggestions
# ---------------------------------------------------------------------------

def generate_improvement_suggestions(candidate: dict, jd_text: str) -> list:
    """Generate actionable resume improvement suggestions."""
    suggestions = []
    required_skills = extract_required_skills_from_jd(jd_text)
    candidate_skills_lower = {s.lower() for s in candidate.get("skills", [])}

    # Missing required skills
    missing_skills = [s for s in required_skills if s.lower() not in candidate_skills_lower]
    if missing_skills[:5]:
        suggestions.append({
            "category": "Skills Gap",
            "priority": "High",
            "suggestion": f"Add these in-demand skills to your resume (or acquire them): {', '.join(missing_skills[:5])}",
            "impact": "Increases keyword match with the job description significantly"
        })

    # Contact info
    if not candidate.get("email"):
        suggestions.append({
            "category": "Contact Info",
            "priority": "High",
            "suggestion": "Add your professional email address prominently at the top.",
            "impact": "Recruiters cannot contact you without it"
        })

    if not candidate.get("phone"):
        suggestions.append({
            "category": "Contact Info",
            "priority": "Medium",
            "suggestion": "Include a phone number for direct contact.",
            "impact": "Speeds up recruiter outreach"
        })

    if not candidate.get("linkedin"):
        suggestions.append({
            "category": "Online Presence",
            "priority": "Medium",
            "suggestion": "Add your LinkedIn profile URL to stand out.",
            "impact": "LinkedIn profiles increase recruiter trust and context"
        })

    # Summary section
    if not candidate.get("has_summary"):
        suggestions.append({
            "category": "Structure",
            "priority": "High",
            "suggestion": "Add a 2-3 sentence professional summary tailored to this role.",
            "impact": "Helps recruiters quickly understand your value proposition"
        })

    # Word count
    wc = candidate.get("word_count", 0)
    if wc < 200:
        suggestions.append({
            "category": "Content",
            "priority": "High",
            "suggestion": "Your resume appears too short. Add more details about your experience, achievements, and projects.",
            "impact": "Thin resumes often get auto-rejected by ATS systems"
        })
    elif wc > 1200:
        suggestions.append({
            "category": "Conciseness",
            "priority": "Medium",
            "suggestion": "Your resume is quite long. Consider trimming it to 1-2 pages focusing on the most relevant experience.",
            "impact": "Shorter, focused resumes are easier to review quickly"
        })

    # Skills count
    if candidate.get("skill_count", 0) < 5:
        suggestions.append({
            "category": "Skills",
            "priority": "High",
            "suggestion": "Add a dedicated skills section with at least 8-12 relevant technical and soft skills.",
            "impact": "ATS systems heavily weight skills sections for ranking"
        })

    # Certifications
    if not candidate.get("certifications"):
        suggestions.append({
            "category": "Credentials",
            "priority": "Low",
            "suggestion": "Consider adding relevant certifications (e.g., AWS, Google, Microsoft, PMP) to boost credibility.",
            "impact": "Certifications differentiate you from candidates with similar experience"
        })

    # Quantify achievements
    text = candidate.get("raw_text", "")
    if not re.search(r'\b\d+%\b|\b\d+x\b|\$[\d,]+|\b\d+\s+(users|customers|projects|teams)', text, re.IGNORECASE):
        suggestions.append({
            "category": "Impact",
            "priority": "High",
            "suggestion": "Quantify your achievements with numbers (e.g., 'Reduced latency by 40%', 'Led a team of 8 engineers', 'Grew revenue by $200K').",
            "impact": "Quantified achievements are 2x more convincing to hiring managers"
        })

    # GitHub
    if not candidate.get("github"):
        suggestions.append({
            "category": "Online Presence",
            "priority": "Low",
            "suggestion": "Add your GitHub profile to showcase your code and projects.",
            "impact": "Essential for technical roles — shows real work"
        })

    return suggestions[:8]


# ---------------------------------------------------------------------------
# Main ranking function
# ---------------------------------------------------------------------------

def rank_candidates(
    candidates: List[Dict[str, Any]],
    jd_text: str,
    weights: Dict[str, float] = None
) -> List[Dict[str, Any]]:
    """
    Score and rank all candidates against a job description.
    Returns candidates sorted by final_score descending.
    """
    if weights is None:
        weights = {
            "tfidf": 0.35,
            "skills": 0.35,
            "experience": 0.20,
            "education": 0.10
        }

    required_skills = extract_required_skills_from_jd(jd_text)
    required_years = extract_required_years(jd_text)
    jd_keywords = [s.lower() for s in required_skills]

    scored = []
    for candidate in candidates:
        if candidate.get("error"):
            candidate["scores"] = {}
            candidate["final_score"] = 0.0
            candidate["match_percentage"] = 0.0
            candidate["rank"] = 999
            scored.append(candidate)
            continue

        raw_text = candidate.get("raw_text", "")
        candidate_skills = candidate.get("skills", [])
        exp_years = candidate.get("experience_years", 0.0)
        edu_score = candidate.get("education_score", 0.3)

        tfidf = calculate_tfidf_score(raw_text, jd_text)
        skills = calculate_skills_score(candidate_skills, required_skills)
        experience = calculate_experience_score(exp_years, required_years)
        ats = calculate_ats_score(candidate, jd_keywords)

        final = (
            weights["tfidf"] * tfidf +
            weights["skills"] * skills +
            weights["experience"] * experience +
            weights["education"] * edu_score
        )

        keyword_details = calculate_keyword_match_details(candidate_skills, required_skills)

        candidate["scores"] = {
            "tfidf_score": round(tfidf * 100, 1),
            "skills_score": round(skills * 100, 1),
            "experience_score": round(experience * 100, 1),
            "education_score": round(edu_score * 100, 1),
            "ats_score": round(ats * 100, 1),
        }
        candidate["final_score"] = round(final * 100, 1)
        candidate["match_percentage"] = round(final * 100, 1)
        candidate["keyword_details"] = keyword_details
        candidate["required_years"] = required_years
        candidate["required_skills"] = required_skills

        scored.append(candidate)

    # Sort by final score descending
    scored.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    # Assign ranks
    for i, c in enumerate(scored):
        c["rank"] = i + 1

    # Generate interview questions and suggestions for top candidates
    for candidate in scored[:10]:
        if not candidate.get("error"):
            candidate["interview_questions"] = generate_interview_questions(candidate, jd_text)
            candidate["improvement_suggestions"] = generate_improvement_suggestions(candidate, jd_text)

    return scored


def compute_analytics(candidates: list) -> dict:
    """Compute aggregate analytics from ranked candidates."""
    valid = [c for c in candidates if not c.get("error")]
    if not valid:
        return {}

    scores = [c["final_score"] for c in valid]
    all_skills = []
    for c in valid:
        all_skills.extend(c.get("skills", []))

    from collections import Counter
    skill_counts = Counter(all_skills)
    top_skills = skill_counts.most_common(15)

    score_dist = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    for s in scores:
        if s <= 25:
            score_dist["0-25"] += 1
        elif s <= 50:
            score_dist["26-50"] += 1
        elif s <= 75:
            score_dist["51-75"] += 1
        else:
            score_dist["76-100"] += 1

    exp_levels = {"Junior (0-2y)": 0, "Mid (2-5y)": 0, "Senior (5-8y)": 0, "Lead (8+y)": 0}
    for c in valid:
        yrs = c.get("experience_years", 0)
        if yrs < 2:
            exp_levels["Junior (0-2y)"] += 1
        elif yrs < 5:
            exp_levels["Mid (2-5y)"] += 1
        elif yrs < 8:
            exp_levels["Senior (5-8y)"] += 1
        else:
            exp_levels["Lead (8+y)"] += 1

    edu_dist = {}
    for c in valid:
        lvl = c.get("education_level", "Unknown")
        edu_dist[lvl] = edu_dist.get(lvl, 0) + 1

    return {
        "total_candidates": len(valid),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "top_score": round(max(scores), 1) if scores else 0,
        "min_score": round(min(scores), 1) if scores else 0,
        "shortlisted": sum(1 for s in scores if s >= 70),
        "score_distribution": score_dist,
        "top_skills": [{"skill": k, "count": v} for k, v in top_skills],
        "experience_levels": exp_levels,
        "education_distribution": edu_dist
    }

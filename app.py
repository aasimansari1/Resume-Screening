import os
import uuid
import json
import logging
import csv
import io
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, send_file, flash, Response
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required,
    current_user, UserMixin
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from resume_parser import parse_resume, extract_required_skills_from_jd
from rank_candidates import rank_candidates, compute_analytics

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)
os.makedirs(os.path.dirname(app.config['RESULTS_FILE']), exist_ok=True)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ---------------------------------------------------------------------------
# Simple user model (no DB required)
# ---------------------------------------------------------------------------

class User(UserMixin):
    def __init__(self, user_id, username, role='admin'):
        self.id = user_id
        self.username = username
        self.role = role

USERS = {
    app.config['ADMIN_USERNAME']: {
        'id': '1',
        'password_hash': generate_password_hash(app.config['ADMIN_PASSWORD']),
        'role': 'admin'
    }
}

@login_manager.user_loader
def load_user(user_id):
    for username, data in USERS.items():
        if data['id'] == user_id:
            return User(user_id=data['id'], username=username, role=data['role'])
    return None


# ---------------------------------------------------------------------------
# Results persistence
# ---------------------------------------------------------------------------

def load_results() -> dict:
    path = app.config['RESULTS_FILE']
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_results(results: dict):
    path = app.config['RESULTS_FILE']
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save results: {e}")


def allowed_file(filename: str) -> bool:
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    )


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user_data = USERS.get(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_id=user_data['id'], username=username, role=user_data['role'])
            login_user(user, remember=request.form.get('remember'))
            next_page = request.args.get('next')
            flash('Login successful! Welcome back.', 'success')
            return redirect(next_page or url_for('index'))
        flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Main routes
# ---------------------------------------------------------------------------

@app.route('/')
@login_required
def index():
    results = load_results()
    has_results = bool(results.get('candidates'))
    return render_template('index.html', has_results=has_results, results=results)


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle resume uploads and job description, then run analysis."""
    # Job description
    jd_text = request.form.get('job_description', '').strip()
    jd_file = request.files.get('jd_file')

    if jd_file and jd_file.filename:
        from resume_parser import extract_text
        jd_filename = secure_filename(jd_file.filename)
        jd_path = os.path.join(app.config['UPLOAD_FOLDER'], f"jd_{uuid.uuid4().hex}_{jd_filename}")
        jd_file.save(jd_path)
        jd_text = extract_text(jd_path)
        os.remove(jd_path)

    if not jd_text:
        flash('Please provide a job description (text or file).', 'danger')
        return redirect(url_for('index'))

    # Resume files
    resume_files = request.files.getlist('resumes')
    if not resume_files or all(f.filename == '' for f in resume_files):
        flash('Please upload at least one resume.', 'danger')
        return redirect(url_for('index'))

    # Save and parse resumes
    session_id = uuid.uuid4().hex
    saved_paths = []
    parse_errors = []

    for resume_file in resume_files:
        if resume_file and resume_file.filename and allowed_file(resume_file.filename):
            filename = secure_filename(resume_file.filename)
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            resume_file.save(filepath)
            saved_paths.append(filepath)
        elif resume_file and resume_file.filename:
            parse_errors.append(f"Unsupported file format: {resume_file.filename}")

    if not saved_paths:
        flash('No valid resume files found. Supported formats: PDF, DOCX.', 'danger')
        return redirect(url_for('index'))

    # Parse all resumes
    candidates = []
    for path in saved_paths:
        try:
            logger.info(f"Parsing resume: {path}")
            parsed = parse_resume(path)
            parsed['id'] = uuid.uuid4().hex
            candidates.append(parsed)
        except Exception as e:
            logger.error(f"Failed to parse {path}: {e}")
            parse_errors.append(f"Failed to parse {os.path.basename(path)}: {str(e)}")

    if not candidates:
        flash('Could not parse any resumes. Please check file formats.', 'danger')
        return redirect(url_for('index'))

    # Rank candidates
    try:
        ranked = rank_candidates(candidates, jd_text)
        analytics = compute_analytics(ranked)
    except Exception as e:
        logger.error(f"Ranking failed: {e}")
        flash(f'Analysis error: {str(e)}', 'danger')
        return redirect(url_for('index'))

    # Required skills extracted from JD
    required_skills = extract_required_skills_from_jd(jd_text)

    # Store results
    results = {
        'session_id': session_id,
        'job_description': jd_text,
        'required_skills': required_skills,
        'candidates': ranked,
        'analytics': analytics,
        'created_at': datetime.now().isoformat(),
        'total_uploaded': len(saved_paths),
        'parse_errors': parse_errors
    }
    save_results(results)
    session['session_id'] = session_id

    if parse_errors:
        for err in parse_errors:
            flash(err, 'warning')

    flash(f'Successfully analyzed {len(ranked)} candidate(s).', 'success')
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    results = load_results()
    if not results.get('candidates'):
        flash('No analysis data found. Please upload resumes first.', 'info')
        return redirect(url_for('index'))

    analytics = results.get('analytics', {})
    top_candidates = results['candidates'][:5]
    return render_template(
        'dashboard.html',
        results=results,
        analytics=analytics,
        top_candidates=top_candidates,
        candidates=results['candidates']
    )


@app.route('/candidates')
@login_required
def candidates():
    results = load_results()
    if not results.get('candidates'):
        flash('No candidates found. Please run an analysis first.', 'info')
        return redirect(url_for('index'))

    # Filtering
    min_score = float(request.args.get('min_score', 0))
    search_q = request.args.get('q', '').lower().strip()
    sort_by = request.args.get('sort', 'rank')

    all_candidates = results['candidates']

    if min_score > 0:
        all_candidates = [c for c in all_candidates if c.get('final_score', 0) >= min_score]
    if search_q:
        all_candidates = [
            c for c in all_candidates
            if search_q in c.get('name', '').lower()
            or search_q in c.get('email', '').lower()
            or any(search_q in s.lower() for s in c.get('skills', []))
        ]
    if sort_by == 'name':
        all_candidates.sort(key=lambda x: x.get('name', '').lower())
    elif sort_by == 'score':
        all_candidates.sort(key=lambda x: x.get('final_score', 0), reverse=True)

    return render_template(
        'candidates.html',
        candidates=all_candidates,
        results=results,
        min_score=min_score,
        search_q=search_q,
        sort_by=sort_by
    )


@app.route('/candidate/<candidate_id>')
@login_required
def candidate_detail(candidate_id):
    results = load_results()
    candidate = next(
        (c for c in results.get('candidates', []) if c.get('id') == candidate_id),
        None
    )
    if not candidate:
        flash('Candidate not found.', 'danger')
        return redirect(url_for('candidates'))

    return render_template(
        'candidate_detail.html',
        candidate=candidate,
        results=results
    )


# ---------------------------------------------------------------------------
# API endpoints for charts / async
# ---------------------------------------------------------------------------

@app.route('/api/analytics')
@login_required
def api_analytics():
    results = load_results()
    analytics = results.get('analytics', {})
    return jsonify(analytics)


@app.route('/api/scores')
@login_required
def api_scores():
    results = load_results()
    candidates = results.get('candidates', [])
    data = [
        {
            'name': c.get('name', 'Unknown')[:20],
            'score': c.get('final_score', 0),
            'skills_score': c.get('scores', {}).get('skills_score', 0),
            'tfidf_score': c.get('scores', {}).get('tfidf_score', 0),
            'experience_score': c.get('scores', {}).get('experience_score', 0),
            'ats_score': c.get('scores', {}).get('ats_score', 0),
            'rank': c.get('rank', 0)
        }
        for c in candidates[:20]
    ]
    return jsonify(data)


@app.route('/api/regenerate-questions/<candidate_id>', methods=['POST'])
@login_required
def regenerate_questions(candidate_id):
    results = load_results()
    candidate = next(
        (c for c in results.get('candidates', []) if c.get('id') == candidate_id),
        None
    )
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404

    from rank_candidates import generate_interview_questions
    questions = generate_interview_questions(candidate, results.get('job_description', ''))
    candidate['interview_questions'] = questions
    save_results(results)
    return jsonify({'questions': questions})


# ---------------------------------------------------------------------------
# Export routes
# ---------------------------------------------------------------------------

@app.route('/export/csv')
@login_required
def export_csv():
    results = load_results()
    candidates = results.get('candidates', [])
    if not candidates:
        flash('No data to export.', 'warning')
        return redirect(url_for('dashboard'))

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        'Rank', 'Name', 'Email', 'Phone', 'Final Score (%)',
        'TF-IDF Score', 'Skills Score', 'Experience Score',
        'Education Score', 'ATS Score',
        'Experience Years', 'Education Level',
        'Skills Count', 'Certifications',
        'LinkedIn', 'GitHub', 'Filename'
    ]
    writer.writerow(headers)

    for c in candidates:
        scores = c.get('scores', {})
        writer.writerow([
            c.get('rank', ''),
            c.get('name', ''),
            c.get('email', ''),
            c.get('phone', ''),
            c.get('final_score', 0),
            scores.get('tfidf_score', ''),
            scores.get('skills_score', ''),
            scores.get('experience_score', ''),
            scores.get('education_score', ''),
            scores.get('ats_score', ''),
            c.get('experience_years', ''),
            c.get('education_level', ''),
            c.get('skill_count', 0),
            '; '.join(c.get('certifications', [])[:3]),
            c.get('linkedin', ''),
            c.get('github', ''),
            c.get('filename', '')
        ])

    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=candidate_ranking_{timestamp}.csv'
        }
    )


@app.route('/export/pdf')
@login_required
def export_pdf():
    """Generate a PDF ranking report using ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph,
            Spacer, HRFlowable
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        flash('ReportLab not installed. Please use CSV export instead.', 'warning')
        return redirect(url_for('dashboard'))

    results = load_results()
    candidates = results.get('candidates', [])
    if not candidates:
        flash('No data to export.', 'warning')
        return redirect(url_for('dashboard'))

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_path = os.path.join(app.config['EXPORT_FOLDER'], f'ranking_report_{timestamp}.pdf')

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                  alignment=TA_CENTER, fontSize=18,
                                  textColor=colors.HexColor('#4f46e5'))
    elements.append(Paragraph("AI Resume Screening Report", title_style))
    elements.append(Spacer(1, 0.3*cm))

    # Metadata
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'],
                                 alignment=TA_CENTER, fontSize=9,
                                 textColor=colors.grey)
    analytics = results.get('analytics', {})
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')} | "
        f"Total Candidates: {analytics.get('total_candidates', 0)} | "
        f"Avg Score: {analytics.get('avg_score', 0)}%",
        meta_style
    ))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#4f46e5')))
    elements.append(Spacer(1, 0.5*cm))

    # Table
    table_data = [[
        'Rank', 'Name', 'Email', 'Score', 'Skills', 'Exp.Yrs', 'ATS'
    ]]
    row_colors = []
    for i, c in enumerate(candidates[:30]):
        score = c.get('final_score', 0)
        scores = c.get('scores', {})
        table_data.append([
            str(c.get('rank', '')),
            c.get('name', '')[:25],
            c.get('email', '')[:28],
            f"{score:.1f}%",
            f"{scores.get('skills_score', 0):.1f}%",
            str(c.get('experience_years', '')),
            f"{scores.get('ats_score', 0):.1f}%"
        ])
        if score >= 75:
            row_colors.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.HexColor('#d1fae5')))
        elif score >= 50:
            row_colors.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.HexColor('#fef3c7')))

    col_widths = [1.5*cm, 4.5*cm, 5.0*cm, 2.0*cm, 2.0*cm, 1.8*cm, 1.8*cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (2, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ] + row_colors)
    table.setStyle(table_style)
    elements.append(table)

    # Footer legend
    elements.append(Spacer(1, 0.5*cm))
    legend_style = ParagraphStyle('Legend', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
    elements.append(Paragraph(
        "Score Legend: <font color='#059669'>Green ≥75%</font> (Highly Recommended) | "
        "<font color='#d97706'>Yellow 50-74%</font> (Consider) | White &lt;50% (Review Carefully)",
        legend_style
    ))

    doc.build(elements)

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f'ranking_report_{timestamp}.pdf',
        mimetype='application/pdf'
    )


# ---------------------------------------------------------------------------
# Clear / reset
# ---------------------------------------------------------------------------

@app.route('/clear', methods=['POST'])
@login_required
def clear_results():
    """Clear all analysis results and uploaded resumes."""
    results = load_results()
    # Delete uploaded resume files
    for c in results.get('candidates', []):
        fp = c.get('filepath', '')
        if fp and os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception:
                pass

    save_results({})
    flash('All results cleared successfully.', 'success')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message="Page not found"), 404

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 16 MB.', 'danger')
    return redirect(url_for('index'))

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message="Internal server error"), 500


# ---------------------------------------------------------------------------
# Template context processors
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    results = load_results()
    return {
        'app_name': 'AI Resume Screener',
        'candidate_count': len(results.get('candidates', [])),
        'has_results': bool(results.get('candidates'))
    }


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)

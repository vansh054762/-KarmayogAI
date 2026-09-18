"""
KarmayogAI — Main Flask Application Entry Point
"""
from flask import Flask, send_from_directory, redirect, jsonify, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

from models.database import db
from routes.auth import auth_bp
from routes.assessment import assessment_bp
from routes.recommendations import recommendations_bp
from routes.quiz_generator import quiz_bp
from routes.igot import igot_bp
from routes.progress import progress_bp
from routes.admin import admin_bp
from routes.ml import ml_bp

load_dotenv()


def create_app():
    app = Flask(__name__, static_folder=None)

    # ── Config ────────────────────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'karmayogai-secret')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///karmayogai.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # File upload limits — Flask enforces this globally before any route runs
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB hard cap

    app.config['UPLOAD_FOLDER'] = os.path.abspath(
        os.getenv('UPLOAD_FOLDER', '../uploads')
    )

    # JWT cookie settings (for future cookie-based auth)
    app.config['JWT_COOKIE_SECURE'] = os.getenv('FLASK_ENV', 'development') == 'production'
    app.config['JWT_COOKIE_SAMESITE'] = 'Strict'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = True

    # Static frontend folder
    FRONTEND_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static')
    )

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Extensions ────────────────────────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": os.getenv('ALLOWED_ORIGINS', '*')}})
    JWTManager(app)
    db.init_app(app)

    # ── Blueprints ────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp,            url_prefix='/api/auth')
    app.register_blueprint(assessment_bp,      url_prefix='/api/assessment')
    app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')
    app.register_blueprint(quiz_bp,            url_prefix='/api/quiz')
    app.register_blueprint(igot_bp,            url_prefix='/api/igot')
    app.register_blueprint(progress_bp,        url_prefix='/api/progress')
    app.register_blueprint(admin_bp,           url_prefix='/api/admin')
    app.register_blueprint(ml_bp,              url_prefix='/api/ml')

    # ── Security Headers (applied to every response) ──────────────────────
    @app.after_request
    def set_security_headers(response):
        from flask import request as _request
        # Prevent browsers from MIME-sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Block page from being embedded in iframes (clickjacking)
        response.headers['X-Frame-Options'] = 'DENY'
        # Enable browser XSS filter
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Strict referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Permissions policy — disable unused browser features
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), payment=()'
        )
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        # Force HTTPS in production
        if os.getenv('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )
        # No caching for API responses
        if _request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
        return response

    # ── Handle oversized uploads gracefully ───────────────────────────────
    @app.errorhandler(413)
    def request_entity_too_large(e):
        from flask import request as _request
        from utils.audit import log_security
        log_security('file_too_large', details={'path': _request.path})
        return jsonify({'error': 'File too large. Maximum allowed size is 10 MB.'}), 413

    # ── CSRF token endpoint ───────────────────────────────────────────────
    @app.route('/api/csrf-token', methods=['GET'])
    def csrf_token():
        from utils.security import generate_csrf_token
        token = generate_csrf_token()
        resp = make_response(jsonify({'csrf_token': token}))
        resp.set_cookie(
            'csrf_token', token,
            httponly=False,   # must be readable by JS for double-submit
            secure=os.getenv('FLASK_ENV') == 'production',
            samesite='Strict',
            max_age=3600
        )
        return resp

    # ── Serve HTML frontend pages ──────────────────────────────────────────
    def serve_page(filename):
        resp = make_response(send_from_directory(FRONTEND_DIR, filename))
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp

    @app.route('/')
    def home_page():
        return serve_page('index.html')

    @app.route('/login')
    def login_page():
        return serve_page('login.html')

    @app.route('/register')
    def register_page():
        return serve_page('register.html')

    @app.route('/dashboard')
    def dashboard_page():
        return serve_page('dashboard.html')

    @app.route('/assessment')
    def assessment_page():
        return serve_page('assessment.html')

    @app.route('/recommendations')
    def recommendations_page():
        return serve_page('recommendations.html')

    @app.route('/quiz-generator')
    def quiz_generator_page():
        return serve_page('quiz-generator.html')

    @app.route('/quiz/<int:quiz_id>')
    def quiz_take_page(quiz_id):
        return serve_page('quiz-take.html')

    @app.route('/learning-paths')
    def learning_paths_page():
        return serve_page('learning-paths.html')

    @app.route('/progress')
    def progress_page():
        return serve_page('progress.html')

    @app.route('/igot')
    def igot_page():
        return serve_page('igot.html')

    @app.route('/admin')
    def admin_page():
        return serve_page('admin.html')

    # Serve static assets with no-cache headers
    @app.route('/static/<path:filename>')
    def static_files(filename):
        resp = make_response(send_from_directory(FRONTEND_DIR, filename))
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp
    # ──────────────────────────────────────────────────────────────────────

    with app.app_context():
        db.create_all()
        _seed_data()

    return app


def _seed_data():
    """Seed initial competencies, questions, and courses if DB is empty."""
    from models.database import Competency, Question, Course
    import json

    if Competency.query.first():
        return  # Already seeded

    competencies = [
        {'name': 'Data Analysis', 'domain': 'Statistics', 'description': 'Ability to collect, process, and interpret data'},
        {'name': 'Statistical Methods', 'domain': 'Statistics', 'description': 'Knowledge of statistical techniques and their application'},
        {'name': 'Data Visualization', 'domain': 'Data Science', 'description': 'Creating meaningful charts and dashboards'},
        {'name': 'Machine Learning Basics', 'domain': 'AI/ML', 'description': 'Foundational ML concepts and algorithms'},
        {'name': 'Policy Analysis', 'domain': 'Governance', 'description': 'Analyzing and evaluating government policies'},
        {'name': 'Public Administration', 'domain': 'Governance', 'description': 'Principles of effective public service delivery'},
        {'name': 'Financial Management', 'domain': 'Finance', 'description': 'Budgeting, accounting, and fiscal management'},
        {'name': 'Leadership & Management', 'domain': 'Soft Skills', 'description': 'Team leadership and organizational management'},
    ]

    comp_objs = []
    for c in competencies:
        obj = Competency(name=c['name'], domain=c['domain'], description=c['description'])
        db.session.add(obj)
        comp_objs.append(obj)
    db.session.flush()

    # Questions per competency
    questions_data = {
        0: [  # Data Analysis
            {'text': 'What is the primary purpose of exploratory data analysis (EDA)?', 'options': ['To train ML models', 'To summarize and visualize data characteristics', 'To deploy applications', 'To write SQL queries'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'EDA helps understand data distribution, patterns, and anomalies before modeling.'},
            {'text': 'Which measure is most resistant to outliers?', 'options': ['Mean', 'Standard deviation', 'Median', 'Variance'], 'correct': 2, 'difficulty': 'medium', 'explanation': 'Median is not affected by extreme values unlike mean.'},
            {'text': 'In a dataset with skewed distribution, which central tendency measure is preferred?', 'options': ['Mean', 'Mode', 'Median', 'Range'], 'correct': 2, 'difficulty': 'medium', 'explanation': 'Median represents the central value without being pulled by skew.'},
            {'text': 'What does a correlation coefficient of -0.9 indicate?', 'options': ['No correlation', 'Weak positive', 'Strong negative correlation', 'Weak negative'], 'correct': 2, 'difficulty': 'hard', 'explanation': 'Close to -1 means strong inverse relationship between variables.'},
            {'text': 'Which Python library is most commonly used for data manipulation?', 'options': ['NumPy', 'Pandas', 'Matplotlib', 'Seaborn'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Pandas provides DataFrames ideal for data manipulation.'},
        ],
        1: [  # Statistical Methods
            {'text': 'What is a p-value in hypothesis testing?', 'options': ['Probability of null hypothesis being true', 'Probability of observing results if null is true', 'Type I error rate', 'Confidence interval width'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'P-value is the probability of observing results as extreme as the data, assuming H0 is true.'},
            {'text': 'What does a 95% confidence interval mean?', 'options': ['95% of data lies in this range', '95% chance the interval contains the true parameter', 'The parameter equals the midpoint 95% of the time', 'Sample size is 95% accurate'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'If we repeated the study many times, 95% of such intervals would contain the true value.'},
            {'text': 'Which test compares means of two independent groups?', 'options': ['Chi-square test', 'ANOVA', 'Independent t-test', 'Pearson correlation'], 'correct': 2, 'difficulty': 'medium', 'explanation': 'Independent samples t-test compares means of two unrelated groups.'},
            {'text': 'What is Type II error?', 'options': ['Rejecting a true null hypothesis', 'Failing to reject a false null hypothesis', 'Accepting the alternative', 'Sample bias'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'Type II (beta error) is a false negative — missing a real effect.'},
            {'text': 'Normal distribution is characterized by which parameters?', 'options': ['Mean and Variance', 'Median and Range', 'Mode and Std Dev', 'Mean and Mode'], 'correct': 0, 'difficulty': 'easy', 'explanation': 'Normal distribution is fully defined by its mean (μ) and variance (σ²).'},
        ],
        2: [  # Data Visualization
            {'text': 'Which chart type is best for showing distribution of a continuous variable?', 'options': ['Pie chart', 'Bar chart', 'Histogram', 'Line chart'], 'correct': 2, 'difficulty': 'easy', 'explanation': 'Histograms show frequency distribution of continuous data.'},
            {'text': 'What is the purpose of a box plot?', 'options': ['Show trends over time', 'Display 5-number summary and outliers', 'Compare categories', 'Show correlations'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Box plots show min, Q1, median, Q3, max and outliers.'},
            {'text': 'When should you use a scatter plot?', 'options': ['To show proportions', 'To show relationship between two numeric variables', 'To compare frequencies', 'To track change over time'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Scatter plots reveal correlations between two continuous variables.'},
            {'text': 'What does a heat map visualize?', 'options': ['Geographic temperature', 'Matrix data with color intensity', 'Time series trends', 'Categorical comparisons'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Heat maps use color to represent values in a matrix, useful for correlation matrices.'},
            {'text': 'Which principle should guide dashboard design?', 'options': ['Use as many colors as possible', 'Maximize data-ink ratio', 'Include every available metric', 'Use 3D charts always'], 'correct': 1, 'difficulty': 'hard', 'explanation': "Tufte's data-ink ratio principle: maximize data content, minimize non-essential ink."},
        ],
        3: [  # Machine Learning
            {'text': 'What is overfitting in machine learning?', 'options': ['Model too simple', 'Model performs well on training but poorly on test data', 'Low training accuracy', 'Missing data problem'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Overfitting: model memorizes training data but fails to generalize.'},
            {'text': 'Which algorithm is used for classification tasks?', 'options': ['Linear regression', 'K-means clustering', 'Random Forest', 'PCA'], 'correct': 2, 'difficulty': 'easy', 'explanation': 'Random Forest is a supervised classification (and regression) algorithm.'},
            {'text': 'What does cross-validation help prevent?', 'options': ['Underfitting', 'Data leakage', 'Overfitting', 'Feature scaling issues'], 'correct': 2, 'difficulty': 'medium', 'explanation': 'Cross-validation estimates generalization performance to detect overfitting.'},
            {'text': 'What is the purpose of feature scaling?', 'options': ['Reduce features', 'Ensure features contribute equally to distance-based models', 'Remove outliers', 'Increase training speed only'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Scaling ensures no feature dominates due to magnitude differences.'},
            {'text': 'Which metric is best for imbalanced classification datasets?', 'options': ['Accuracy', 'F1 Score', 'Mean Squared Error', 'R-squared'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'F1 balances precision and recall, important when classes are unequal.'},
        ],
        4: [  # Policy Analysis
            {'text': 'What is the first step in policy analysis?', 'options': ['Policy implementation', 'Problem identification', 'Stakeholder engagement', 'Budget allocation'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Clear problem identification is the foundation of effective policy analysis.'},
            {'text': 'What is cost-benefit analysis in policy?', 'options': ['Comparing costs only', 'Evaluating monetary and non-monetary costs vs benefits', 'Budget preparation', 'Financial auditing'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'CBA weighs all costs against all benefits to determine net policy value.'},
            {'text': 'What does evidence-based policy making rely on?', 'options': ['Political opinions', 'Empirical research and data', 'Historical precedent only', 'Expert intuition'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Evidence-based policy uses rigorous research to inform decisions.'},
            {'text': 'What is regulatory impact assessment?', 'options': ['Budget review', 'Analysis of regulation effects on economy and society', 'Environmental audit', 'Staff performance review'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'RIA evaluates the anticipated effects of proposed regulations.'},
            {'text': 'Which framework evaluates policy alternatives systematically?', 'options': ['SWOT analysis', 'Multi-criteria analysis', 'PESTLE analysis', 'Both B and C'], 'correct': 3, 'difficulty': 'medium', 'explanation': 'MCA and PESTLE together provide comprehensive policy evaluation.'},
        ],
        5: [  # Public Administration
            {'text': 'What is the primary goal of e-governance?', 'options': ['Reduce government size', 'Use ICT to improve public service delivery', 'Automate all jobs', 'Increase taxation'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'E-governance leverages technology to deliver transparent, efficient services.'},
            {'text': 'What does RTI stand for in Indian governance?', 'options': ['Right to Information', 'Return to Investment', 'Revenue Transfer Initiative', 'Regulatory Technical Input'], 'correct': 0, 'difficulty': 'easy', 'explanation': 'RTI Act 2005 empowers citizens to access government information.'},
            {'text': 'What is the principle of subsidiarity?', 'options': ['Central authority controls all', 'Decisions made at lowest competent level', 'Supreme court precedent', 'Federal budgeting'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'Subsidiarity delegates decisions to the most local appropriate level.'},
            {'text': 'What is outcome budgeting?', 'options': ['Budgeting by department', 'Linking expenditure to measurable outcomes', 'Zero-based budgeting', 'Incremental budgeting'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Outcome budgeting ties funds to expected results and performance metrics.'},
            {'text': 'Which of these is a feature of good governance?', 'options': ['Opacity', 'Accountability', 'Centralization', 'Delay'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Good governance includes accountability, transparency, rule of law, and participation.'},
        ],
        6: [  # Financial Management
            {'text': 'What is the difference between capital and revenue expenditure?', 'options': ['No difference', 'Capital creates long-term assets; revenue is for current operations', 'Revenue is larger', 'Capital is annual'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Capital expenditure creates assets; revenue expenditure maintains operations.'},
            {'text': 'What is a fiscal deficit?', 'options': ['Trade imbalance', 'Excess of government expenditure over revenue', 'Foreign debt', 'Corporate losses'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Fiscal deficit = total expenditure - total revenue (excluding borrowings).'},
            {'text': 'What does PFMS stand for?', 'options': ['Public Fund Management System', 'Policy Finance Monitoring Service', 'Public Financial Management System', 'Program for Monetary Stability'], 'correct': 2, 'difficulty': 'easy', 'explanation': 'PFMS tracks government funds from allocation to end-use.'},
            {'text': 'What is internal audit?', 'options': ['External review by CAG', 'Independent assessment within an organization', 'Tax audit', 'Annual inspection'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Internal audit evaluates internal controls and compliance within the organization.'},
            {'text': 'What is the purpose of accrual accounting?', 'options': ['Record cash only when received', 'Record transactions when they occur, not when cash moves', 'Simplify bookkeeping', 'Avoid taxation'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'Accrual accounting provides a more accurate picture of financial position.'},
        ],
        7: [  # Leadership
            {'text': 'What is transformational leadership?', 'options': ['Managing by rules', 'Inspiring change through vision and motivation', 'Transactional management', 'Autocratic control'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Transformational leaders inspire followers to exceed self-interest for organizational goals.'},
            {'text': 'What is emotional intelligence in leadership?', 'options': ['IQ-based decision making', 'Ability to recognize and manage emotions in self and others', 'Technical expertise', 'Financial acumen'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'EI (Goleman) includes self-awareness, empathy, and social skills.'},
            {'text': 'What does delegation in management mean?', 'options': ['Doing all tasks yourself', 'Assigning responsibility and authority to subordinates', 'Avoiding accountability', 'Reducing team size'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Delegation empowers team members and improves efficiency.'},
            {'text': 'What is the purpose of performance appraisal?', 'options': ['Salary deduction', 'Evaluate employee performance and identify development needs', 'Punish poor performers', 'Reduce headcount'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Appraisals align individual performance with organizational goals.'},
            {'text': 'What is change management?', 'options': ['Resisting organizational change', 'Structured approach to transitioning individuals and organizations', 'Changing job roles', 'IT system migration only'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'Change management ensures smooth transitions with minimal disruption.'},
        ],
    }

    for comp_idx, qs in questions_data.items():
        comp_id = comp_objs[comp_idx].id
        for q in qs:
            question = Question(
                competency_id=comp_id,
                text=q['text'],
                options=json.dumps(q['options']),
                correct_answer=q['correct'],
                explanation=q['explanation'],
                difficulty=q['difficulty'],
                source='system'
            )
            db.session.add(question)

    # Seed courses
    courses_data = [
        # Data Analysis
        {'title': 'Introduction to Data Analysis', 'description': 'Learn fundamentals of data collection, cleaning, and basic analysis techniques.', 'comp': 0, 'difficulty': 'beginner', 'duration': 3.0, 'type': 'video', 'tags': ['data', 'analysis', 'basics']},
        {'title': 'Intermediate Data Analysis with Python', 'description': 'Pandas, NumPy for real-world data analysis. Covers EDA and statistical summaries.', 'comp': 0, 'difficulty': 'intermediate', 'duration': 5.0, 'type': 'interactive', 'tags': ['python', 'pandas', 'EDA']},
        {'title': 'Advanced Data Analysis & Storytelling', 'description': 'Advanced techniques including multivariate analysis and data-driven narrative.', 'comp': 0, 'difficulty': 'advanced', 'duration': 4.0, 'type': 'document', 'tags': ['advanced', 'storytelling', 'insights']},
        # Statistical Methods
        {'title': 'Statistics Fundamentals', 'description': 'Descriptive statistics, probability, and distributions from scratch.', 'comp': 1, 'difficulty': 'beginner', 'duration': 4.0, 'type': 'video', 'tags': ['statistics', 'probability', 'beginner']},
        {'title': 'Inferential Statistics & Hypothesis Testing', 'description': 'T-tests, ANOVA, chi-square, confidence intervals, and p-values.', 'comp': 1, 'difficulty': 'intermediate', 'duration': 6.0, 'type': 'interactive', 'tags': ['hypothesis', 'inference', 'testing']},
        {'title': 'Regression Analysis Mastery', 'description': 'Linear, multiple, and logistic regression with practical applications.', 'comp': 1, 'difficulty': 'advanced', 'duration': 5.0, 'type': 'interactive', 'tags': ['regression', 'modeling', 'advanced']},
        # Data Visualization
        {'title': 'Data Visualization Basics', 'description': 'Charts, graphs, and visual encoding principles using Matplotlib and Seaborn.', 'comp': 2, 'difficulty': 'beginner', 'duration': 3.0, 'type': 'video', 'tags': ['visualization', 'charts', 'matplotlib']},
        {'title': 'Dashboard Design with Power BI', 'description': 'Build interactive government dashboards using Power BI.', 'comp': 2, 'difficulty': 'intermediate', 'duration': 5.0, 'type': 'interactive', 'tags': ['powerbi', 'dashboard', 'government']},
        # Machine Learning
        {'title': 'ML Foundations for Government Officials', 'description': 'Non-technical introduction to AI/ML concepts relevant to governance.', 'comp': 3, 'difficulty': 'beginner', 'duration': 2.0, 'type': 'document', 'tags': ['ML', 'AI', 'government', 'beginner']},
        {'title': 'Applied Machine Learning', 'description': 'Hands-on ML with scikit-learn: classification, regression, clustering.', 'comp': 3, 'difficulty': 'intermediate', 'duration': 8.0, 'type': 'interactive', 'tags': ['sklearn', 'applied', 'ML']},
        # Policy Analysis
        {'title': 'Policy Analysis Framework', 'description': 'Systematic approaches to analyzing and evaluating public policies.', 'comp': 4, 'difficulty': 'beginner', 'duration': 4.0, 'type': 'document', 'tags': ['policy', 'analysis', 'framework']},
        {'title': 'Evidence-Based Policy Making', 'description': 'Using data and research to design effective government policies.', 'comp': 4, 'difficulty': 'intermediate', 'duration': 5.0, 'type': 'video', 'tags': ['evidence', 'policy', 'research']},
        # Public Administration
        {'title': 'Fundamentals of Public Administration', 'description': 'Core principles of governance, accountability, and public service.', 'comp': 5, 'difficulty': 'beginner', 'duration': 3.0, 'type': 'document', 'tags': ['governance', 'administration', 'public']},
        {'title': 'E-Governance and Digital India', 'description': 'Digital transformation in government services — iGOT, PFMS, DigiLocker.', 'comp': 5, 'difficulty': 'intermediate', 'duration': 4.0, 'type': 'video', 'tags': ['digital', 'e-gov', 'India']},
        # Financial Management
        {'title': 'Government Financial Management Basics', 'description': 'Budgeting, fiscal management, and public finance fundamentals.', 'comp': 6, 'difficulty': 'beginner', 'duration': 4.0, 'type': 'document', 'tags': ['finance', 'budget', 'government']},
        {'title': 'Internal Audit and Controls', 'description': 'Internal audit procedures, risk management, and compliance in government.', 'comp': 6, 'difficulty': 'intermediate', 'duration': 5.0, 'type': 'video', 'tags': ['audit', 'controls', 'compliance']},
        # Leadership
        {'title': 'Leadership in Public Service', 'description': 'Developing leadership skills for effective governance and team management.', 'comp': 7, 'difficulty': 'beginner', 'duration': 3.0, 'type': 'video', 'tags': ['leadership', 'public service', 'management']},
        {'title': 'Change Management for Government Officials', 'description': 'Managing organizational change in government departments effectively.', 'comp': 7, 'difficulty': 'intermediate', 'duration': 4.0, 'type': 'interactive', 'tags': ['change', 'management', 'transformation']},
    ]

    for i, c in enumerate(courses_data):
        comp_id = comp_objs[c['comp']].id
        igot_id = f"IGOT-{c['comp']+1:02d}-{i+1:03d}"
        course = Course(
            title=c['title'],
            description=c['description'],
            competency_id=comp_id,
            difficulty=c['difficulty'],
            duration_hours=c['duration'],
            course_type=c['type'],
            igot_course_id=igot_id,
            tags=json.dumps(c['tags']),
            source='igot'
        )
        db.session.add(course)

    # ── NEW Official Statistics Competencies (for NSSTA TPAC) ─────────────
    nssta_competencies = [
        {'name': 'Survey Design & Sampling',       'domain': 'Official Statistics', 'description': 'Survey methodology, sampling techniques, and questionnaire design for official data collection'},
        {'name': 'National Accounts Statistics',   'domain': 'Official Statistics', 'description': 'GDP compilation, National Income Accounting, SNA framework, and derived statistics'},
        {'name': 'Price & Index Statistics',        'domain': 'Official Statistics', 'description': 'CPI, WPI, index number theory, and price statistics methodology'},
        {'name': 'Agricultural Statistics',        'domain': 'Official Statistics', 'description': 'Crop estimation surveys, land use statistics, and agricultural data systems'},
        {'name': 'Labour & Employment Statistics', 'domain': 'Official Statistics', 'description': 'PLFS, employment-unemployment surveys, and labour market indicators'},
        {'name': 'SDG & Metadata Standards',       'domain': 'Official Statistics', 'description': 'SDG indicator monitoring, metadata frameworks, and data quality standards'},
        {'name': 'GIS & Geospatial Analysis',      'domain': 'Technical',           'description': 'Geographic Information Systems for spatial data analysis and mapping'},
        {'name': 'Python & R for Statistics',      'domain': 'Technical',           'description': 'Statistical computing using Python and R for official data analysis'},
        {'name': 'Data Privacy & Cybersecurity',   'domain': 'Digital Governance',  'description': 'Cybersecurity fundamentals, data privacy laws, digital signatures, and secure data handling'},
        {'name': 'Industrial & Economic Statistics', 'domain': 'Official Statistics', 'description': 'IIP, ASI, economic census, and industrial data collection frameworks'},
    ]

    nssta_comp_objs = []
    for c in nssta_competencies:
        obj = Competency(name=c['name'], domain=c['domain'], description=c['description'])
        db.session.add(obj)
        nssta_comp_objs.append(obj)
    db.session.flush()

    # ── NSSTA TPAC Questions ───────────────────────────────────────────────
    nssta_questions = {
        0: [  # Survey Design & Sampling
            {'text': 'Which sampling method ensures every unit in the population has an equal chance of selection?', 'options': ['Stratified sampling', 'Simple random sampling', 'Cluster sampling', 'Purposive sampling'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Simple random sampling gives each unit an equal probability of being selected.'},
            {'text': 'What is the primary advantage of stratified random sampling?', 'options': ['Reduces sample size', 'Ensures representation of all subgroups', 'Eliminates non-sampling error', 'Simplifies field operations'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Stratification ensures proportional representation of all population subgroups.'},
            {'text': 'In a survey, what does "non-sampling error" refer to?', 'options': ['Error due to small sample', 'Error from random selection', 'Errors from measurement, coverage, or processing', 'Error from large variance'], 'correct': 2, 'difficulty': 'medium', 'explanation': 'Non-sampling errors arise from measurement issues, not from the sampling process itself.'},
            {'text': 'What does PPS sampling stand for?', 'options': ['Proportional to Population Size', 'Probability Proportional to Size', 'Partial Population Sampling', 'Primary Population Survey'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'PPS (Probability Proportional to Size) gives larger units a higher chance of selection.'},
            {'text': 'Which organisation conducts the Periodic Labour Force Survey (PLFS) in India?', 'options': ['RBI', 'NSSO / NSO', 'NITI Aayog', 'Labour Ministry'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'The National Statistical Office (NSO) under MoSPI conducts PLFS.'},
        ],
        1: [  # National Accounts Statistics
            {'text': 'Which approach measures GDP by summing value added across all sectors?', 'options': ['Expenditure approach', 'Income approach', 'Production/Output approach', 'Trade approach'], 'correct': 2, 'difficulty': 'medium', 'explanation': 'The production approach sums Gross Value Added (GVA) across all economic sectors.'},
            {'text': 'What does GVA stand for in national accounts?', 'options': ['Gross Value Assessment', 'Gross Value Added', 'General Value Aggregate', 'Government Value Analysis'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'GVA = GDP - Product taxes + Subsidies. It measures output net of intermediate consumption.'},
            {'text': 'The current SNA framework used globally is?', 'options': ['SNA 1993', 'SNA 2008', 'SNA 2015', 'SNA 1968'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'SNA 2008 (System of National Accounts 2008) is the current international standard.'},
            {'text': 'What is the base year for India\'s current GDP series?', 'options': ['2004-05', '2010-11', '2011-12', '2015-16'], 'correct': 2, 'difficulty': 'easy', 'explanation': 'India revised its GDP base year to 2011-12 in January 2015.'},
            {'text': 'Which component is NOT included in GDP by expenditure method?', 'options': ['Government consumption', 'Gross fixed capital formation', 'Intermediate consumption', 'Net exports'], 'correct': 2, 'difficulty': 'hard', 'explanation': 'Intermediate consumption is excluded from GDP to avoid double counting.'},
        ],
        2: [  # Price & Index Statistics
            {'text': 'CPI in India is compiled and released by which organisation?', 'options': ['RBI', 'MoSPI / NSO', 'Finance Ministry', 'DPIIT'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'The National Statistical Office (NSO) under MoSPI releases the CPI.'},
            {'text': 'Which index measures price changes at the wholesale level in India?', 'options': ['CPI', 'WPI', 'PPI', 'HPCI'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'WPI (Wholesale Price Index) measures price changes at the first point of bulk sale.'},
            {'text': 'What is the Laspeyres price index formula based on?', 'options': ['Current period quantities as weights', 'Base period quantities as weights', 'Average of base and current weights', 'Geometric mean of prices'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'Laspeyres index uses base period quantities as fixed weights.'},
            {'text': 'The current base year for WPI in India is?', 'options': ['2004-05', '2010-11', '2011-12', '2017-18'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'India revised the WPI base year to 2011-12 effective from May 2017.'},
            {'text': 'Core inflation excludes which components?', 'options': ['Manufacturing goods', 'Food and fuel', 'Services', 'Housing'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Core inflation strips out volatile food and fuel prices to show underlying inflation trends.'},
        ],
        3: [  # Agricultural Statistics
            {'text': 'Which survey estimates crop production in India?', 'options': ['NSS', 'Crop Cutting Experiments', 'PLFS', 'NSSO Round'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Crop Cutting Experiments (CCE) are used to scientifically estimate crop yield.'},
            {'text': 'Which ministry is responsible for Agricultural Statistics in India?', 'options': ['MoSPI', 'Ministry of Agriculture & Farmers Welfare', 'NITI Aayog', 'Rural Development Ministry'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'The Directorate of Economics & Statistics under MoAFW handles agricultural statistics.'},
            {'text': 'What does "Minimum Support Price" data primarily reflect?', 'options': ['Market price', 'Government procurement price floor for crops', 'Export price', 'Consumer price'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'MSP is the government-guaranteed price floor to protect farmers from price falls.'},
            {'text': 'Land use statistics in India are maintained under which classification system?', 'options': ['FAO system', '9-fold land use classification', 'NLRMP system', 'UN land framework'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'India uses the 9-fold land use classification: net sown area, fallow, forest, etc.'},
            {'text': 'FASAL stands for?', 'options': ['Forecasting Agriculture Output using Space-based Analytics and Land', 'Farming and Satellite Land', 'Food Analysis for Statistical Agriculture', 'None of the above'], 'correct': 0, 'difficulty': 'medium', 'explanation': 'FASAL uses remote sensing and satellite data for advance crop production forecasting.'},
        ],
        4: [  # Labour & Employment Statistics
            {'text': 'PLFS stands for?', 'options': ['Periodic Labour Force Survey', 'Primary Labour & Financial Survey', 'Public Labour Force Statistics', 'Planned Labour Force Study'], 'correct': 0, 'difficulty': 'easy', 'explanation': 'PLFS (Periodic Labour Force Survey) provides quarterly and annual employment data.'},
            {'text': 'What is the Usual Principal Status (UPS) in employment surveys?', 'options': ['Status for the last 7 days', 'Activity status for the major part of the reference year', 'Employment status in formal sector', 'Status for last 30 days'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'UPS captures the activity in which a person spent the majority of the last 365 days.'},
            {'text': 'Labour Force Participation Rate (LFPR) is defined as?', 'options': ['Employed / Total population', '(Employed + Unemployed) / Working age population', 'Employed / Working age population', 'Unemployed / Total population'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'LFPR = (Employed + Unemployed seeking work) / Working age population × 100.'},
            {'text': 'Which survey replaced the earlier Employment-Unemployment Survey (EUS)?', 'options': ['NSSO', 'PLFS', 'ASI', 'CESS'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'PLFS replaced the quinquennial EUS from 2017-18 with more frequent data.'},
            {'text': 'Worker Population Ratio (WPR) measures?', 'options': ['Ratio of workers to unemployed', 'Proportion of employed persons in total population', 'Formal sector employment rate', 'Urban employment rate'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'WPR = Employed persons / Total persons × 100.'},
        ],
        5: [  # SDG & Metadata Standards
            {'text': 'How many Sustainable Development Goals (SDGs) are there?', 'options': ['15', '17', '19', '21'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'The UN 2030 Agenda has 17 SDGs with 169 targets and 232 unique indicators.'},
            {'text': 'Which Indian ministry is the nodal agency for SDG monitoring?', 'options': ['MoSPI', 'NITI Aayog', 'Finance Ministry', 'MEA'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'NITI Aayog coordinates SDG monitoring; MoSPI compiles SDG India Index.'},
            {'text': 'SDMX stands for?', 'options': ['Statistical Data and Metadata eXchange', 'Standard Data Management eXchange', 'Structured Data Metadata Exchange', 'Statistical Digital Management XML'], 'correct': 0, 'difficulty': 'hard', 'explanation': 'SDMX is the international standard for exchanging statistical data and metadata.'},
            {'text': 'Data Quality Framework (DQF) for Official Statistics includes which dimension?', 'options': ['Relevance, Accuracy, Timeliness, Accessibility', 'Speed, Cost, Volume, Accuracy', 'Reliability, Usability, Speed, Format', 'Completeness, Syntax, Format, Speed'], 'correct': 0, 'difficulty': 'medium', 'explanation': 'IMF/UN DQF dimensions: Relevance, Accuracy, Timeliness, Accessibility, Coherence, Interpretability.'},
            {'text': 'The UN Fundamental Principles of Official Statistics were adopted in which year?', 'options': ['1991', '1994', '2003', '2014'], 'correct': 1, 'difficulty': 'hard', 'explanation': 'The UN Fundamental Principles of Official Statistics were adopted in 1994 by the UN Statistical Commission.'},
        ],
        6: [  # GIS & Geospatial Analysis
            {'text': 'What does GIS stand for?', 'options': ['Geographic Information System', 'General Integrated Statistics', 'Geospatial Index Standard', 'Government Information System'], 'correct': 0, 'difficulty': 'easy', 'explanation': 'GIS is a system for capturing, storing, analyzing, and visualizing geographic data.'},
            {'text': 'Which file format is commonly used for vector geospatial data?', 'options': ['CSV', 'Shapefile (.shp)', 'JPEG', 'PDF'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Shapefiles (.shp) are the standard format for vector GIS data.'},
            {'text': 'What is remote sensing used for in agricultural statistics?', 'options': ['Recording farmer interviews', 'Estimating crop area and yield using satellite imagery', 'Processing price data', 'Compiling trade statistics'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Remote sensing uses satellite imagery to estimate crop area, health, and yield (e.g., FASAL project).'},
            {'text': 'QGIS is?', 'options': ['A paid GIS software by ESRI', 'A free open-source GIS application', 'A government portal for maps', 'A satellite data format'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'QGIS is a free, open-source Geographic Information System application.'},
            {'text': 'What is a choropleth map used for?', 'options': ['Showing 3D terrain', 'Displaying statistical data using color intensity across regions', 'Tracking satellite positions', 'Plotting survey routes'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Choropleth maps use color shading to show statistical variation across geographic areas.'},
        ],
        7: [  # Python & R for Statistics
            {'text': 'Which Python library is specifically designed for statistical modeling?', 'options': ['NumPy', 'statsmodels', 'Matplotlib', 'Flask'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'statsmodels provides classes and functions for statistical models and tests.'},
            {'text': 'In R, which function is used to read a CSV file?', 'options': ['load.csv()', 'read.csv()', 'import.csv()', 'open.csv()'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'read.csv() is the standard R function to import CSV data into a data frame.'},
            {'text': 'What does the pandas function describe() do?', 'options': ['Describe the column names', 'Generate summary statistics for numeric columns', 'Print the data types', 'Show missing values'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'describe() returns count, mean, std, min, quartiles, and max for numeric columns.'},
            {'text': 'Which package in R is used for data manipulation similar to pandas?', 'options': ['ggplot2', 'dplyr', 'caret', 'shiny'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'dplyr provides a grammar for data manipulation: filter, select, mutate, summarise, arrange.'},
            {'text': 'In Python, which library is used for machine learning?', 'options': ['NumPy', 'scikit-learn', 'Seaborn', 'SQLAlchemy'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'scikit-learn is the standard Python library for ML algorithms and pipelines.'},
        ],
        8: [  # Data Privacy & Cybersecurity
            {'text': 'What does the Digital Personal Data Protection Act 2023 primarily protect?', 'options': ['Government digital assets', 'Personal data of Indian citizens', 'Corporate financial data', 'Intellectual property'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'India\'s DPDP Act 2023 establishes rights of data principals and obligations of data fiduciaries.'},
            {'text': 'What is a digital signature used for?', 'options': ['Encrypting all data', 'Verifying authenticity and integrity of digital documents', 'Compressing files', 'Storing passwords'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Digital signatures authenticate the sender and ensure the document has not been tampered with.'},
            {'text': 'What does two-factor authentication (2FA) add?', 'options': ['A second password', 'An additional verification layer beyond just a password', 'Encryption to data', 'Firewall protection'], 'correct': 1, 'difficulty': 'easy', 'explanation': '2FA requires something you know (password) plus something you have (OTP/token).'},
            {'text': 'MeghRaj is?', 'options': ['A cybersecurity law', 'Government of India\'s cloud computing initiative', 'A statistical software', 'A digital signature standard'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'GI Cloud (MeghRaj) is the Government of India\'s cloud infrastructure for hosting government applications.'},
            {'text': 'What is phishing?', 'options': ['A network protocol', 'A fraudulent attempt to obtain sensitive information by impersonation', 'A type of encryption', 'A government database'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'Phishing uses deceptive emails or websites to trick users into revealing credentials.'},
        ],
        9: [  # Industrial & Economic Statistics
            {'text': 'IIP stands for?', 'options': ['Index of Industrial Production', 'Indian Industrial Policy', 'Integrated Industrial Programme', 'Index of Import Prices'], 'correct': 0, 'difficulty': 'easy', 'explanation': 'IIP measures the growth rate of industry groups in a fixed period compared to a base period.'},
            {'text': 'Annual Survey of Industries (ASI) in India covers?', 'options': ['All industrial units', 'Factories registered under Factories Act with 10+ workers', 'Only public sector units', 'Small and medium enterprises only'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'ASI covers factories registered under the Factories Act, primarily with 10 or more workers.'},
            {'text': 'The base year for current IIP series in India is?', 'options': ['2004-05', '2010-11', '2011-12', '2017-18'], 'correct': 2, 'difficulty': 'medium', 'explanation': 'India\'s IIP base year was revised to 2011-12 in 2017.'},
            {'text': 'Economic Census in India is conducted by?', 'options': ['RBI', 'MoSPI', 'Ministry of Commerce', 'DPIIT'], 'correct': 1, 'difficulty': 'easy', 'explanation': 'MoSPI conducts the Economic Census to count all establishments in India.'},
            {'text': 'Which sector has the highest weight in India\'s IIP?', 'options': ['Mining', 'Manufacturing', 'Electricity', 'Construction'], 'correct': 1, 'difficulty': 'medium', 'explanation': 'Manufacturing has the highest weight (~77.6%) in India\'s IIP basket.'},
        ],
    }

    for comp_idx, qs in nssta_questions.items():
        comp_id = nssta_comp_objs[comp_idx].id
        for q in qs:
            question = Question(
                competency_id=comp_id,
                text=q['text'],
                options=json.dumps(q['options']),
                correct_answer=q['correct'],
                explanation=q['explanation'],
                difficulty=q['difficulty'],
                source='system'
            )
            db.session.add(question)

    # ── NSSTA TPAC Programmes (loaded from real MoSPI/NSSTA dataset CSV) ──
    import csv, os as _os
    _csv_path = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'data', 'nssta_programmes.csv'))

    # Map competency domain name → comp object id
    _domain_map = {c.name: c.id for c in nssta_comp_objs}
    # Fallback: also map by partial keyword
    _domain_keywords = {
        'survey': nssta_comp_objs[0].id,
        'sampling': nssta_comp_objs[0].id,
        'national accounts': nssta_comp_objs[1].id,
        'macroeconomic': nssta_comp_objs[1].id,
        'econometric': nssta_comp_objs[1].id,
        'price': nssta_comp_objs[2].id,
        'index': nssta_comp_objs[2].id,
        'agricultural': nssta_comp_objs[3].id,
        'crop': nssta_comp_objs[3].id,
        'labour': nssta_comp_objs[4].id,
        'plfs': nssta_comp_objs[4].id,
        'employment': nssta_comp_objs[4].id,
        'sdg': nssta_comp_objs[5].id,
        'metadata': nssta_comp_objs[5].id,
        'gis': nssta_comp_objs[6].id,
        'geospatial': nssta_comp_objs[6].id,
        'visualization': nssta_comp_objs[6].id,
        'dashboard': nssta_comp_objs[6].id,
        'python': nssta_comp_objs[7].id,
        'data analytics': nssta_comp_objs[7].id,
        'machine learning': nssta_comp_objs[7].id,
        'cybersecurity': nssta_comp_objs[8].id,
        'data privacy': nssta_comp_objs[8].id,
        'igot': nssta_comp_objs[8].id,
        'karmayogi': nssta_comp_objs[8].id,
        'industrial': nssta_comp_objs[9].id,
        'asuse': nssta_comp_objs[9].id,
        'leadership': comp_objs[7].id,
        'management': comp_objs[7].id,
        'mid career': comp_objs[7].id,
        'mctp': comp_objs[7].id,
        'official statistics': nssta_comp_objs[0].id,
        'state': nssta_comp_objs[0].id,
        'international': nssta_comp_objs[0].id,
        'awareness': nssta_comp_objs[0].id,
    }

    def _resolve_comp_id(domain_str, title_str):
        """Resolve competency id from domain column or title keywords."""
        # Exact name match first
        if domain_str in _domain_map:
            return _domain_map[domain_str]
        # Keyword match on domain + title combined
        combined = (domain_str + ' ' + title_str).lower()
        for kw, cid in _domain_keywords.items():
            if kw in combined:
                return cid
        return nssta_comp_objs[0].id  # fallback

    nssta_courses = []
    if _os.path.exists(_csv_path):
        with open(_csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dur = float(row['duration_days'])
                except ValueError:
                    dur = 3.0
                nssta_courses.append({
                    'title':       row['title'],
                    'description': row['description'],
                    'comp_id':     _resolve_comp_id(row['competency_domain'], row['title']),
                    'difficulty':  row['difficulty'],
                    'duration':    dur,
                    'type':        'workshop' if row['mode'] == 'Residential' else
                                   'online'   if row['mode'] == 'Online' else 'hybrid',
                    'tags':        [t.strip() for t in
                                    (row['category'] + ',' + row['competency_domain'] +
                                     ',NSSTA,MoSPI').split(',') if t.strip()],
                    'nssta_id':    row['programme_id'],
                    'venue':       row['venue'],
                    'audience':    row['target_audience'],
                    'source_url':  row.get('source_url', ''),
                })
        print(f"  Loaded {len(nssta_courses)} NSSTA programmes from CSV")
    else:
        print("  WARNING: nssta_programmes.csv not found — skipping NSSTA seed")

    # Fallback hardcoded list kept empty — CSV is single source of truth
    _extra_nssta_courses = [
        # ── Statistical Competencies ──────────────────────────────────────
        {
            'title': 'Survey Methodology & Data Analysis',
            'description': 'Covers survey design, sampling methods, questionnaire design, field operations, and data processing for official surveys. Hands-on exercises with real NSO datasets.',
            'comp': 0, 'difficulty': 'intermediate', 'duration': 5.0,
            'type': 'workshop', 'tags': ['survey', 'sampling', 'NSO', 'NSSTA'],
            'nssta_id': 'NSSTA-STAT-001',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'ISS Probationers / ISS In-service Officers'
        },
        {
            'title': 'Advanced Sampling Techniques',
            'description': 'PPS sampling, multi-stage sampling, systematic sampling, variance estimation, and sample size determination for large-scale surveys.',
            'comp': 0, 'difficulty': 'advanced', 'duration': 5.0,
            'type': 'workshop', 'tags': ['PPS', 'multi-stage', 'variance', 'NSSTA'],
            'nssta_id': 'NSSTA-STAT-002',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'ISS Officers (In-service)'
        },
        {
            'title': 'National Accounts Statistics — Foundation',
            'description': 'GDP compilation using production, expenditure, and income approaches. SNA 2008 framework, GVA computation, and India\'s national accounts methodology.',
            'comp': 1, 'difficulty': 'intermediate', 'duration': 5.0,
            'type': 'workshop', 'tags': ['GDP', 'GVA', 'SNA', 'national accounts', 'NSSTA'],
            'nssta_id': 'NSSTA-STAT-003',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'ISS / SSS Officers'
        },
        {
            'title': 'Derived Statistics & Official Statistics Methodology',
            'description': 'Compilation of derived statistics, index numbers, rebasing, chaining, and quality assessment of official statistical outputs.',
            'comp': 1, 'difficulty': 'advanced', 'duration': 4.0,
            'type': 'workshop', 'tags': ['derived statistics', 'index', 'rebasing', 'NSSTA'],
            'nssta_id': 'NSSTA-STAT-004',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'ISS Officers (Senior)'
        },
        {
            'title': 'Price Statistics & Index Numbers',
            'description': 'CPI and WPI methodology, Laspeyres and Paasche indices, hedonic pricing, and international price comparison (PPP). Practical compilation exercises.',
            'comp': 2, 'difficulty': 'intermediate', 'duration': 4.0,
            'type': 'workshop', 'tags': ['CPI', 'WPI', 'index numbers', 'price statistics', 'NSSTA'],
            'nssta_id': 'NSSTA-STAT-005',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'ISS / SSS Officers'
        },
        {
            'title': 'Agricultural Statistics & Crop Estimation',
            'description': 'Crop cutting experiments, area enumeration, FASAL remote sensing programme, land use classification, and agricultural data systems in India.',
            'comp': 3, 'difficulty': 'intermediate', 'duration': 5.0,
            'type': 'workshop', 'tags': ['agriculture', 'crop estimation', 'FASAL', 'NSSTA'],
            'nssta_id': 'NSSTA-STAT-006',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'State Statistical Officers / ISS Officers'
        },
        {
            'title': 'Labour & Employment Statistics — PLFS Methodology',
            'description': 'PLFS design, UPS/CWS/CDS concepts, LFPR/WPR/UR computation, employment-unemployment analysis, and international labour standards (ILO framework).',
            'comp': 4, 'difficulty': 'intermediate', 'duration': 4.0,
            'type': 'workshop', 'tags': ['PLFS', 'labour', 'employment', 'LFPR', 'NSSTA'],
            'nssta_id': 'NSSTA-STAT-007',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'ISS / SSS Officers'
        },
        {
            'title': 'SDG Indicators & Data Quality Frameworks',
            'description': 'SDG monitoring framework, India\'s SDG India Index, SDMX metadata standards, IMF Data Quality Assessment Framework (DQAF), and reporting to UN agencies.',
            'comp': 5, 'difficulty': 'intermediate', 'duration': 3.0,
            'type': 'workshop', 'tags': ['SDG', 'SDMX', 'metadata', 'data quality', 'NSSTA'],
            'nssta_id': 'NSSTA-STAT-008',
            'venue': 'NSSTA, Greater Noida / Online',
            'audience': 'All Statistical Officers'
        },
        {
            'title': 'Industrial Statistics — IIP & ASI Methodology',
            'description': 'Index of Industrial Production (IIP) compilation, Annual Survey of Industries (ASI) methodology, Economic Census framework, and industrial classification (NIC 2008).',
            'comp': 9, 'difficulty': 'intermediate', 'duration': 4.0,
            'type': 'workshop', 'tags': ['IIP', 'ASI', 'economic census', 'NIC', 'NSSTA'],
            'nssta_id': 'NSSTA-STAT-009',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'ISS / SSS Officers'
        },

        # ── Technical Competencies ────────────────────────────────────────
        {
            'title': 'Machine Learning using Python (with IIT Madras)',
            'description': '12-week online programme in collaboration with IIT Madras. Covers Python programming, data analysis with pandas/NumPy, ML algorithms (regression, classification, clustering), and application to official statistics datasets.',
            'comp': 7, 'difficulty': 'advanced', 'duration': 60.0,
            'type': 'online', 'tags': ['python', 'ML', 'IIT Madras', 'scikit-learn', 'NSSTA'],
            'nssta_id': 'NSSTA-TECH-001',
            'venue': 'Online (IIT Madras + NSSTA)',
            'audience': 'ISS / SSS Officers'
        },
        {
            'title': 'Data Analysis using R for Official Statistics',
            'description': 'Statistical computing with R: data wrangling with dplyr/tidyr, visualization with ggplot2, hypothesis testing, regression analysis, and survey data analysis using the survey package.',
            'comp': 7, 'difficulty': 'intermediate', 'duration': 5.0,
            'type': 'workshop', 'tags': ['R', 'ggplot2', 'dplyr', 'statistical computing', 'NSSTA'],
            'nssta_id': 'NSSTA-TECH-002',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'ISS / SSS Officers'
        },
        {
            'title': 'GIS & Remote Sensing for Statistical Applications',
            'description': 'Introduction to GIS concepts, QGIS hands-on, spatial data analysis, choropleth mapping, remote sensing for agricultural statistics, and geospatial data integration.',
            'comp': 6, 'difficulty': 'intermediate', 'duration': 5.0,
            'type': 'workshop', 'tags': ['GIS', 'QGIS', 'remote sensing', 'spatial', 'NSSTA'],
            'nssta_id': 'NSSTA-TECH-003',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'Statistical Officers / State Personnel'
        },
        {
            'title': 'Data Visualization & Dashboard Development',
            'description': 'Principles of statistical visualization, chart selection, Power BI and Tableau for government dashboards, and building interactive reports for policy dissemination.',
            'comp': 6, 'difficulty': 'beginner', 'duration': 4.0,
            'type': 'workshop', 'tags': ['visualization', 'Power BI', 'dashboard', 'NSSTA'],
            'nssta_id': 'NSSTA-TECH-004',
            'venue': 'NSSTA, Greater Noida / Online',
            'audience': 'All Statistical Officers'
        },
        {
            'title': 'Big Data Analytics for Official Statistics',
            'description': 'Big data concepts, administrative data sources, web scraping for price statistics, alternative data (satellite, mobile, social media), and ethical use of big data in official statistics.',
            'comp': 7, 'difficulty': 'advanced', 'duration': 3.0,
            'type': 'workshop', 'tags': ['big data', 'alternative data', 'web scraping', 'NSSTA'],
            'nssta_id': 'NSSTA-TECH-005',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'ISS Officers (Senior)'
        },

        # ── Digital Governance ────────────────────────────────────────────
        {
            'title': 'Cybersecurity & Data Privacy for Government Officials',
            'description': 'Cybersecurity fundamentals, DPDP Act 2023, digital signatures, secure data handling, MeghRaj (Government Cloud), password hygiene, phishing awareness, and incident response.',
            'comp': 8, 'difficulty': 'beginner', 'duration': 3.0,
            'type': 'workshop', 'tags': ['cybersecurity', 'DPDP', 'data privacy', 'MeghRaj', 'NSSTA'],
            'nssta_id': 'NSSTA-DIG-001',
            'venue': 'NSSTA, Greater Noida / Online',
            'audience': 'All Government Officers'
        },

        # ── Induction / Probationary Programmes ──────────────────────────
        {
            'title': 'ISS Two-Year Probationary Training Programme',
            'description': 'Comprehensive 2-year structured training for newly recruited Indian Statistical Service (ISS) officers covering all domains: official statistics, econometrics, computing, field training, and governance.',
            'comp': 0, 'difficulty': 'beginner', 'duration': 320.0,
            'type': 'induction', 'tags': ['ISS', 'probationary', 'induction', 'NSSTA'],
            'nssta_id': 'NSSTA-IND-001',
            'venue': 'NSSTA, Greater Noida + Field Attachments',
            'audience': 'ISS Probationers (New Recruits)'
        },
        {
            'title': 'SSS New Recruits Induction Training',
            'description': '3-month induction training for Subordinate Statistical Service (SSS) new recruits covering official statistics fundamentals, data collection procedures, and government systems.',
            'comp': 0, 'difficulty': 'beginner', 'duration': 60.0,
            'type': 'induction', 'tags': ['SSS', 'induction', 'new recruits', 'NSSTA'],
            'nssta_id': 'NSSTA-IND-002',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'SSS New Recruits'
        },
        {
            'title': 'Induction Training for Promotee JTS Officers (SSS to ISS)',
            'description': '2-week bridging programme for SSS officers promoted to ISS Junior Time Scale (JTS), covering advanced statistical methods, policy interface, and leadership responsibilities.',
            'comp': 0, 'difficulty': 'intermediate', 'duration': 10.0,
            'type': 'induction', 'tags': ['ISS', 'SSS', 'promotee', 'JTS', 'NSSTA'],
            'nssta_id': 'NSSTA-IND-003',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'SSS Officers Promoted to ISS JTS'
        },

        # ── State & International ─────────────────────────────────────────
        {
            'title': 'Training Programme for State Statistical Personnel',
            'description': 'Capacity building for state government statistical officers covering official statistics methodology, survey operations, data quality, and use of MoSPI tools and frameworks.',
            'comp': 5, 'difficulty': 'beginner', 'duration': 5.0,
            'type': 'workshop', 'tags': ['state', 'statistical personnel', 'capacity building', 'NSSTA'],
            'nssta_id': 'NSSTA-STATE-001',
            'venue': 'NSSTA, Greater Noida / State ATIs',
            'audience': 'State Government Statistical Officers'
        },
        {
            'title': 'International Training Programme on Official Statistics',
            'description': '2-week programme for foreign statistical officers from developing countries covering India\'s statistical system, NSO operations, survey methodology, and data dissemination.',
            'comp': 5, 'difficulty': 'advanced', 'duration': 10.0,
            'type': 'workshop', 'tags': ['international', 'official statistics', 'India', 'NSSTA'],
            'nssta_id': 'NSSTA-INTL-001',
            'venue': 'NSSTA, Greater Noida',
            'audience': 'Foreign Statistical Officers'
        },
    ]  # end _extra_nssta_courses (empty — CSV is single source of truth)

    for c in nssta_courses:
        course = Course(
            title=c['title'],
            description=c['description'],
            competency_id=c['comp_id'],
            difficulty=c['difficulty'],
            duration_hours=c['duration'],
            course_type=c['type'],
            igot_course_id=c['nssta_id'],
            tags=json.dumps(c['tags']),
            source='nssta',
            venue=c['venue'],
            target_audience=c['audience'],
            content_url=c.get('source_url', '')
        )
        db.session.add(course)

    db.session.commit()
    print("✅ Database seeded with competencies, questions, iGOT courses, and NSSTA TPAC programmes.")


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)

"""
Quiz Generator Routes — Upload document, generate MCQs
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from models.database import db, GeneratedQuiz
from ai_modules.document_parser import parse_document, chunk_text
from ai_modules.mcq_generator import generate_mcqs_from_text, validate_and_enhance_quiz
from utils.security import validate_upload_file, sanitize_dict, rate_limit
from utils.audit import log_file, log_data, log_security
import os
import json

quiz_bp = Blueprint('quiz', __name__)

# Per-route file size cap (Flask global MAX_CONTENT_LENGTH is also enforced)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@quiz_bp.route('/upload', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=20, window_seconds=3600)  # 20 uploads/hour per IP
def upload_and_generate():
    user_id = int(get_jwt_identity())

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    # ── File validation (extension + magic bytes + size) ──
    try:
        file_info = validate_upload_file(file)
    except ValueError as e:
        log_file('upload_rejected', user_id=user_id,
                 details={'filename': file.filename, 'reason': str(e)}, success=False)
        log_security('invalid_file_upload', user_id=user_id,
                     details={'filename': file.filename, 'reason': str(e)})
        return jsonify({'error': str(e)}), 400

    # ── Form field validation ──
    try:
        form_data = sanitize_dict(request.form, {
            'num_questions': {'type': int, 'required': False, 'min_value': 5,
                              'max_value': 25, 'default': 10},
            'title':         {'type': str, 'required': False, 'max_length': 200, 'default': ''},
        })
    except ValueError as e:
        log_security('invalid_input', user_id=user_id,
                     details={'action': 'quiz_upload', 'error': str(e)})
        return jsonify({'error': str(e)}), 400

    num_questions = form_data['num_questions'] or 10
    title = form_data['title'] or secure_filename(file.filename)

    # ── Save file with user-scoped name ──
    filename = secure_filename(file.filename)
    upload_path = current_app.config['UPLOAD_FOLDER']
    filepath = os.path.join(upload_path, f"{user_id}_{filename}")
    file.save(filepath)

    log_file('upload', user_id=user_id, details={
        'filename': filename, 'size_bytes': file_info['size'], 'ext': file_info['ext']
    })

    # ── Parse document ──
    try:
        parse_result = parse_document(filepath)
        if not parse_result['success']:
            os.remove(filepath)
            return jsonify({'error': f"Could not parse document: {parse_result['error']}"}), 422

        text = parse_result['text']
        metadata = parse_result['metadata']

        if len(text.split()) < 100:
            os.remove(filepath)
            return jsonify({'error': 'Document has too little text content (min 100 words)'}), 422

        # ── Generate MCQs ──
        mcqs = generate_mcqs_from_text(text, num_questions=num_questions, title=title)
        quiz_data = validate_and_enhance_quiz(mcqs)

        if quiz_data['total'] == 0:
            os.remove(filepath)
            return jsonify({
                'error': 'Could not generate questions from this document. '
                         'Try a more detailed text file.'
            }), 422

        # ── Persist quiz ──
        quiz = GeneratedQuiz(
            user_id=user_id,
            title=title,
            source_filename=filename,
            questions=json.dumps(quiz_data['questions'])
        )
        db.session.add(quiz)
        db.session.commit()

        log_data('quiz_generated', user_id=user_id, details={
            'quiz_id': quiz.id, 'questions': quiz_data['total']
        })

        return jsonify({
            'quiz_id': quiz.id,
            'title': title,
            'questions': quiz_data['questions'],
            'total': quiz_data['total'],
            'difficulty_distribution': quiz_data['difficulty_distribution'],
            'quality_score': quiz_data['quality_score'],
            'document_metadata': metadata,
            'message': f'Successfully generated {quiz_data["total"]} questions'
        }), 201

    finally:
        # Always clean up the uploaded file
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass


@quiz_bp.route('/my-quizzes', methods=['GET'])
@jwt_required()
def get_my_quizzes():
    user_id = int(get_jwt_identity())
    quizzes = (GeneratedQuiz.query
               .filter_by(user_id=user_id)
               .order_by(GeneratedQuiz.created_at.desc())
               .all())
    result = []
    for q in quizzes:
        qd = q.to_dict()
        qd['question_count'] = len(qd['questions'])
        qd.pop('questions')
        result.append(qd)
    return jsonify({'quizzes': result}), 200


@quiz_bp.route('/<int:quiz_id>', methods=['GET'])
@jwt_required()
def get_quiz(quiz_id):
    user_id = int(get_jwt_identity())
    quiz = GeneratedQuiz.query.filter_by(id=quiz_id, user_id=user_id).first_or_404()
    return jsonify(quiz.to_dict()), 200


@quiz_bp.route('/<int:quiz_id>/submit', methods=['POST'])
@jwt_required()
def submit_generated_quiz(quiz_id):
    user_id = int(get_jwt_identity())
    quiz = GeneratedQuiz.query.filter_by(id=quiz_id, user_id=user_id).first_or_404()

    raw = request.get_json(silent=True) or {}
    answers = raw.get('answers', [])

    if not isinstance(answers, list):
        return jsonify({'error': 'answers must be a list'}), 400

    questions = json.loads(quiz.questions)
    q_map = {q['id']: q for q in questions}

    correct = 0
    results = []
    for ans in answers:
        if not isinstance(ans, dict):
            continue
        qid = ans.get('question_id')
        selected = ans.get('selected_option')
        if not isinstance(selected, int) or selected not in range(4):
            continue
        q = q_map.get(qid)
        if not q:
            continue
        is_correct = (selected == q['correct_answer'])
        if is_correct:
            correct += 1
        results.append({
            'question_id': qid,
            'question': q['text'],
            'selected_option': selected,
            'correct_answer': q['correct_answer'],
            'options': q['options'],
            'is_correct': is_correct,
            'explanation': q.get('explanation', ''),
            'difficulty': q.get('difficulty')
        })

    total = len(results)
    score_pct = round(correct / total * 100, 1) if total else 0

    log_data('quiz_submit', user_id=user_id, details={
        'quiz_id': quiz_id, 'score': score_pct, 'total': total
    })

    return jsonify({
        'score': score_pct,
        'correct': correct,
        'total': total,
        'results': results,
        'passed': score_pct >= 60,
        'message': 'Great job!' if score_pct >= 70 else 'Keep practicing to improve your score!'
    }), 200


@quiz_bp.route('/<int:quiz_id>', methods=['DELETE'])
@jwt_required()
def delete_quiz(quiz_id):
    user_id = int(get_jwt_identity())
    quiz = GeneratedQuiz.query.filter_by(id=quiz_id, user_id=user_id).first_or_404()
    db.session.delete(quiz)
    db.session.commit()
    log_data('quiz_delete', user_id=user_id, details={'quiz_id': quiz_id})
    return jsonify({'message': 'Quiz deleted'}), 200

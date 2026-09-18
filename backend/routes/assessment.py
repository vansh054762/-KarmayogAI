"""
Assessment Routes — Get questions, submit answers, analyze gaps
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db, Competency, Question, AssessmentResult
from ai_modules.competency_analyzer import (
    analyze_competency_gaps, calculate_weighted_score, get_improvement_suggestions
)
from utils.security import sanitize_dict
from utils.audit import log_data, log_security
import json
import random

assessment_bp = Blueprint('assessment', __name__)


@assessment_bp.route('/competencies', methods=['GET'])
@jwt_required()
def get_competencies():
    """Return all competencies grouped by domain."""
    comps = Competency.query.all()
    by_domain = {}
    for c in comps:
        d = c.domain or 'General'
        by_domain.setdefault(d, []).append(c.to_dict())
    return jsonify({'domains': by_domain, 'total': len(comps)}), 200


@assessment_bp.route('/questions', methods=['GET'])
@jwt_required()
def get_questions():
    """
    Get assessment questions for selected competencies.
    Query params: competency_ids (comma-separated), count (per competency, default 5)
    """
    comp_ids_str = request.args.get('competency_ids', '')
    count_raw = request.args.get('count', '5')

    # Validate count param
    try:
        count = int(count_raw)
        if count < 1 or count > 20:
            raise ValueError
    except ValueError:
        count = 5

    if not comp_ids_str:
        comp_ids = [c.id for c in Competency.query.all()]
    else:
        # Strict integer parsing — ignore any non-digit tokens
        comp_ids = [int(x) for x in comp_ids_str.split(',') if x.strip().isdigit()]

    all_questions = []
    for comp_id in comp_ids:
        qs = Question.query.filter_by(competency_id=comp_id).all()
        sampled = random.sample(qs, min(count, len(qs)))
        for q in sampled:
            qd = q.to_dict()
            qd.pop('correct_answer', None)  # don't send answer to client
            qd.pop('explanation', None)
            all_questions.append(qd)

    random.shuffle(all_questions)
    return jsonify({'questions': all_questions, 'total': len(all_questions)}), 200


@assessment_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_assessment():
    """
    Submit assessment answers and get competency gap analysis.
    Body: {answers: [{question_id, selected_option}], time_taken: seconds}
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    answers = data.get('answers', [])
    time_taken = data.get('time_taken', 0)

    if not isinstance(answers, list) or not answers:
        return jsonify({'error': 'No answers provided'}), 400

    # Sanitize time_taken
    try:
        time_taken = int(time_taken)
        if time_taken < 0 or time_taken > 86400:
            time_taken = 0
    except (TypeError, ValueError):
        time_taken = 0

    # Look up questions and evaluate
    competency_scores = {}  # comp_id -> {correct, total, wrong_ids, questions}

    for ans in answers:
        if not isinstance(ans, dict):
            continue
        q = Question.query.get(ans.get('question_id'))
        if not q:
            continue
        selected = ans.get('selected_option')
        # Validate selected_option is a valid integer index 0–3
        if not isinstance(selected, int) or selected not in range(4):
            continue
        comp_id = q.competency_id
        if comp_id not in competency_scores:
            competency_scores[comp_id] = {
                'correct': 0, 'total': 0, 'wrong_ids': [],
                'weighted_answers': []
            }

        is_correct = (selected == q.correct_answer)
        competency_scores[comp_id]['total'] += 1
        competency_scores[comp_id]['weighted_answers'].append({
            'question_id': q.id,
            'is_correct': is_correct,
            'difficulty': q.difficulty,
            'selected_option': ans.get('selected_option'),
            'correct_answer': q.correct_answer,
            'explanation': q.explanation
        })
        if is_correct:
            competency_scores[comp_id]['correct'] += 1
        else:
            competency_scores[comp_id]['wrong_ids'].append(q.id)

    # Calculate scores and save results
    assessment_results = []
    for comp_id, data_c in competency_scores.items():
        comp = Competency.query.get(comp_id)
        score_info = calculate_weighted_score(
            data_c['weighted_answers'], []
        )
        weighted_score = score_info['weighted_score']

        result = AssessmentResult(
            user_id=user_id,
            competency_id=comp_id,
            score=weighted_score,
            total_questions=data_c['total'],
            correct_answers=data_c['correct'],
            wrong_questions=json.dumps(data_c['wrong_ids']),
            time_taken=time_taken
        )
        db.session.add(result)

        assessment_results.append({
            'competency_id': comp_id,
            'competency_name': comp.name if comp else f'Competency {comp_id}',
            'score': weighted_score,
            'raw_score': score_info['raw_score'],
            'correct': data_c['correct'],
            'total': data_c['total'],
            'wrong_question_ids': data_c['wrong_ids'],
            'detailed_answers': data_c['weighted_answers']
        })

    db.session.commit()

    # Analyze gaps
    gap_analysis = analyze_competency_gaps(assessment_results)

    # Add improvement suggestions to each gap
    for gap in gap_analysis['gaps']:
        gap['suggestions'] = get_improvement_suggestions(gap)

    log_data('assessment_submit', user_id=user_id, details={
        'competencies': len(assessment_results),
        'overall_score': gap_analysis.get('overall_score')
    })

    return jsonify({
        'assessment_results': assessment_results,
        'gap_analysis': gap_analysis,
        'message': 'Assessment submitted successfully'
    }), 200


@assessment_bp.route('/history', methods=['GET'])
@jwt_required()
def assessment_history():
    """Get user's past assessment results."""
    user_id = int(get_jwt_identity())
    results = (AssessmentResult.query
               .filter_by(user_id=user_id)
               .order_by(AssessmentResult.taken_at.desc())
               .limit(50).all())

    history = []
    for r in results:
        rd = r.to_dict()
        comp = Competency.query.get(r.competency_id)
        rd['competency_name'] = comp.name if comp else 'Unknown'
        history.append(rd)

    return jsonify({'history': history}), 200


@assessment_bp.route('/latest-gaps', methods=['GET'])
@jwt_required()
def latest_gaps():
    """Get most recent gap analysis for the user (one result per competency)."""
    user_id = int(get_jwt_identity())
    comps = Competency.query.all()
    assessment_results = []

    for comp in comps:
        latest = (AssessmentResult.query
                  .filter_by(user_id=user_id, competency_id=comp.id)
                  .order_by(AssessmentResult.taken_at.desc())
                  .first())
        if latest:
            assessment_results.append({
                'competency_id': comp.id,
                'competency_name': comp.name,
                'score': latest.score,
                'wrong_question_ids': json.loads(latest.wrong_questions) if latest.wrong_questions else []
            })

    if not assessment_results:
        return jsonify({'gaps': [], 'message': 'No assessments taken yet'}), 200

    gap_analysis = analyze_competency_gaps(assessment_results)
    for gap in gap_analysis['gaps']:
        gap['suggestions'] = get_improvement_suggestions(gap)

    return jsonify(gap_analysis), 200

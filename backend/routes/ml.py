"""
ML Inference Routes — expose trained model predictions via API
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import User
from ai_modules.model_inference import (
    predict_gap_level, predict_score,
    predict_completion, get_model_stats
)

ml_bp = Blueprint('ml', __name__)


@ml_bp.route('/predict-gap', methods=['POST'])
@jwt_required()
def predict_gap():
    """
    Predict gap level for a given score + context.
    Body: { score, domain, difficulty, total_questions, correct_answers }
    """
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    result = predict_gap_level(
        score           = float(data.get('score', 50)),
        domain          = data.get('domain', 'Statistics'),
        difficulty      = data.get('difficulty', 'medium'),
        education       = user.designation or 'B.Stat',
        experience_years= data.get('experience_years', 5),
        total_questions = data.get('total_questions', 5),
        correct_answers = data.get('correct_answers', None)
    )
    return jsonify(result), 200


@ml_bp.route('/predict-score', methods=['POST'])
@jwt_required()
def predict_score_route():
    """
    Predict expected score before taking an assessment.
    Body: { domain, difficulty, competency_name }
    """
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    # Estimate experience from designation
    exp_map = {
        'Field Investigator': 2, 'Statistical Assistant': 3,
        'Statistical Officer': 5, 'Senior Statistical Officer': 8,
        'Assistant Director': 7, 'Deputy Director': 12,
        'Director': 18, 'Joint Director': 15, 'Deputy CSG': 20
    }
    exp = exp_map.get(user.designation, 5)

    result = predict_score(
        experience_years = exp,
        domain           = data.get('domain', 'Statistics'),
        difficulty       = data.get('difficulty', 'medium'),
        education        = user.designation or 'B.Stat',
        competency_name  = data.get('competency_name', 'Data Analysis'),
        total_questions  = data.get('total_questions', 5)
    )
    result['user_designation'] = user.designation
    result['estimated_experience'] = exp
    return jsonify(result), 200


@ml_bp.route('/predict-completion', methods=['POST'])
@jwt_required()
def predict_completion_route():
    """
    Predict probability a user will complete a course.
    Body: { difficulty, duration_hours, competency_name }
    """
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    exp_map = {
        'Field Investigator': 2, 'Statistical Assistant': 3,
        'Statistical Officer': 5, 'Senior Statistical Officer': 8,
        'Assistant Director': 7, 'Deputy Director': 12,
        'Director': 18, 'Joint Director': 15, 'Deputy CSG': 20
    }
    exp = exp_map.get(user.designation, 5)

    result = predict_completion(
        experience_years = exp,
        difficulty       = data.get('difficulty', 'beginner'),
        education        = user.designation or 'B.Stat',
        competency_name  = data.get('competency_name', 'Data Analysis'),
        duration_hours   = float(data.get('duration_hours', 3.0))
    )
    return jsonify(result), 200


@ml_bp.route('/model-stats', methods=['GET'])
@jwt_required()
def model_stats():
    """Return trained model accuracy stats."""
    stats = get_model_stats()
    return jsonify(stats), 200

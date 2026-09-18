"""
Progress & Dashboard Routes
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db, User, AssessmentResult, UserProgress, LearningPath, Course, Competency
from utils.security import sanitize_dict
from utils.audit import log_data, log_security
from datetime import datetime, timedelta
import json

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """Comprehensive dashboard data for the logged-in user."""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)

    # Assessment stats
    all_results = AssessmentResult.query.filter_by(user_id=user_id).all()
    comps_assessed = set(r.competency_id for r in all_results)

    # Latest score per competency
    comp_scores = {}
    for comp_id in comps_assessed:
        latest = (AssessmentResult.query
                  .filter_by(user_id=user_id, competency_id=comp_id)
                  .order_by(AssessmentResult.taken_at.desc()).first())
        if latest:
            comp = Competency.query.get(comp_id)
            comp_scores[comp_id] = {
                'competency_name': comp.name if comp else str(comp_id),
                'score': latest.score,
                'taken_at': latest.taken_at.isoformat()
            }

    # Progress stats
    enrolled = UserProgress.query.filter_by(user_id=user_id).all()
    completed = [p for p in enrolled if p.status == 'completed']
    in_progress = [p for p in enrolled if p.status == 'in_progress']

    # Learning paths
    paths = LearningPath.query.filter_by(user_id=user_id).all()
    active_paths = [p for p in paths if p.status == 'active']

    # Overall skill level
    scores = [v['score'] for v in comp_scores.values()]
    overall_score = round(sum(scores) / len(scores), 1) if scores else 0

    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_assessments = [r for r in all_results if r.taken_at >= week_ago]
    recent_completions = [p for p in completed if p.completed_at and p.completed_at >= week_ago]

    # Skill radar data
    radar_data = []
    for cid, info in comp_scores.items():
        radar_data.append({
            'competency': info['competency_name'],
            'score': info['score'],
            'full_mark': 100
        })
    radar_data.sort(key=lambda x: -x['score'])

    # Score trend (last 10 assessments)
    recent_10 = sorted(all_results, key=lambda r: r.taken_at)[-10:]
    trend = []
    for r in recent_10:
        comp = Competency.query.get(r.competency_id)
        trend.append({
            'date': r.taken_at.strftime('%b %d'),
            'score': r.score,
            'competency': comp.name if comp else 'Unknown'
        })

    return jsonify({
        'user': user.to_dict(),
        'stats': {
            'overall_score': overall_score,
            'competencies_assessed': len(comps_assessed),
            'total_assessments': len(all_results),
            'courses_enrolled': len(enrolled),
            'courses_completed': len(completed),
            'courses_in_progress': len(in_progress),
            'active_learning_paths': len(active_paths),
            'recent_assessments_7d': len(recent_assessments),
            'recent_completions_7d': len(recent_completions),
        },
        'competency_scores': list(comp_scores.values()),
        'radar_data': radar_data,
        'score_trend': trend,
        'skill_level': _get_skill_level(overall_score)
    }), 200


@progress_bp.route('/course-progress', methods=['GET'])
@jwt_required()
def course_progress():
    """Get all course progress for the user."""
    user_id = int(get_jwt_identity())
    progs = UserProgress.query.filter_by(user_id=user_id).all()
    result = []
    for p in progs:
        course = Course.query.get(p.course_id)
        if not course:
            continue
        result.append({
            'course_id': p.course_id,
            'course_title': course.title,
            'difficulty': course.difficulty,
            'duration_hours': course.duration_hours,
            'status': p.status,
            'progress_pct': p.progress_pct,
            'started_at': p.started_at.isoformat() if p.started_at else None,
            'completed_at': p.completed_at.isoformat() if p.completed_at else None,
            'igot_course_id': course.igot_course_id
        })
    return jsonify({'progress': result}), 200


@progress_bp.route('/update-course', methods=['POST'])
@jwt_required()
def update_course_progress():
    """Update progress for a specific course."""
    user_id = int(get_jwt_identity())
    raw = request.get_json(silent=True) or {}

    try:
        data = sanitize_dict(raw, {
            'course_id':    {'type': int,   'required': True},
            'progress_pct': {'type': float, 'required': False,
                             'min_value': 0.0, 'max_value': 100.0, 'default': 0.0},
        })
    except ValueError as e:
        log_security('invalid_input', user_id=user_id,
                     details={'action': 'update_course', 'error': str(e)})
        return jsonify({'error': str(e)}), 400

    course_id = data['course_id']
    progress_pct = data['progress_pct']

    if not course_id:
        return jsonify({'error': 'course_id required'}), 400

    prog = UserProgress.query.filter_by(user_id=user_id, course_id=course_id).first()
    if not prog:
        prog = UserProgress(
            user_id=user_id, course_id=course_id,
            status='in_progress', progress_pct=progress_pct,
            started_at=datetime.utcnow()
        )
        db.session.add(prog)
    else:
        prog.progress_pct = progress_pct
        if progress_pct >= 100:
            prog.status = 'completed'
            prog.completed_at = datetime.utcnow()
            _update_learning_path_progress(user_id, course_id)
        elif progress_pct > 0:
            prog.status = 'in_progress'

    db.session.commit()
    log_data('course_progress_update', user_id=user_id, details={
        'course_id': course_id, 'progress_pct': progress_pct
    })
    return jsonify({'message': 'Progress updated', 'progress_pct': progress_pct}), 200


def _update_learning_path_progress(user_id, completed_course_id):
    """Update learning path completion when a course is finished."""
    paths = LearningPath.query.filter_by(user_id=user_id, status='active').all()
    for path in paths:
        try:
            seq = json.loads(path.course_sequence)
        except Exception:
            continue
        if completed_course_id in seq:
            completed_in_path = 0
            for cid in seq:
                p = UserProgress.query.filter_by(
                    user_id=user_id, course_id=cid, status='completed'
                ).first()
                if p:
                    completed_in_path += 1
            path.current_step = completed_in_path
            path.completion_percentage = round(completed_in_path / len(seq) * 100, 1)
            if completed_in_path >= len(seq):
                path.status = 'completed'
    db.session.commit()


def _get_skill_level(score):
    if score >= 85:
        return {'label': 'Expert', 'color': '#27ae60', 'icon': '🏆'}
    elif score >= 70:
        return {'label': 'Proficient', 'color': '#2ecc71', 'icon': '⭐'}
    elif score >= 50:
        return {'label': 'Developing', 'color': '#f39c12', 'icon': '📈'}
    else:
        return {'label': 'Beginner', 'color': '#e74c3c', 'icon': '🌱'}

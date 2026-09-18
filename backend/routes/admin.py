"""
Admin Dashboard Routes
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db, User, AssessmentResult, UserProgress, Competency, Course
from utils.security import sanitize_dict
from utils.audit import log_admin, log_security
from datetime import datetime, timedelta
from functools import wraps
import json

admin_bp = Blueprint('admin', __name__)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            log_security('unauthorized_access', user_id=user_id,
                         details={'route': request.path, 'reason': 'not_admin'})
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper


@admin_bp.route('/stats', methods=['GET'])
@admin_required
def admin_stats():
    admin_id = int(get_jwt_identity())
    total_users = User.query.filter_by(role='employee').count()
    total_assessments = AssessmentResult.query.count()
    total_completions = UserProgress.query.filter_by(status='completed').count()
    total_enrollments = UserProgress.query.count()

    comps = Competency.query.all()
    comp_analytics = []
    for comp in comps:
        results = AssessmentResult.query.filter_by(competency_id=comp.id).all()
        if results:
            avg = sum(r.score for r in results) / len(results)
            comp_analytics.append({
                'competency': comp.name,
                'domain': comp.domain,
                'avg_score': round(avg, 1),
                'assessments_taken': len(results),
                'users_assessed': len(set(r.user_id for r in results))
            })
    comp_analytics.sort(key=lambda x: x['avg_score'])

    week_ago = datetime.utcnow() - timedelta(days=7)
    active_users = (db.session.query(AssessmentResult.user_id)
                    .filter(AssessmentResult.taken_at >= week_ago)
                    .distinct().count())

    log_admin('view_stats', user_id=admin_id)

    return jsonify({
        'platform_stats': {
            'total_users': total_users,
            'total_assessments': total_assessments,
            'total_enrollments': total_enrollments,
            'total_completions': total_completions,
            'active_users_7d': active_users,
            'completion_rate': round(total_completions / max(total_enrollments, 1) * 100, 1)
        },
        'competency_analytics': comp_analytics,
        'weakest_competencies': comp_analytics[:3],
        'strongest_competencies': comp_analytics[-3:][::-1]
    }), 200


@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    admin_id = int(get_jwt_identity())
    users = User.query.filter_by(role='employee').all()
    result = []
    for u in users:
        results = AssessmentResult.query.filter_by(user_id=u.id).all()
        scores = [r.score for r in results]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        completed = UserProgress.query.filter_by(user_id=u.id, status='completed').count()
        result.append({
            **u.to_dict(),
            'avg_score': avg_score,
            'assessments_taken': len(set(r.competency_id for r in results)),
            'courses_completed': completed
        })

    log_admin('list_users', user_id=admin_id, details={'count': len(result)})
    return jsonify({'users': result, 'total': len(result)}), 200


@admin_bp.route('/add-course', methods=['POST'])
@admin_required
def add_course():
    admin_id = int(get_jwt_identity())
    raw = request.get_json(silent=True) or {}

    try:
        data = sanitize_dict(raw, {
            'title':          {'type': str, 'required': True,  'min_length': 3, 'max_length': 200},
            'description':    {'type': str, 'required': False, 'max_length': 1000, 'default': ''},
            'competency_id':  {'type': int, 'required': False, 'default': None},
            'difficulty':     {'type': str, 'required': False,
                               'choices': ['beginner', 'intermediate', 'advanced'],
                               'default': 'beginner'},
            'duration_hours': {'type': float, 'required': False,
                               'min_value': 0.5, 'max_value': 100.0, 'default': 1.0},
            'course_type':    {'type': str, 'required': False,
                               'choices': ['video', 'document', 'quiz', 'interactive'],
                               'default': 'document'},
            'igot_course_id': {'type': str, 'required': False, 'max_length': 100, 'default': ''},
        })
    except ValueError as e:
        log_security('invalid_input', user_id=admin_id,
                     details={'action': 'add_course', 'error': str(e)})
        return jsonify({'error': str(e)}), 400

    # Validate tags separately (it's a list, not a simple scalar)
    tags = raw.get('tags', [])
    if not isinstance(tags, list):
        return jsonify({'error': "'tags' must be a list"}), 400
    tags = [str(t)[:50] for t in tags[:20]]  # cap at 20 tags, 50 chars each

    course = Course(
        title=data['title'],
        description=data['description'],
        competency_id=data['competency_id'],
        difficulty=data['difficulty'],
        duration_hours=data['duration_hours'],
        course_type=data['course_type'],
        igot_course_id=data['igot_course_id'],
        tags=json.dumps(tags)
    )
    db.session.add(course)
    db.session.commit()

    log_admin('add_course', user_id=admin_id, details={
        'course_id': course.id, 'title': data['title']
    })
    return jsonify({'message': 'Course added', 'course': course.to_dict()}), 201

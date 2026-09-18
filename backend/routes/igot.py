"""
iGOT Karmayogi Mock Integration Layer
Simulates real iGOT API endpoints for the prototype.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db, User, Course, UserProgress
from utils.audit import log_data
import os
import json
from datetime import datetime

igot_bp = Blueprint('igot', __name__)

IGOT_BASE = os.getenv('IGOT_API_BASE_URL', 'https://igot-mock.karmayogai.local/api/v1')


def _mock_igot_course(course):
    """Enrich a course with iGOT metadata."""
    return {
        **course,
        'igot_url': f"https://igotkarmayogi.gov.in/course/{course.get('igot_course_id', '')}",
        'provider': 'iGOT Karmayogi',
        'certificate_available': True,
        'government_approved': True,
        'language': 'English/Hindi',
        'enrollment_status': 'open',
    }


@igot_bp.route('/courses', methods=['GET'])
@jwt_required()
def igot_courses():
    """
    Mock iGOT course catalog endpoint.
    In production, this would call the real iGOT API.
    """
    competency_id = request.args.get('competency_id')
    query = Course.query
    if competency_id:
        query = query.filter_by(competency_id=int(competency_id))
    courses = query.all()
    result = [_mock_igot_course(c.to_dict()) for c in courses]
    return jsonify({
        'source': 'iGOT Karmayogi (Mock)',
        'api_version': 'v1',
        'courses': result,
        'total': len(result),
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@igot_bp.route('/enroll', methods=['POST'])
@jwt_required()
def igot_enroll():
    """
    Mock iGOT course enrollment.
    In production: POST to iGOT enrollment API.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    course_id = data.get('course_id')

    if not course_id:
        return jsonify({'error': 'course_id required'}), 400

    course = Course.query.get_or_404(course_id)

    # Check if already enrolled
    existing = UserProgress.query.filter_by(user_id=user_id, course_id=course_id).first()
    if existing:
        return jsonify({
            'message': 'Already enrolled',
            'enrollment': {'course_id': course_id, 'status': existing.status}
        }), 200

    progress = UserProgress(
        user_id=user_id,
        course_id=course_id,
        status='enrolled',
        progress_pct=0.0,
        started_at=datetime.utcnow()
    )
    db.session.add(progress)
    db.session.commit()

    log_data('course_enroll', user_id=user_id, details={'course_id': course_id})

    return jsonify({
        'message': 'Successfully enrolled',
        'igot_enrollment_id': f'IGOT-ENR-{user_id}-{course_id}',
        'course': _mock_igot_course(course.to_dict()),
        'enrollment': {
            'status': 'enrolled',
            'enrolled_at': datetime.utcnow().isoformat(),
            'expected_completion': '30 days'
        }
    }), 201


@igot_bp.route('/profile', methods=['GET'])
@jwt_required()
def igot_profile():
    """
    Mock iGOT learner profile — simulates what iGOT would return for this user.
    """
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)

    enrolled = UserProgress.query.filter_by(user_id=user_id).all()
    completed = [e for e in enrolled if e.status == 'completed']

    return jsonify({
        'igot_user_id': f'IGOT-{user_id:06d}',
        'name': user.name,
        'designation': user.designation,
        'department': user.department,
        'total_enrolled': len(enrolled),
        'total_completed': len(completed),
        'learning_hours': len(completed) * 3.5,  # mock
        'badges': [
            {'name': 'Early Learner', 'earned': len(enrolled) >= 1},
            {'name': 'Consistent Learner', 'earned': len(completed) >= 3},
            {'name': 'Skill Champion', 'earned': len(completed) >= 5},
        ],
        'source': 'iGOT Karmayogi (Mock)'
    }), 200


@igot_bp.route('/sync-progress', methods=['POST'])
@jwt_required()
def sync_progress():
    """
    Simulate syncing user progress back to iGOT platform.
    In production: POST completion data to iGOT API.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    course_id = data.get('course_id')
    progress_pct = data.get('progress_pct', 0)

    progress = UserProgress.query.filter_by(user_id=user_id, course_id=course_id).first()
    if not progress:
        return jsonify({'error': 'Not enrolled in this course'}), 404

    progress.progress_pct = progress_pct
    if progress_pct >= 100:
        progress.status = 'completed'
        progress.completed_at = datetime.utcnow()
    elif progress_pct > 0:
        progress.status = 'in_progress'

    db.session.commit()

    return jsonify({
        'message': 'Progress synced to iGOT',
        'igot_sync_id': f'SYNC-{user_id}-{course_id}-{int(datetime.utcnow().timestamp())}',
        'progress_pct': progress_pct,
        'status': progress.status
    }), 200

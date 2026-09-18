"""
Recommendation Routes — Personalized learning paths
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db, Course, LearningPath, UserProgress, Competency, AssessmentResult
from ai_modules.recommendation_engine import RecommendationEngine
import json

recommendations_bp = Blueprint('recommendations', __name__)
engine = RecommendationEngine()


@recommendations_bp.route('/', methods=['GET'])
@jwt_required()
def get_recommendations():
    """Get personalized course recommendations based on user's competency gaps."""
    user_id = int(get_jwt_identity())

    # Get latest gaps
    comps = Competency.query.all()
    user_gaps = []
    for comp in comps:
        latest = (AssessmentResult.query
                  .filter_by(user_id=user_id, competency_id=comp.id)
                  .order_by(AssessmentResult.taken_at.desc())
                  .first())
        if latest and latest.score < 85:
            user_gaps.append({
                'competency_id': comp.id,
                'competency_name': comp.name,
                'score': latest.score,
                'gap_level': _score_to_level(latest.score),
                'priority': _score_to_priority(latest.score)
            })

    if not user_gaps:
        return jsonify({
            'recommendations': [],
            'message': 'Great job! No significant gaps found. Take an assessment to get recommendations.'
        }), 200

    # Get completed courses
    completed = [p.course_id for p in
                 UserProgress.query.filter_by(user_id=user_id, status='completed').all()]

    # Separate iGOT and NSSTA courses
    igot_courses  = [c.to_dict() for c in Course.query.filter_by(source='igot').all()]
    nssta_courses = [c.to_dict() for c in Course.query.filter_by(source='nssta').all()]
    all_courses   = igot_courses + nssta_courses

    engine.fit(all_courses)

    # iGOT recommendations (top 6)
    igot_recs = engine.get_recommendations(user_gaps, igot_courses, completed, top_n=6)

    # NSSTA recommendations — match by domain/competency (top 4)
    nssta_recs = _get_nssta_recommendations(user_gaps, nssta_courses, completed)

    return jsonify({
        'recommendations': igot_recs,
        'nssta_recommendations': nssta_recs,
        'gap_count': len(user_gaps),
        'top_gap': user_gaps[0] if user_gaps else None
    }), 200


@recommendations_bp.route('/learning-path', methods=['POST'])
@jwt_required()
def generate_learning_path():
    """Generate or retrieve a learning path for a specific competency."""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    comp_id = data.get('competency_id')

    if not comp_id:
        return jsonify({'error': 'competency_id required'}), 400

    # Check if path already exists
    existing = LearningPath.query.filter_by(
        user_id=user_id, competency_id=comp_id, status='active'
    ).first()

    if existing:
        path_courses = _enrich_path(existing)
        return jsonify({'learning_path': existing.to_dict(), 'courses': path_courses}), 200

    # Get latest score for this comp
    latest = (AssessmentResult.query
              .filter_by(user_id=user_id, competency_id=comp_id)
              .order_by(AssessmentResult.taken_at.desc())
              .first())

    score = latest.score if latest else 0
    gap = {
        'competency_id': comp_id,
        'competency_name': Competency.query.get(comp_id).name,
        'score': score,
        'gap_level': _score_to_level(score)
    }

    all_courses = [c.to_dict() for c in Course.query.all()]
    course_ids = engine.build_learning_path(gap, all_courses)

    if not course_ids:
        return jsonify({'error': 'No courses found for this competency'}), 404

    path = LearningPath(
        user_id=user_id,
        competency_id=comp_id,
        course_sequence=json.dumps(course_ids),
        current_step=0,
        status='active',
        completion_percentage=0.0
    )
    db.session.add(path)
    db.session.commit()

    path_courses = _enrich_path(path)
    return jsonify({'learning_path': path.to_dict(), 'courses': path_courses}), 201


@recommendations_bp.route('/learning-paths', methods=['GET'])
@jwt_required()
def get_learning_paths():
    """Get all learning paths for the current user."""
    user_id = int(get_jwt_identity())
    paths = LearningPath.query.filter_by(user_id=user_id).all()
    result = []
    for p in paths:
        pd = p.to_dict()
        comp = Competency.query.get(p.competency_id)
        pd['competency_name'] = comp.name if comp else 'Unknown'
        pd['courses'] = _enrich_path(p)
        result.append(pd)
    return jsonify({'learning_paths': result}), 200


@recommendations_bp.route('/courses', methods=['GET'])
@jwt_required()
def get_all_courses():
    """Get all available courses, optionally filtered by competency, difficulty, or source."""
    comp_id    = request.args.get('competency_id')
    difficulty = request.args.get('difficulty')
    source     = request.args.get('source')  # 'igot' | 'nssta' | None (all)

    query = Course.query
    if comp_id:
        query = query.filter_by(competency_id=int(comp_id))
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if source in ('igot', 'nssta'):
        query = query.filter_by(source=source)

    courses = query.all()
    result = []
    for c in courses:
        cd = c.to_dict()
        comp = Competency.query.get(c.competency_id)
        cd['competency_name'] = comp.name if comp else 'Unknown'
        cd['provider'] = (
            'NSSTA TPAC — MoSPI, Govt. of India'
            if c.source == 'nssta' else 'iGOT Karmayogi'
        )
        result.append(cd)

    igot_count  = sum(1 for r in result if r.get('source') == 'igot')
    nssta_count = sum(1 for r in result if r.get('source') == 'nssta')

    return jsonify({
        'courses': result,
        'total': len(result),
        'igot_count': igot_count,
        'nssta_count': nssta_count
    }), 200


def _score_to_level(score):
    if score < 50:
        return 'critical'
    elif score < 70:
        return 'moderate'
    elif score < 85:
        return 'minor'
    return 'proficient'


def _score_to_priority(score):
    if score < 50:
        return 1
    elif score < 70:
        return 2
    elif score < 85:
        return 3
    return 4


def _get_nssta_recommendations(user_gaps, nssta_courses, completed_ids):
    """
    Match NSSTA TPAC programmes to user gaps by competency_id.
    Returns top 4 most relevant NSSTA programmes with reason text.
    """
    if not nssta_courses or not user_gaps:
        return []

    completed = set(completed_ids or [])
    available = [c for c in nssta_courses if c['id'] not in completed]
    if not available:
        return []

    results = []
    seen = set()

    for gap in sorted(user_gaps, key=lambda g: g.get('priority', 4)):
        comp_id    = gap.get('competency_id')
        comp_name  = gap.get('competency_name', '')
        gap_level  = gap.get('gap_level', 'minor')
        score      = gap.get('score', 100)

        # Direct competency match first
        matching = [c for c in available
                    if c.get('competency_id') == comp_id and c['id'] not in seen]

        # Fallback: keyword match on title/tags
        if not matching:
            keywords = comp_name.lower().split()
            matching = [
                c for c in available
                if any(kw in (c.get('title', '') + ' ' +
                              ' '.join(c.get('tags', []))).lower()
                       for kw in keywords)
                and c['id'] not in seen
            ]

        for course in matching[:2]:  # max 2 per gap
            seen.add(course['id'])
            urgency_label = (
                'Critical gap — foundational programme recommended'
                if gap_level == 'critical' else
                'Moderate gap — intermediate programme recommended'
                if gap_level == 'moderate' else
                'Minor gap — advanced programme recommended'
            )
            results.append({
                **course,
                'recommended_for': comp_name,
                'gap_level': gap_level,
                'reason': f"{urgency_label} for {comp_name} (your score: {score:.0f}%)",
                'source': 'nssta',
                'provider': 'NSSTA TPAC — MoSPI, Govt. of India',
                'apply_url': 'https://mospi.gov.in/training'
            })

        if len(results) >= 4:
            break

    return results


def _enrich_path(path_obj):
    """Return full course objects for a learning path."""
    try:
        ids = json.loads(path_obj.course_sequence)
    except Exception:
        ids = []
    courses = []
    for cid in ids:
        c = Course.query.get(cid)
        if c:
            courses.append(c.to_dict())
    return courses

"""
Competency Gap Analyzer
Analyzes assessment results and identifies weak areas using scoring + NLP similarity.
"""
import numpy as np
from sklearn.preprocessing import MinMaxScaler


COMPETENCY_WEIGHTS = {
    'easy': 1.0,
    'medium': 1.5,
    'hard': 2.0
}

GAP_THRESHOLDS = {
    'critical': 50.0,   # score < 50 → critical gap
    'moderate': 70.0,   # 50-70 → moderate gap
    'minor': 85.0,      # 70-85 → minor gap
    'proficient': 100.0 # >85 → proficient
}


def calculate_weighted_score(answers: list, questions: list) -> dict:
    """
    Calculate weighted score based on question difficulty.
    answers: list of {question_id, selected_option, is_correct, difficulty}
    questions: list of question dicts
    """
    if not answers:
        return {'weighted_score': 0, 'raw_score': 0, 'total_weight': 0}

    total_weight = 0
    earned_weight = 0
    correct = 0

    for ans in answers:
        diff = ans.get('difficulty', 'medium')
        weight = COMPETENCY_WEIGHTS.get(diff, 1.5)
        total_weight += weight
        if ans.get('is_correct'):
            earned_weight += weight
            correct += 1

    weighted_score = (earned_weight / total_weight * 100) if total_weight > 0 else 0
    raw_score = (correct / len(answers) * 100) if answers else 0

    return {
        'weighted_score': round(weighted_score, 2),
        'raw_score': round(raw_score, 2),
        'correct': correct,
        'total': len(answers),
        'total_weight': total_weight
    }


def classify_gap(score: float) -> dict:
    """Classify a score into a gap category with priority."""
    if score < GAP_THRESHOLDS['critical']:
        return {'level': 'critical', 'priority': 1, 'label': 'Critical Gap', 'color': '#e74c3c'}
    elif score < GAP_THRESHOLDS['moderate']:
        return {'level': 'moderate', 'priority': 2, 'label': 'Moderate Gap', 'color': '#e67e22'}
    elif score < GAP_THRESHOLDS['minor']:
        return {'level': 'minor', 'priority': 3, 'label': 'Minor Gap', 'color': '#f39c12'}
    else:
        return {'level': 'proficient', 'priority': 4, 'label': 'Proficient', 'color': '#27ae60'}


def analyze_competency_gaps(assessment_results: list) -> dict:
    """
    Main function: analyze multiple competency assessment results.
    assessment_results: list of {competency_id, competency_name, score, wrong_question_ids}
    Returns ranked gaps and recommendations priority.
    """
    gaps = []
    strengths = []

    for result in assessment_results:
        score = result.get('score', 0)
        gap_info = classify_gap(score)

        entry = {
            'competency_id': result.get('competency_id'),
            'competency_name': result.get('competency_name'),
            'score': score,
            'gap_level': gap_info['level'],
            'priority': gap_info['priority'],
            'label': gap_info['label'],
            'color': gap_info['color'],
            'wrong_questions': result.get('wrong_question_ids', [])
        }

        if gap_info['level'] in ('critical', 'moderate', 'minor'):
            gaps.append(entry)
        else:
            strengths.append(entry)

    # Sort gaps by priority (critical first), then by score (lowest first)
    gaps.sort(key=lambda x: (x['priority'], x['score']))

    overall_score = np.mean([r.get('score', 0) for r in assessment_results]) if assessment_results else 0

    return {
        'overall_score': round(float(overall_score), 2),
        'gaps': gaps,
        'strengths': strengths,
        'total_competencies': len(assessment_results),
        'gap_count': len(gaps),
        'top_priority_gap': gaps[0] if gaps else None,
        'summary': _generate_summary(gaps, strengths, overall_score)
    }


def _generate_summary(gaps, strengths, overall_score):
    if not gaps:
        return "Excellent! No significant competency gaps detected. Keep up the great work!"
    critical = [g for g in gaps if g['gap_level'] == 'critical']
    moderate = [g for g in gaps if g['gap_level'] == 'moderate']
    parts = []
    if critical:
        names = ', '.join(g['competency_name'] for g in critical[:2])
        parts.append(f"Critical gaps in: {names}")
    if moderate:
        names = ', '.join(g['competency_name'] for g in moderate[:2])
        parts.append(f"Moderate gaps in: {names}")
    parts.append(f"Overall score: {overall_score:.1f}%")
    return '. '.join(parts) + '. Personalized learning path generated.'


def get_improvement_suggestions(gap_entry: dict) -> list:
    """Generate improvement suggestions for a specific gap."""
    level = gap_entry.get('gap_level', 'moderate')
    name = gap_entry.get('competency_name', 'this competency')
    suggestions = {
        'critical': [
            f"Start with foundational concepts of {name}",
            "Complete all beginner-level courses before advancing",
            "Practice with daily 15-minute exercises",
            "Take a diagnostic quiz after each module"
        ],
        'moderate': [
            f"Review core principles of {name}",
            "Focus on intermediate-level courses",
            "Apply concepts through practice problems",
            "Re-take the assessment after completing 2 courses"
        ],
        'minor': [
            f"Brush up on advanced topics in {name}",
            "Complete 1-2 targeted courses",
            "Practice with challenging case studies"
        ]
    }
    return suggestions.get(level, suggestions['moderate'])

"""
KarmayogAI — Model Inference
Loads trained .pkl models and exposes prediction functions
used by the backend routes.
"""
import os
import pickle
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'trained_models')

# ── Load models at import time ────────────────────────────────────────────
def _load(name):
    path = os.path.join(MODEL_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return pickle.load(f)

_gap_data        = _load('gap_classifier.pkl')
_score_data      = _load('score_predictor.pkl')
_completion_data = _load('completion_predictor.pkl')
_metadata        = _load('metadata.pkl')

models_loaded = all([_gap_data, _score_data, _completion_data])


# ── 1. Predict gap level from score + features ───────────────────────────

def predict_gap_level(score: float, domain: str, difficulty: str,
                      education: str = 'B.Stat', experience_years: int = 5,
                      total_questions: int = 5, correct_answers: int = None) -> dict:
    """
    Predict gap level using trained Random Forest classifier.
    Falls back to rule-based if model not loaded.
    """
    if correct_answers is None:
        correct_answers = int(score / 100 * total_questions)

    if not _gap_data:
        # Fallback: rule-based
        return _rule_based_gap(score)

    try:
        domain_enc  = _gap_data['domain_enc']
        diff_enc    = _gap_data['diff_enc']
        edu_enc     = _gap_data['edu_enc']
        model       = _gap_data['model']

        d_enc  = _safe_encode(domain_enc, domain, 0)
        df_enc = _safe_encode(diff_enc, difficulty, 1)
        e_enc  = _safe_encode(edu_enc, education, 0)

        X = np.array([[score, d_enc, df_enc, e_enc, experience_years,
                        total_questions, correct_answers]])

        level = model.predict(X)[0]
        proba = model.predict_proba(X)[0]
        confidence = round(float(max(proba)) * 100, 1)

        return {
            'gap_level':  level,
            'confidence': confidence,
            'source':     'ml_model',
            **_gap_meta(level)
        }
    except Exception:
        return _rule_based_gap(score)


# ── 2. Predict expected score ─────────────────────────────────────────────

def predict_score(experience_years: int, domain: str, difficulty: str,
                  education: str = 'B.Stat', competency_name: str = 'Data Analysis',
                  total_questions: int = 5) -> dict:
    """
    Predict expected competency score for a user profile.
    Useful for showing 'predicted baseline' before assessment.
    """
    if not _score_data:
        return {'predicted_score': 60.0, 'source': 'fallback'}

    try:
        domain_enc = _score_data['domain_enc']
        diff_enc   = _score_data['diff_enc']
        edu_enc    = _score_data['edu_enc']
        comp_enc   = _score_data['comp_enc']
        model      = _score_data['model']

        d_enc  = _safe_encode(domain_enc,  domain,           0)
        df_enc = _safe_encode(diff_enc,    difficulty,        1)
        e_enc  = _safe_encode(edu_enc,     education,         0)
        c_enc  = _safe_encode(comp_enc,    competency_name,   0)
        exp    = float(experience_years)

        X = np.array([[exp, exp**2, d_enc, df_enc, e_enc, c_enc, total_questions]])
        predicted = float(model.predict(X)[0])
        predicted = round(max(0.0, min(100.0, predicted)), 1)

        return {
            'predicted_score': predicted,
            'gap_level': _rule_based_gap(predicted)['gap_level'],
            'source': 'ml_model'
        }
    except Exception:
        return {'predicted_score': 60.0, 'source': 'fallback'}


# ── 3. Predict course completion probability ─────────────────────────────

def predict_completion(experience_years: int, difficulty: str,
                       education: str = 'B.Stat',
                       competency_name: str = 'Data Analysis',
                       duration_hours: float = 3.0) -> dict:
    """
    Predict probability that a user will complete a given course.
    Returns probability 0-1 and recommendation.
    """
    if not _completion_data:
        return {'completion_probability': 0.65, 'source': 'fallback'}

    try:
        diff_enc = _completion_data['diff_enc']
        edu_enc  = _completion_data['edu_enc']
        comp_enc = _completion_data['comp_enc']
        model    = _completion_data['model']

        df_enc = _safe_encode(diff_enc, difficulty,      0)
        e_enc  = _safe_encode(edu_enc,  education,       0)
        c_enc  = _safe_encode(comp_enc, competency_name, 0)

        X = np.array([[float(experience_years), df_enc, e_enc, c_enc, duration_hours]])
        proba = float(model.predict_proba(X)[0][1])

        return {
            'completion_probability': round(proba, 3),
            'completion_pct': round(proba * 100, 1),
            'likely_to_complete': proba >= 0.5,
            'recommendation': (
                'Highly likely to complete — great fit!' if proba >= 0.7 else
                'Likely to complete with consistent effort.' if proba >= 0.5 else
                'May need extra motivation — consider shorter course first.'
            ),
            'source': 'ml_model'
        }
    except Exception:
        return {'completion_probability': 0.65, 'source': 'fallback'}


def get_model_stats() -> dict:
    """Return model accuracy stats for admin dashboard."""
    if not _metadata:
        return {'loaded': False}
    return {
        'loaded': models_loaded,
        'gap_classifier_accuracy':      round(_metadata.get('gap_classifier', {}).get('accuracy', 0) * 100, 1),
        'score_predictor_mae':          round(_metadata.get('score_predictor', {}).get('mae', 0), 1),
        'completion_predictor_accuracy':round(_metadata.get('completion_predictor', {}).get('accuracy', 0) * 100, 1),
        'training_rows':                _metadata.get('training_rows', {}),
    }


# ── Helpers ───────────────────────────────────────────────────────────────

def _safe_encode(encoder, value, default=0):
    try:
        return int(encoder.transform([value])[0])
    except Exception:
        return default

def _rule_based_gap(score: float) -> dict:
    if score < 50:
        return {'gap_level': 'critical',   'priority': 1, 'label': 'Critical Gap',  'color': '#e74c3c', 'source': 'rule_based'}
    elif score < 70:
        return {'gap_level': 'moderate',   'priority': 2, 'label': 'Moderate Gap',  'color': '#e67e22', 'source': 'rule_based'}
    elif score < 85:
        return {'gap_level': 'minor',      'priority': 3, 'label': 'Minor Gap',     'color': '#f39c12', 'source': 'rule_based'}
    else:
        return {'gap_level': 'proficient', 'priority': 4, 'label': 'Proficient',    'color': '#27ae60', 'source': 'rule_based'}

def _gap_meta(level: str) -> dict:
    meta = {
        'critical':   {'priority': 1, 'label': 'Critical Gap',  'color': '#e74c3c'},
        'moderate':   {'priority': 2, 'label': 'Moderate Gap',  'color': '#e67e22'},
        'minor':      {'priority': 3, 'label': 'Minor Gap',     'color': '#f39c12'},
        'proficient': {'priority': 4, 'label': 'Proficient',    'color': '#27ae60'},
    }
    return meta.get(level, meta['moderate'])

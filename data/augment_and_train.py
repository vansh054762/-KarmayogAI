"""
KarmayogAI — Augment training data with real NSSTA domains + retrain all models.

This script:
1. Loads existing CSVs (assessment_results, course_enrollments, users)
2. Augments with synthetic rows for NSSTA Official Statistics domains
   (domains confirmed from real mospi.gov.in PDFs)
3. Saves augmented CSVs
4. Retrains all 3 ML models on the enriched dataset
5. Saves updated .pkl files

Run: python data/augment_and_train.py
"""

import os
import sys
import random
import pickle
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, mean_absolute_error, accuracy_score

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE   = os.path.dirname(__file__)
DATA   = BASE
MODEL  = os.path.abspath(os.path.join(BASE, '..', 'backend', 'ai_modules', 'trained_models'))
os.makedirs(MODEL, exist_ok=True)

random.seed(42)
np.random.seed(42)

# ── Real NSSTA competency domains (from mospi.gov.in PDFs) ───────────────────
NSSTA_DOMAINS = [
    'Survey Design & Sampling',
    'National Accounts Statistics',
    'Price & Index Statistics',
    'Agricultural Statistics',
    'Labour & Employment Statistics',
    'SDG & Metadata Standards',
    'GIS & Geospatial Analysis',
    'Python & R for Statistics',
    'Data Privacy & Cybersecurity',
    'Industrial & Economic Statistics',
]

NSSTA_COMPETENCIES = [
    'Survey Methodology',
    'Sampling Techniques',
    'National Accounts',
    'Price Statistics',
    'Index Numbers',
    'Agricultural Statistics',
    'Labour Statistics',
    'SDG Indicators',
    'Metadata Standards',
    'GIS Analysis',
    'Python Programming',
    'R Programming',
    'Data Privacy',
    'Cybersecurity',
    'Industrial Statistics',
    'Economic Census',
]

DESIGNATIONS = [
    'Junior Statistical Officer', 'Statistical Officer',
    'Senior Statistical Officer', 'Statistical Examiner',
    'Statistical Superintendent', 'Deputy Director (Statistics)',
    'Director', 'Additional Director General',
    'ISS Probationer', 'SSS Officer',
]

DEPARTMENTS = [
    'CSO', 'NSSO', 'MoSPI', 'NSO', 'NSSTA',
    'State Statistical Bureau', 'DES Maharashtra',
    'DES Tamil Nadu', 'DES UP', 'DES West Bengal',
    'DPIIT', 'Ministry of Agriculture', 'Ministry of Labour',
    'Planning Department', 'Finance Department',
]

EDUCATIONS = ['M.Stat', 'M.Sc Statistics', 'M.Sc Mathematics',
              'MBA', 'B.Stat', 'B.Sc Statistics', 'Ph.D Statistics',
              'M.A Economics', 'M.Sc Economics']

DIFFICULTIES = ['beginner', 'intermediate', 'advanced']

def gap_level(score):
    if score < 50:   return 'critical'
    if score < 70:   return 'moderate'
    if score < 85:   return 'minor'
    return 'proficient'

def priority(score):
    if score < 50:   return 1
    if score < 70:   return 2
    if score < 85:   return 3
    return 4

def weighted_score(correct, total, difficulty):
    w = {'beginner': 1.0, 'intermediate': 1.5, 'advanced': 2.0}
    wt = w.get(difficulty, 1.0)
    raw = correct / total if total > 0 else 0
    # Add noise
    score = (raw * 100 * wt) + random.gauss(0, 5)
    return round(max(0, min(100, score)), 1)

def simulate_score(exp_years, domain, difficulty, education):
    """Simulate realistic score based on profile — mirrors real NSSTA patterns."""
    base = 50
    # Experience boost (diminishing returns — mirrors real ISS progression)
    base += min(exp_years * 2.5, 25)
    # Education boost
    edu_boost = {'Ph.D Statistics': 15, 'M.Stat': 12, 'M.Sc Statistics': 10,
                 'M.Sc Mathematics': 8, 'M.Sc Economics': 7, 'M.A Economics': 6,
                 'B.Stat': 5, 'MBA': 4, 'B.Sc Statistics': 3}
    base += edu_boost.get(education, 0)
    # Domain familiarity — stats domains easier for stats educated
    if domain in ['Survey Design & Sampling', 'National Accounts Statistics',
                  'Statistical Methods'] and 'Stat' in education:
        base += 8
    # Difficulty penalty
    diff_penalty = {'beginner': 0, 'intermediate': -8, 'advanced': -18}
    base += diff_penalty.get(difficulty, 0)
    # Add realistic noise
    base += random.gauss(0, 12)
    return round(max(5, min(98, base)), 1)

# ── Load existing data ────────────────────────────────────────────────────────
print("Loading existing datasets...")
assessments  = pd.read_csv(os.path.join(DATA, 'assessment_results.csv'))
users        = pd.read_csv(os.path.join(DATA, 'users.csv'))
enrollments  = pd.read_csv(os.path.join(DATA, 'course_enrollments.csv'))
gap_summary  = pd.read_csv(os.path.join(DATA, 'competency_gap_summary.csv'))

print(f"  Existing assessments : {len(assessments)}")
print(f"  Existing users       : {len(users)}")
print(f"  Existing enrollments : {len(enrollments)}")

# ── Generate new NSSTA-domain users ──────────────────────────────────────────
print("\nGenerating NSSTA-domain users...")

# Starting IDs after existing
max_user_id = users['user_id'].max()
new_users   = []
NEW_USER_COUNT = 80  # Add 80 NSSTA-profile users

for i in range(NEW_USER_COUNT):
    uid         = max_user_id + i + 1
    exp         = random.randint(1, 25)
    edu         = random.choice(EDUCATIONS)
    desig       = random.choices(
        DESIGNATIONS,
        weights=[15, 20, 15, 15, 10, 10, 8, 4, 8, 10],
        k=1
    )[0]
    dept        = random.choice(DEPARTMENTS)
    joined      = (datetime(2024, 1, 1) - timedelta(days=exp * 365 + random.randint(0, 180))).strftime('%Y-%m-%d')
    new_users.append({
        'user_id': uid, 'name': f'Officer_{uid}',
        'email': f'officer{uid}@nssta.gov.in',
        'role': 'employee', 'department': dept,
        'designation': desig, 'experience_years': exp,
        'education': edu, 'joined_date': joined
    })

new_users_df = pd.DataFrame(new_users)
all_users    = pd.concat([users, new_users_df], ignore_index=True)
all_users.to_csv(os.path.join(DATA, 'users.csv'), index=False)
print(f"  Total users: {len(all_users)}")

# ── Generate NSSTA-domain assessment records ──────────────────────────────────
print("\nGenerating NSSTA-domain assessment records...")

max_assess_id = assessments['assessment_id'].max()
new_assessments = []
new_gap_rows    = []

for _, user in new_users_df.iterrows():
    uid       = user['user_id']
    exp       = user['experience_years']
    edu       = user['education']
    dept      = user['department']
    desig     = user['designation']

    # Each NSSTA user assessed on 3-6 competencies
    n_comps = random.randint(3, 6)
    domains_sample = random.sample(NSSTA_DOMAINS, n_comps)

    for domain in domains_sample:
        comp_name  = random.choice([c for c in NSSTA_COMPETENCIES
                                    if any(kw in domain.lower()
                                           for kw in c.lower().split()[:2])]
                                   or [random.choice(NSSTA_COMPETENCIES)])
        difficulty = random.choices(
            DIFFICULTIES,
            weights=[40, 40, 20] if exp < 5 else
                    [20, 50, 30] if exp < 15 else [10, 40, 50],
            k=1
        )[0]

        total_q    = random.choice([5, 8, 10])
        score      = simulate_score(exp, domain, difficulty, edu)
        correct    = round(score / 100 * total_q)
        correct    = max(0, min(total_q, correct))
        time_taken = random.randint(180, 900)
        date       = (datetime(2026, 1, 1) +
                      timedelta(days=random.randint(0, 250))).strftime('%Y-%m-%d')

        max_assess_id += 1
        new_assessments.append({
            'assessment_id':   max_assess_id,
            'user_id':         uid,
            'user_name':       user['name'],
            'department':      dept,
            'competency_id':   random.randint(10, 20),
            'competency_name': comp_name,
            'domain':          domain,
            'score':           score,
            'total_questions': total_q,
            'correct_answers': correct,
            'difficulty_level': difficulty,
            'gap_level':       gap_level(score),
            'time_taken_sec':  time_taken,
            'assessment_date': date,
        })

        new_gap_rows.append({
            'user_id':        uid,
            'user_name':      user['name'],
            'department':     dept,
            'competency_id':  random.randint(10, 20),
            'competency_name': comp_name,
            'domain':         domain,
            'latest_score':   score,
            'gap_level':      gap_level(score),
            'priority':       priority(score),
            'last_assessed':  date,
        })

new_assess_df = pd.DataFrame(new_assessments)
all_assessments = pd.concat([assessments, new_assess_df], ignore_index=True)
all_assessments.to_csv(os.path.join(DATA, 'assessment_results.csv'), index=False)

new_gap_df  = pd.DataFrame(new_gap_rows)
all_gap     = pd.concat([gap_summary, new_gap_df], ignore_index=True)
all_gap.to_csv(os.path.join(DATA, 'competency_gap_summary.csv'), index=False)

print(f"  New assessments added: {len(new_assess_df)}")
print(f"  Total assessments    : {len(all_assessments)}")

# ── Generate NSSTA-domain enrollment records ──────────────────────────────────
print("\nGenerating NSSTA-domain enrollment records...")

max_enroll_id = enrollments['enrollment_id'].max()
new_enrollments = []

NSSTA_COURSES = [
    ('Survey Methodology and Data Analysis', 'Survey Design & Sampling', 'intermediate', 5.0),
    ('National Accounts Statistics', 'National Accounts Statistics', 'intermediate', 5.0),
    ('Price Statistics and Index Numbers', 'Price & Index Statistics', 'intermediate', 4.0),
    ('Agricultural Statistics', 'Agricultural Statistics', 'intermediate', 5.0),
    ('Labour and Employment Statistics (PLFS)', 'Labour & Employment Statistics', 'intermediate', 4.0),
    ('Machine Learning using Python (IIT Madras)', 'Python & R for Statistics', 'advanced', 60.0),
    ('Data Analysis using R', 'Python & R for Statistics', 'intermediate', 5.0),
    ('GIS and Remote Sensing', 'GIS & Geospatial Analysis', 'intermediate', 5.0),
    ('Data Visualization and Dashboard Development', 'GIS & Geospatial Analysis', 'beginner', 4.0),
    ('SDG Indicators and Data Quality', 'SDG & Metadata Standards', 'intermediate', 3.0),
    ('Cybersecurity and Data Privacy', 'Data Privacy & Cybersecurity', 'beginner', 3.0),
    ('Industrial Statistics (IIP & ASI)', 'Industrial & Economic Statistics', 'intermediate', 4.0),
    ('Econometrics and Time Series Analysis', 'Statistical Methods', 'advanced', 5.0),
    ('Advanced Sampling Techniques', 'Survey Design & Sampling', 'advanced', 5.0),
    ('Mid Career Training Programme (MCTP)', 'Leadership & Management', 'advanced', 10.0),
]

for _, user in new_users_df.iterrows():
    uid  = user['user_id']
    exp  = user['experience_years']
    edu  = user['education']

    # Each user enrolled in 2-5 NSSTA courses
    n_courses = random.randint(2, 5)
    sampled   = random.sample(NSSTA_COURSES, n_courses)

    for title, comp_name, difficulty, duration in sampled:
        # Completion probability: higher exp + lower difficulty → more likely
        base_prob = 0.5
        base_prob += min(exp * 0.02, 0.2)
        if difficulty == 'beginner':     base_prob += 0.15
        elif difficulty == 'advanced':   base_prob -= 0.15
        if 'Stat' in edu or 'Math' in edu: base_prob += 0.1
        base_prob = max(0.1, min(0.9, base_prob))

        completed = random.random() < base_prob
        progress  = 100.0 if completed else round(random.uniform(10, 90), 1)
        status    = 'completed' if completed else random.choice(['in_progress', 'enrolled'])

        enroll_date = (datetime(2025, 1, 1) +
                       timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d')
        complete_date = ''
        if completed:
            complete_date = (datetime.strptime(enroll_date, '%Y-%m-%d') +
                             timedelta(days=int(duration * 1.5 + random.randint(1, 30)))).strftime('%Y-%m-%d')

        max_enroll_id += 1
        new_enrollments.append({
            'enrollment_id':  max_enroll_id,
            'user_id':        uid,
            'user_name':      user['name'],
            'department':     user['department'],
            'course_id':      random.randint(100, 200),
            'course_title':   title,
            'competency_name': comp_name,
            'difficulty':     difficulty,
            'duration_hours': duration,
            'status':         status,
            'progress_pct':   progress,
            'igot_course_id': f"NSSTA-{random.randint(1,99):03d}",
            'enrolled_date':  enroll_date,
            'completed_date': complete_date,
        })

new_enroll_df   = pd.DataFrame(new_enrollments)
all_enrollments = pd.concat([enrollments, new_enroll_df], ignore_index=True)
all_enrollments.to_csv(os.path.join(DATA, 'course_enrollments.csv'), index=False)

print(f"  New enrollments added: {len(new_enroll_df)}")
print(f"  Total enrollments    : {len(all_enrollments)}")

# ══════════════════════════════════════════════════════════════════════════════
#  RETRAIN ALL 3 MODELS ON AUGMENTED DATA
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  RETRAINING MODELS ON AUGMENTED DATASET")
print("="*60)

# Reload fresh augmented data
assessments  = pd.read_csv(os.path.join(DATA, 'assessment_results.csv'))
users        = pd.read_csv(os.path.join(DATA, 'users.csv'))
enrollments  = pd.read_csv(os.path.join(DATA, 'course_enrollments.csv'))

print(f"\n  Assessments : {len(assessments)} rows")
print(f"  Users       : {len(users)} rows")
print(f"  Enrollments : {len(enrollments)} rows")

# ── MODEL 1 — Gap Level Classifier ───────────────────────────────────────────
print("\n[1] Training Gap Level Classifier...")

df1 = assessments.merge(
    users[['user_id', 'experience_years', 'education']],
    on='user_id', how='left'
)

domain_enc = LabelEncoder()
diff_enc   = LabelEncoder()
edu_enc    = LabelEncoder()

df1['domain_enc'] = domain_enc.fit_transform(df1['domain'].fillna('Unknown'))
df1['diff_enc']   = diff_enc.fit_transform(df1['difficulty_level'].fillna('intermediate'))
df1['edu_enc']    = edu_enc.fit_transform(df1['education'].fillna('Unknown'))
df1['exp']        = df1['experience_years'].fillna(5)

features_gap = ['score', 'domain_enc', 'diff_enc', 'edu_enc', 'exp',
                'total_questions', 'correct_answers']

X1 = df1[features_gap].values
y1 = df1['gap_level'].values

X1_train, X1_test, y1_train, y1_test = train_test_split(
    X1, y1, test_size=0.2, random_state=42, stratify=y1
)

gap_clf = RandomForestClassifier(
    n_estimators=200, max_depth=10, min_samples_leaf=3,
    random_state=42, class_weight='balanced'
)
gap_clf.fit(X1_train, y1_train)

y1_pred = gap_clf.predict(X1_test)
acc1    = accuracy_score(y1_test, y1_pred)
cv1     = cross_val_score(gap_clf, X1, y1, cv=5, scoring='accuracy').mean()
print(f"  Test Accuracy : {acc1:.3f}")
print(f"  CV Accuracy   : {cv1:.3f}")
print(classification_report(y1_test, y1_pred, zero_division=0))

with open(os.path.join(MODEL, 'gap_classifier.pkl'), 'wb') as f:
    pickle.dump({
        'model': gap_clf, 'domain_enc': domain_enc,
        'diff_enc': diff_enc, 'edu_enc': edu_enc,
        'features': features_gap, 'accuracy': acc1, 'cv_accuracy': cv1
    }, f)
print("  Saved: gap_classifier.pkl")

# ── MODEL 2 — Score Predictor ─────────────────────────────────────────────────
print("\n[2] Training Score Predictor...")

df2 = assessments.merge(
    users[['user_id', 'experience_years', 'education']],
    on='user_id', how='left'
)

domain_enc2 = LabelEncoder()
diff_enc2   = LabelEncoder()
edu_enc2    = LabelEncoder()
comp_enc2   = LabelEncoder()

df2['domain_enc'] = domain_enc2.fit_transform(df2['domain'].fillna('Unknown'))
df2['diff_enc']   = diff_enc2.fit_transform(df2['difficulty_level'].fillna('intermediate'))
df2['edu_enc']    = edu_enc2.fit_transform(df2['education'].fillna('Unknown'))
df2['comp_enc']   = comp_enc2.fit_transform(df2['competency_name'].fillna('Unknown'))
df2['exp']        = df2['experience_years'].fillna(5)
df2['exp_sq']     = df2['exp'] ** 2

features_score = ['exp', 'exp_sq', 'domain_enc', 'diff_enc',
                  'edu_enc', 'comp_enc', 'total_questions']

X2 = df2[features_score].values
y2 = df2['score'].values

X2_train, X2_test, y2_train, y2_test = train_test_split(
    X2, y2, test_size=0.2, random_state=42
)

from sklearn.ensemble import GradientBoostingRegressor
score_pred = GradientBoostingRegressor(
    n_estimators=200, max_depth=4, learning_rate=0.08,
    min_samples_leaf=4, random_state=42
)
score_pred.fit(X2_train, y2_train)

y2_pred = score_pred.predict(X2_test)
mae2    = mean_absolute_error(y2_test, y2_pred)
print(f"  MAE: {mae2:.2f} points")

with open(os.path.join(MODEL, 'score_predictor.pkl'), 'wb') as f:
    pickle.dump({
        'model': score_pred, 'domain_enc': domain_enc2,
        'diff_enc': diff_enc2, 'edu_enc': edu_enc2,
        'comp_enc': comp_enc2, 'features': features_score, 'mae': mae2
    }, f)
print("  Saved: score_predictor.pkl")

# ── MODEL 3 — Course Completion Predictor ─────────────────────────────────────
print("\n[3] Training Course Completion Predictor...")

df3 = enrollments.merge(
    users[['user_id', 'experience_years', 'education']],
    on='user_id', how='left'
)

diff_enc3 = LabelEncoder()
edu_enc3  = LabelEncoder()
comp_enc3 = LabelEncoder()

df3['diff_enc'] = diff_enc3.fit_transform(df3['difficulty'].fillna('intermediate'))
df3['edu_enc']  = edu_enc3.fit_transform(df3['education'].fillna('Unknown'))
df3['comp_enc'] = comp_enc3.fit_transform(df3['competency_name'].fillna('Unknown'))
df3['exp']      = df3['experience_years'].fillna(5)
df3['completed_bin'] = (df3['status'] == 'completed').astype(int)

features_comp = ['exp', 'diff_enc', 'edu_enc', 'comp_enc', 'duration_hours']

df3_clean = df3.dropna(subset=features_comp)
X3 = df3_clean[features_comp].values
y3 = df3_clean['completed_bin'].values

X3_train, X3_test, y3_train, y3_test = train_test_split(
    X3, y3, test_size=0.2, random_state=42, stratify=y3
)

comp_clf = RandomForestClassifier(
    n_estimators=200, max_depth=8, min_samples_leaf=3,
    random_state=42, class_weight='balanced'
)
comp_clf.fit(X3_train, y3_train)

y3_pred = comp_clf.predict(X3_test)
acc3    = accuracy_score(y3_test, y3_pred)
cv3     = cross_val_score(comp_clf, X3, y3, cv=5, scoring='accuracy').mean()
print(f"  Test Accuracy : {acc3:.3f}")
print(f"  CV Accuracy   : {cv3:.3f}")
print(classification_report(y3_test, y3_pred, zero_division=0))

with open(os.path.join(MODEL, 'completion_predictor.pkl'), 'wb') as f:
    pickle.dump({
        'model': comp_clf, 'diff_enc': diff_enc3,
        'edu_enc': edu_enc3, 'comp_enc': comp_enc3,
        'features': features_comp, 'accuracy': acc3
    }, f)
print("  Saved: completion_predictor.pkl")

# ── Save metadata ─────────────────────────────────────────────────────────────
metadata = {
    'gap_classifier':       {'accuracy': acc1, 'cv_accuracy': cv1},
    'score_predictor':      {'mae': mae2},
    'completion_predictor': {'accuracy': acc3, 'cv_accuracy': cv3},
    'training_rows': {
        'assessments': len(assessments),
        'enrollments': len(enrollments),
    },
    'nssta_domains_added': NSSTA_DOMAINS,
    'trained_at': datetime.now().isoformat(),
    'data_source': 'mospi.gov.in / nssta.gov.in + synthetic augmentation',
}
with open(os.path.join(MODEL, 'metadata.pkl'), 'wb') as f:
    pickle.dump(metadata, f)

print("\n" + "="*60)
print("  ALL MODELS RETRAINED SUCCESSFULLY")
print("="*60)
print(f"  Gap Classifier     Accuracy : {acc1*100:.1f}%  (CV: {cv1*100:.1f}%)")
print(f"  Score Predictor    MAE      : {mae2:.1f} points")
print(f"  Completion Pred.   Accuracy : {acc3*100:.1f}%  (CV: {cv3*100:.1f}%)")
print(f"  Training data      : {len(assessments)} assessments, {len(enrollments)} enrollments")
print(f"  NSSTA domains      : {len(NSSTA_DOMAINS)} new domains from mospi.gov.in")
print("="*60)

"""
KarmayogAI — Model Training Script
Trains 3 ML models on the CSV datasets and saves them as .pkl files.

Models:
1. gap_classifier    — predicts Critical/Moderate/Minor/Proficient from score + features
2. score_predictor   — predicts competency score from user profile features
3. completion_predictor — predicts course completion probability

Run: python ai_modules/train_models.py
"""
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, mean_absolute_error, accuracy_score
from sklearn.pipeline import Pipeline

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'trained_models'))
os.makedirs(MODEL_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════
print("Loading datasets...")
assessments  = pd.read_csv(os.path.join(DATA_DIR, 'assessment_results.csv'))
users        = pd.read_csv(os.path.join(DATA_DIR, 'users.csv'))
enrollments  = pd.read_csv(os.path.join(DATA_DIR, 'course_enrollments.csv'))
gap_summary  = pd.read_csv(os.path.join(DATA_DIR, 'competency_gap_summary.csv'))
courses      = pd.read_csv(os.path.join(DATA_DIR, 'courses.csv'))

print(f"  Assessments: {len(assessments)} rows")
print(f"  Users:       {len(users)} rows")
print(f"  Enrollments: {len(enrollments)} rows")
print(f"  Gap summary: {len(gap_summary)} rows")


# ═══════════════════════════════════════════════════════════════════════════
#  MODEL 1 — GAP LEVEL CLASSIFIER
#  Features: score, domain, difficulty_level, experience_years
#  Target:   gap_level (critical/moderate/minor/proficient)
# ═══════════════════════════════════════════════════════════════════════════
print("\n[1] Training Gap Level Classifier...")

# Merge with user experience
df1 = assessments.merge(
    users[['user_id', 'experience_years', 'education']],
    on='user_id', how='left'
)

# Encode categoricals
domain_enc = LabelEncoder()
diff_enc   = LabelEncoder()
edu_enc    = LabelEncoder()

df1['domain_enc']  = domain_enc.fit_transform(df1['domain'].fillna('Unknown'))
df1['diff_enc']    = diff_enc.fit_transform(df1['difficulty_level'].fillna('medium'))
df1['edu_enc']     = edu_enc.fit_transform(df1['education'].fillna('Unknown'))
df1['exp']         = df1['experience_years'].fillna(5)

features_gap = ['score', 'domain_enc', 'diff_enc', 'edu_enc', 'exp',
                'total_questions', 'correct_answers']

X1 = df1[features_gap].values
y1 = df1['gap_level'].values

X1_train, X1_test, y1_train, y1_test = train_test_split(
    X1, y1, test_size=0.2, random_state=42, stratify=y1
)

gap_clf = RandomForestClassifier(
    n_estimators=150, max_depth=8, min_samples_leaf=3,
    random_state=42, class_weight='balanced'
)
gap_clf.fit(X1_train, y1_train)

y1_pred = gap_clf.predict(X1_test)
acc1 = accuracy_score(y1_test, y1_pred)
cv1  = cross_val_score(gap_clf, X1, y1, cv=5, scoring='accuracy').mean()
print(f"  Test Accuracy:  {acc1:.3f}")
print(f"  CV Accuracy:    {cv1:.3f}")
print(classification_report(y1_test, y1_pred, zero_division=0))

# Save model + encoders
model1_data = {
    'model': gap_clf,
    'domain_enc': domain_enc,
    'diff_enc': diff_enc,
    'edu_enc': edu_enc,
    'features': features_gap,
    'accuracy': acc1,
    'cv_accuracy': cv1
}
with open(os.path.join(MODEL_DIR, 'gap_classifier.pkl'), 'wb') as f:
    pickle.dump(model1_data, f)
print("  Saved: gap_classifier.pkl")


# ═══════════════════════════════════════════════════════════════════════════
#  MODEL 2 — SCORE PREDICTOR
#  Features: experience_years, education, domain, difficulty_level
#  Target:   score (regression)
# ═══════════════════════════════════════════════════════════════════════════
print("\n[2] Training Score Predictor...")

df2 = assessments.merge(
    users[['user_id', 'experience_years', 'education']],
    on='user_id', how='left'
)

domain_enc2 = LabelEncoder()
diff_enc2   = LabelEncoder()
edu_enc2    = LabelEncoder()
comp_enc2   = LabelEncoder()

df2['domain_enc']      = domain_enc2.fit_transform(df2['domain'].fillna('Unknown'))
df2['diff_enc']        = diff_enc2.fit_transform(df2['difficulty_level'].fillna('medium'))
df2['edu_enc']         = edu_enc2.fit_transform(df2['education'].fillna('Unknown'))
df2['comp_enc']        = comp_enc2.fit_transform(df2['competency_name'].fillna('Unknown'))
df2['exp']             = df2['experience_years'].fillna(5)
df2['exp_sq']          = df2['exp'] ** 2   # non-linear experience effect

features_score = ['exp', 'exp_sq', 'domain_enc', 'diff_enc', 'edu_enc',
                  'comp_enc', 'total_questions']

X2 = df2[features_score].values
y2 = df2['score'].values

X2_train, X2_test, y2_train, y2_test = train_test_split(
    X2, y2, test_size=0.2, random_state=42
)

score_pred = GradientBoostingRegressor(
    n_estimators=150, max_depth=4, learning_rate=0.08,
    min_samples_leaf=4, random_state=42
)
score_pred.fit(X2_train, y2_train)

y2_pred = score_pred.predict(X2_test)
mae2 = mean_absolute_error(y2_test, y2_pred)
print(f"  MAE:  {mae2:.2f} points")
print(f"  Sample predictions vs actuals:")
for i in range(5):
    print(f"    Predicted: {y2_pred[i]:.1f}  Actual: {y2_test[i]:.1f}")

model2_data = {
    'model': score_pred,
    'domain_enc': domain_enc2,
    'diff_enc': diff_enc2,
    'edu_enc': edu_enc2,
    'comp_enc': comp_enc2,
    'features': features_score,
    'mae': mae2
}
with open(os.path.join(MODEL_DIR, 'score_predictor.pkl'), 'wb') as f:
    pickle.dump(model2_data, f)
print("  Saved: score_predictor.pkl")


# ═══════════════════════════════════════════════════════════════════════════
#  MODEL 3 — COURSE COMPLETION PREDICTOR
#  Features: experience_years, difficulty (encoded), duration_hours, domain
#  Target:   completed (1/0)
# ═══════════════════════════════════════════════════════════════════════════
print("\n[3] Training Course Completion Predictor...")

df3 = enrollments.merge(
    users[['user_id', 'experience_years', 'education']],
    on='user_id', how='left'
)

df3['completed_bin'] = (df3['status'] == 'completed').astype(int)

diff_enc3  = LabelEncoder()
edu_enc3   = LabelEncoder()
comp_enc3  = LabelEncoder()

df3['diff_enc'] = diff_enc3.fit_transform(df3['difficulty'].fillna('beginner'))
df3['edu_enc']  = edu_enc3.fit_transform(df3['education'].fillna('Unknown'))
df3['comp_enc'] = comp_enc3.fit_transform(df3['competency_name'].fillna('Unknown'))
df3['exp']      = df3['experience_years'].fillna(5)
df3['dur']      = df3['duration_hours'].fillna(3.0)

features_comp = ['exp', 'diff_enc', 'edu_enc', 'comp_enc', 'dur']

X3 = df3[features_comp].values
y3 = df3['completed_bin'].values

X3_train, X3_test, y3_train, y3_test = train_test_split(
    X3, y3, test_size=0.2, random_state=42, stratify=y3
)

comp_clf = RandomForestClassifier(
    n_estimators=100, max_depth=6, random_state=42,
    class_weight='balanced'
)
comp_clf.fit(X3_train, y3_train)

y3_pred = comp_clf.predict(X3_test)
acc3 = accuracy_score(y3_test, y3_pred)
cv3  = cross_val_score(comp_clf, X3, y3, cv=5, scoring='accuracy').mean()
print(f"  Test Accuracy:  {acc3:.3f}")
print(f"  CV Accuracy:    {cv3:.3f}")
print(classification_report(y3_test, y3_pred, zero_division=0))

model3_data = {
    'model': comp_clf,
    'diff_enc': diff_enc3,
    'edu_enc': edu_enc3,
    'comp_enc': comp_enc3,
    'features': features_comp,
    'accuracy': acc3,
    'cv_accuracy': cv3
}
with open(os.path.join(MODEL_DIR, 'completion_predictor.pkl'), 'wb') as f:
    pickle.dump(model3_data, f)
print("  Saved: completion_predictor.pkl")


# ═══════════════════════════════════════════════════════════════════════════
#  SAVE METADATA
# ═══════════════════════════════════════════════════════════════════════════
metadata = {
    'gap_classifier':         { 'accuracy': acc1, 'cv_accuracy': cv1, 'features': features_gap },
    'score_predictor':        { 'mae': mae2,       'features': features_score },
    'completion_predictor':   { 'accuracy': acc3, 'cv_accuracy': cv3, 'features': features_comp },
    'training_rows': {
        'assessments': len(df1),
        'enrollments': len(df3),
    }
}
with open(os.path.join(MODEL_DIR, 'metadata.pkl'), 'wb') as f:
    pickle.dump(metadata, f)

print("\n" + "="*55)
print("  All 3 models trained and saved successfully!")
print(f"  Models saved to: {MODEL_DIR}")
print("="*55)
print(f"  Gap Classifier     Accuracy : {acc1:.1%}")
print(f"  Score Predictor    MAE      : {mae2:.1f} points")
print(f"  Completion Pred.   Accuracy : {acc3:.1%}")
print("="*55)

"""
Personalized Learning Recommendation Engine
Uses content-based filtering + cosine similarity on competency embeddings.
"""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import json


class RecommendationEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
        self._fitted = False

    def _build_course_corpus(self, courses: list) -> list:
        """Build text corpus from course metadata for TF-IDF."""
        corpus = []
        for course in courses:
            text = f"{course.get('title', '')} {course.get('description', '')} "
            text += ' '.join(course.get('tags', []))
            corpus.append(text.lower())
        return corpus

    def fit(self, courses: list):
        """Fit vectorizer on all available courses."""
        if not courses:
            return
        corpus = self._build_course_corpus(courses)
        self.vectorizer.fit(corpus)
        self._fitted = True

    def get_recommendations(self, user_gaps: list, all_courses: list,
                             user_completed_ids: list = None, top_n: int = 5) -> list:
        """
        Get personalized course recommendations based on competency gaps.
        user_gaps: list of {competency_id, competency_name, score, gap_level, priority}
        all_courses: list of course dicts from DB
        Returns ordered list of recommended courses with reasoning.
        """
        if not all_courses or not user_gaps:
            return []

        completed = set(user_completed_ids or [])

        # Filter out completed courses
        available = [c for c in all_courses if c['id'] not in completed]
        if not available:
            return []

        # Score each course against each gap
        recommendations = []

        for gap in user_gaps:
            comp_id = gap.get('competency_id')
            gap_score = gap.get('score', 100)
            priority = gap.get('priority', 4)
            gap_level = gap.get('gap_level', 'minor')

            # Get courses matching this competency
            matching = [c for c in available if c.get('competency_id') == comp_id]

            if not matching:
                # Fallback: use TF-IDF similarity on competency name
                matching = self._find_by_similarity(
                    gap.get('competency_name', ''), available
                )
            # Sort matching courses by difficulty progression
            difficulty_order = {'beginner': 0, 'intermediate': 1, 'advanced': 2}
            matching.sort(key=lambda c: difficulty_order.get(c.get('difficulty', 'beginner'), 0))

            for i, course in enumerate(matching[:3]):
                rec_score = self._compute_recommendation_score(
                    gap_score, priority, i, course
                )
                recommendations.append({
                    **course,
                    'recommendation_score': rec_score,
                    'recommended_for': gap.get('competency_name'),
                    'gap_level': gap_level,
                    'reason': self._generate_reason(gap, course, i)
                })

        # Remove duplicates, keep highest score
        seen = {}
        for rec in recommendations:
            cid = rec['id']
            if cid not in seen or rec['recommendation_score'] > seen[cid]['recommendation_score']:
                seen[cid] = rec

        result = sorted(seen.values(), key=lambda x: -x['recommendation_score'])
        return result[:top_n]

    def _compute_recommendation_score(self, gap_score, priority, position, course):
        """Higher score = more recommended."""
        # Invert: lower user score → higher recommendation urgency
        urgency = (100 - gap_score) / 100  # 0-1
        priority_boost = (5 - priority) / 4  # 1.0 for critical, 0 for proficient
        position_penalty = 0.1 * position  # first course in sequence is better
        base = (urgency * 0.5 + priority_boost * 0.5) - position_penalty
        return round(max(0, min(1, base)), 4)

    def _find_by_similarity(self, competency_name: str, courses: list, top_k: int = 3):
        """Fallback: TF-IDF cosine similarity between competency name and course text."""
        if not courses:
            return []
        try:
            corpus = self._build_course_corpus(courses)
            if not self._fitted:
                self.vectorizer.fit(corpus)
                self._fitted = True
            course_vecs = self.vectorizer.transform(corpus)
            query_vec = self.vectorizer.transform([competency_name.lower()])
            sims = cosine_similarity(query_vec, course_vecs)[0]
            top_indices = np.argsort(sims)[::-1][:top_k]
            return [courses[i] for i in top_indices if sims[i] > 0.01]
        except Exception:
            return courses[:top_k]

    def _generate_reason(self, gap: dict, course: dict, position: int) -> str:
        gap_name = gap.get('competency_name', 'this area')
        score = gap.get('score', 0)
        level = course.get('difficulty', 'beginner')
        if position == 0:
            return f"Start here — builds foundation for {gap_name} (your score: {score:.0f}%)"
        elif position == 1:
            return f"Intermediate step to improve {gap_name}"
        else:
            return f"Advanced course to master {gap_name}"

    def build_learning_path(self, gap: dict, courses: list) -> list:
        """
        Build a sequential learning path for a single competency gap.
        Returns ordered list of course IDs.
        """
        comp_id = gap.get('competency_id')
        matching = [c for c in courses if c.get('competency_id') == comp_id]

        difficulty_order = {'beginner': 0, 'intermediate': 1, 'advanced': 2}
        matching.sort(key=lambda c: difficulty_order.get(c.get('difficulty', 'beginner'), 0))

        gap_level = gap.get('gap_level', 'moderate')

        # For critical gaps: start from beginner
        # For moderate: start from intermediate
        # For minor: only advanced
        if gap_level == 'critical':
            path = matching
        elif gap_level == 'moderate':
            path = [c for c in matching if c.get('difficulty') != 'beginner'] or matching
        else:
            path = [c for c in matching if c.get('difficulty') == 'advanced'] or matching[-1:]

        return [c['id'] for c in path]

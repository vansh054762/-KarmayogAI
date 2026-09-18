from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    department = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    role = db.Column(db.String(20), default='employee')  # employee | admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assessments = db.relationship('AssessmentResult', backref='user', lazy=True)
    learning_paths = db.relationship('LearningPath', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'email': self.email,
            'department': self.department, 'designation': self.designation,
            'role': self.role, 'created_at': self.created_at.isoformat()
        }

class Competency(db.Model):
    __tablename__ = 'competencies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(100))
    description = db.Column(db.Text)
    sub_competencies = db.Column(db.Text)  # JSON list

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'domain': self.domain,
            'description': self.description,
            'sub_competencies': json.loads(self.sub_competencies) if self.sub_competencies else []
        }

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    competency_id = db.Column(db.Integer, db.ForeignKey('competencies.id'))
    text = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)  # JSON list of 4 options
    correct_answer = db.Column(db.Integer, nullable=False)  # 0-3 index
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.String(20), default='medium')  # easy|medium|hard
    source = db.Column(db.String(20), default='system')  # system|ai_generated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'competency_id': self.competency_id,
            'text': self.text,
            'options': json.loads(self.options),
            'correct_answer': self.correct_answer,
            'explanation': self.explanation,
            'difficulty': self.difficulty,
            'source': self.source
        }

class AssessmentResult(db.Model):
    __tablename__ = 'assessment_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    competency_id = db.Column(db.Integer, db.ForeignKey('competencies.id'))
    score = db.Column(db.Float, nullable=False)
    total_questions = db.Column(db.Integer)
    correct_answers = db.Column(db.Integer)
    wrong_questions = db.Column(db.Text)  # JSON list of question IDs
    time_taken = db.Column(db.Integer)  # seconds
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id,
            'competency_id': self.competency_id, 'score': self.score,
            'total_questions': self.total_questions,
            'correct_answers': self.correct_answers,
            'wrong_questions': json.loads(self.wrong_questions) if self.wrong_questions else [],
            'time_taken': self.time_taken,
            'taken_at': self.taken_at.isoformat()
        }

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    competency_id = db.Column(db.Integer, db.ForeignKey('competencies.id'))
    difficulty = db.Column(db.String(20), default='beginner')
    duration_hours = db.Column(db.Float)
    course_type = db.Column(db.String(30))  # video|document|quiz|interactive
    igot_course_id = db.Column(db.String(100))  # iGOT platform ID or NSSTA programme ID
    tags = db.Column(db.Text)  # JSON list
    thumbnail_url = db.Column(db.String(300))
    content_url = db.Column(db.String(300))
    source = db.Column(db.String(20), default='igot')  # igot | nssta
    venue = db.Column(db.String(200))          # NSSTA: physical venue
    target_audience = db.Column(db.String(200))  # NSSTA: ISS/SSS/State officers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'description': self.description,
            'competency_id': self.competency_id, 'difficulty': self.difficulty,
            'duration_hours': self.duration_hours, 'course_type': self.course_type,
            'igot_course_id': self.igot_course_id,
            'tags': json.loads(self.tags) if self.tags else [],
            'thumbnail_url': self.thumbnail_url, 'content_url': self.content_url,
            'source': self.source,
            'venue': self.venue,
            'target_audience': self.target_audience,
        }

class LearningPath(db.Model):
    __tablename__ = 'learning_paths'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    competency_id = db.Column(db.Integer, db.ForeignKey('competencies.id'))
    course_sequence = db.Column(db.Text)  # JSON list of course IDs in order
    current_step = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')  # active|completed|paused
    completion_percentage = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id,
            'competency_id': self.competency_id,
            'course_sequence': json.loads(self.course_sequence) if self.course_sequence else [],
            'current_step': self.current_step, 'status': self.status,
            'completion_percentage': self.completion_percentage,
            'created_at': self.created_at.isoformat()
        }

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    status = db.Column(db.String(20), default='not_started')
    progress_pct = db.Column(db.Float, default=0.0)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

class GeneratedQuiz(db.Model):
    __tablename__ = 'generated_quizzes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200))
    source_filename = db.Column(db.String(300))
    questions = db.Column(db.Text)  # JSON list of question objects
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id, 'title': self.title,
            'source_filename': self.source_filename,
            'questions': json.loads(self.questions) if self.questions else [],
            'created_at': self.created_at.isoformat()
        }

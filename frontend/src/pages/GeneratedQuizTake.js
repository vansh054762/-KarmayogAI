import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../utils/api';
import toast from 'react-hot-toast';
import { CheckCircle2, XCircle, ChevronLeft, ChevronRight, Send, Award } from 'lucide-react';

export default function GeneratedQuizTake() {
  const { quizId } = useParams();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [results, setResults] = useState(null);
  const [current, setCurrent] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showReview, setShowReview] = useState(false);

  useEffect(() => {
    api.get(`/quiz/${quizId}`).then(r => { setQuiz(r.data); setLoading(false); })
      .catch(() => { toast.error('Quiz not found'); navigate('/quiz-generator'); });
  }, [quizId, navigate]);

  const submit = async () => {
    const qs = quiz.questions;
    if (Object.keys(answers).length < qs.length) {
      toast.error(`Please answer all ${qs.length} questions`);
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        answers: qs.map(q => ({ question_id: q.id, selected_option: answers[q.id] }))
      };
      const res = await api.post(`/quiz/${quizId}/submit`, payload);
      setResults(res.data);
    } catch { toast.error('Submission failed'); }
    finally { setSubmitting(false); }
  };

  if (loading) return <div className="spinner" />;
  if (!quiz) return null;

  const questions = quiz.questions;
  const letters = ['A', 'B', 'C', 'D'];

  // Results view
  if (results) {
    return (
      <>
        <div className="topbar">
          <div><h1>Quiz Results</h1><p>{quiz.title}</p></div>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/quiz-generator')}>
            <ChevronLeft size={15} /> Back to Quizzes
          </button>
        </div>
        <div className="page-content" style={{ maxWidth: 800, margin: '0 auto' }}>
          {/* Score Banner */}
          <div className="card card-body" style={{
            textAlign: 'center', marginBottom: 24,
            background: results.passed ? 'linear-gradient(135deg, #064e3b, #065f46)' : 'linear-gradient(135deg, #7f1d1d, #991b1b)',
            color: '#fff', border: 'none'
          }}>
            <div style={{ fontSize: 64, marginBottom: 8 }}>{results.passed ? '🎉' : '📚'}</div>
            <div style={{ fontSize: 56, fontWeight: 800, lineHeight: 1 }}>{results.score}%</div>
            <div style={{ fontSize: 18, marginTop: 8, opacity: 0.9 }}>
              {results.correct}/{results.total} Correct
            </div>
            <div style={{ fontSize: 15, marginTop: 6, opacity: 0.8 }}>{results.message}</div>
            <div style={{ marginTop: 16, display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowReview(!showReview)}>
                {showReview ? 'Hide Review' : 'Review Answers'}
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => { setResults(null); setAnswers({}); setCurrent(0); }}>
                Retake Quiz
              </button>
            </div>
          </div>

          {showReview && results.results.map((r, i) => (
            <div key={i} className="card card-body" style={{
              marginBottom: 12,
              borderLeft: `4px solid ${r.is_correct ? '#27ae60' : '#e74c3c'}`
            }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                {r.is_correct
                  ? <CheckCircle2 size={18} color="#27ae60" />
                  : <XCircle size={18} color="#e74c3c" />}
                <span style={{ fontWeight: 600, fontSize: 15 }}>Q{i + 1}. {r.question}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginLeft: 26 }}>
                {r.options.map((opt, idx) => (
                  <div key={idx} style={{
                    padding: '6px 10px', borderRadius: 6, fontSize: 14,
                    background: idx === r.correct_answer ? '#f0fdf4' :
                                idx === r.selected_option && !r.is_correct ? '#fef2f2' : 'transparent',
                    border: `1px solid ${idx === r.correct_answer ? '#bbf7d0' : idx === r.selected_option && !r.is_correct ? '#fecaca' : 'transparent'}`,
                    display: 'flex', alignItems: 'center', gap: 8
                  }}>
                    <span style={{ fontWeight: 700, color: 'var(--text-muted)', minWidth: 20 }}>{letters[idx]}.</span>
                    {opt}
                    {idx === r.correct_answer && <CheckCircle2 size={14} color="#27ae60" style={{ marginLeft: 'auto' }} />}
                    {idx === r.selected_option && !r.is_correct && <XCircle size={14} color="#e74c3c" style={{ marginLeft: 'auto' }} />}
                  </div>
                ))}
                {r.explanation && (
                  <div style={{ marginTop: 6, padding: '8px 10px', background: '#fffbeb', borderRadius: 6, fontSize: 13, color: '#92400e' }}>
                    💡 {r.explanation}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </>
    );
  }

  const q = questions[current];
  const answered = Object.keys(answers).length;

  return (
    <>
      <div className="topbar">
        <div>
          <h1>{quiz.title}</h1>
          <p>Question {current + 1} of {questions.length} · {answered}/{questions.length} answered</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <span className="badge badge-primary">{quiz.source_filename}</span>
        </div>
      </div>

      <div className="page-content" style={{ maxWidth: 760, margin: '0 auto' }}>
        {/* Progress */}
        <div style={{ marginBottom: 20 }}>
          <div className="progress-bar-wrap" style={{ height: 6 }}>
            <div className="progress-bar-fill" style={{ width: `${answered / questions.length * 100}%`, background: 'var(--primary)' }} />
          </div>
        </div>

        <div className="card card-body" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <span className={`badge badge-${q.difficulty}`}>{q.difficulty}</span>
            <span className="badge badge-secondary">{q.type?.replace('_', ' ')}</span>
            <span style={{ marginLeft: 'auto', fontSize: 13, color: 'var(--text-muted)' }}>Q{current + 1}/{questions.length}</span>
          </div>

          <h2 style={{ fontSize: 17, fontWeight: 600, lineHeight: 1.6, marginBottom: 24 }}>{q.text}</h2>

          {q.options.map((opt, idx) => {
            const isSelected = answers[q.id] === idx;
            return (
              <div key={idx} className={`quiz-option ${isSelected ? 'selected' : ''}`}
                onClick={() => setAnswers(p => ({ ...p, [q.id]: idx }))}>
                <span className="option-letter">{letters[idx]}</span>
                <span style={{ fontSize: 14 }}>{opt}</span>
                {isSelected && <CheckCircle2 size={16} style={{ marginLeft: 'auto', color: 'var(--primary)' }} />}
              </div>
            );
          })}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button className="btn btn-secondary" onClick={() => setCurrent(p => Math.max(0, p - 1))} disabled={current === 0}>
            <ChevronLeft size={16} /> Previous
          </button>

          <div style={{ display: 'flex', gap: 4 }}>
            {questions.map((_, i) => (
              <button key={i} onClick={() => setCurrent(i)} style={{
                width: 28, height: 28, borderRadius: 4,
                border: i === current ? '2px solid var(--primary)' : '1px solid var(--border)',
                background: answers[questions[i].id] !== undefined ? '#dbeafe' : i === current ? 'var(--primary-light)' : 'var(--surface)',
                fontSize: 11, fontWeight: 600, color: i === current ? 'var(--primary)' : 'var(--text-muted)', cursor: 'pointer'
              }}>
                {i + 1}
              </button>
            ))}
          </div>

          {current < questions.length - 1 ? (
            <button className="btn btn-primary" onClick={() => setCurrent(p => p + 1)}>
              Next <ChevronRight size={16} />
            </button>
          ) : (
            <button className="btn btn-success" onClick={submit} disabled={submitting}>
              {submitting ? 'Submitting...' : <><Send size={16} /> Submit</>}
            </button>
          )}
        </div>
      </div>
    </>
  );
}

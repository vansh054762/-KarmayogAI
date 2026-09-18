import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import toast from 'react-hot-toast';
import { Clock, ChevronRight, ChevronLeft, Send, CheckCircle2 } from 'lucide-react';

export default function Assessment() {
  const [competencies, setCompetencies] = useState({});
  const [selectedComps, setSelectedComps] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState('select'); // select | quiz | submitting
  const [current, setCurrent] = useState(0);
  const [timer, setTimer] = useState(0);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/assessment/competencies').then(r => setCompetencies(r.data.domains));
  }, []);

  // Timer
  useEffect(() => {
    if (step !== 'quiz') return;
    const id = setInterval(() => setTimer(t => t + 1), 1000);
    return () => clearInterval(id);
  }, [step]);

  const allComps = Object.values(competencies).flat();

  const toggleComp = (id) => {
    setSelectedComps(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);
  };

  const startAssessment = async () => {
    if (selectedComps.length === 0) { toast.error('Select at least one competency'); return; }
    setLoading(true);
    try {
      const res = await api.get('/assessment/questions', {
        params: { competency_ids: selectedComps.join(','), count: 5 }
      });
      setQuestions(res.data.questions);
      setAnswers({});
      setCurrent(0);
      setTimer(0);
      setStep('quiz');
    } catch {
      toast.error('Failed to load questions');
    } finally {
      setLoading(false);
    }
  };

  const selectAnswer = (qId, optIdx) => {
    setAnswers(p => ({ ...p, [qId]: optIdx }));
  };

  const submitAssessment = async () => {
    const unanswered = questions.filter(q => answers[q.id] === undefined);
    if (unanswered.length > 0) {
      toast.error(`${unanswered.length} question(s) unanswered. Please answer all questions.`);
      return;
    }
    setStep('submitting');
    try {
      const payload = {
        answers: questions.map(q => ({
          question_id: q.id,
          selected_option: answers[q.id]
        })),
        time_taken: timer
      };
      const res = await api.post('/assessment/submit', payload);
      navigate('/assessment/result', { state: res.data });
    } catch {
      toast.error('Submission failed. Please try again.');
      setStep('quiz');
    }
  };

  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  if (step === 'submitting') return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '80vh' }}>
      <div className="spinner" />
      <p style={{ marginTop: 16, color: 'var(--text-muted)' }}>Analyzing your competencies...</p>
    </div>
  );

  if (step === 'quiz') {
    const q = questions[current];
    const answered = Object.keys(answers).length;
    const progress = (answered / questions.length) * 100;

    return (
      <>
        <div className="topbar">
          <div>
            <h1>Skill Assessment</h1>
            <p>Question {current + 1} of {questions.length}</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 14 }}>
              <Clock size={16} />
              <span style={{ fontWeight: 600, fontFamily: 'monospace', fontSize: 16 }}>{formatTime(timer)}</span>
            </div>
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{answered}/{questions.length} answered</span>
          </div>
        </div>

        <div className="page-content" style={{ maxWidth: 760, margin: '0 auto' }}>
          {/* Progress */}
          <div style={{ marginBottom: 24 }}>
            <div className="progress-bar-wrap" style={{ height: 6 }}>
              <div className="progress-bar-fill" style={{ width: `${(current + 1) / questions.length * 100}%`, background: 'var(--primary)' }} />
            </div>
          </div>

          {/* Question Card */}
          <div className="card card-body" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
              <span className={`badge badge-${q.difficulty}`}>{q.difficulty}</span>
              <span className="badge badge-primary">{allComps.find(c => c.id === q.competency_id)?.name || 'General'}</span>
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 600, lineHeight: 1.5, marginBottom: 24 }}>
              Q{current + 1}. {q.text}
            </h2>

            {q.options.map((opt, idx) => {
              const isSelected = answers[q.id] === idx;
              const letters = ['A', 'B', 'C', 'D'];
              return (
                <div
                  key={idx}
                  className={`quiz-option ${isSelected ? 'selected' : ''}`}
                  onClick={() => selectAnswer(q.id, idx)}
                >
                  <span className="option-letter">{letters[idx]}</span>
                  <span style={{ fontSize: 15 }}>{opt}</span>
                  {isSelected && <CheckCircle2 size={18} style={{ marginLeft: 'auto', color: 'var(--primary)', minWidth: 18 }} />}
                </div>
              );
            })}
          </div>

          {/* Navigation */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setCurrent(p => Math.max(0, p - 1))}
              disabled={current === 0}
            >
              <ChevronLeft size={16} /> Previous
            </button>

            <div style={{ display: 'flex', gap: 6 }}>
              {questions.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrent(i)}
                  style={{
                    width: 32, height: 32,
                    borderRadius: 6,
                    border: i === current ? '2px solid var(--primary)' : '1px solid var(--border)',
                    background: answers[questions[i].id] !== undefined ? '#dbeafe' : i === current ? 'var(--primary-light)' : 'var(--surface)',
                    fontWeight: 600, fontSize: 12,
                    color: i === current ? 'var(--primary)' : 'var(--text-muted)',
                    cursor: 'pointer'
                  }}
                >
                  {i + 1}
                </button>
              ))}
            </div>

            {current < questions.length - 1 ? (
              <button className="btn btn-primary" onClick={() => setCurrent(p => p + 1)}>
                Next <ChevronRight size={16} />
              </button>
            ) : (
              <button className="btn btn-success" onClick={submitAssessment}>
                <Send size={16} /> Submit Assessment
              </button>
            )}
          </div>
        </div>
      </>
    );
  }

  // Step: select
  return (
    <>
      <div className="topbar">
        <div>
          <h1>Skill Assessment</h1>
          <p>Select competency areas to assess your knowledge and identify skill gaps</p>
        </div>
      </div>
      <div className="page-content" style={{ maxWidth: 900, margin: '0 auto' }}>
        <div className="card card-body" style={{ marginBottom: 20, background: 'var(--primary-light)', border: '1px solid #bfdbfe' }}>
          <strong>How it works:</strong> Select one or more competency areas → Answer 5 questions each →
          AI analyzes your responses → Get personalized gap analysis and learning recommendations.
        </div>

        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <div className="card-title">Select Competency Areas</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{selectedComps.length} selected</div>
          </div>
          <div className="card-body">
            {Object.entries(competencies).map(([domain, comps]) => (
              <div key={domain} style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '.04em' }}>
                  {domain}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                  {comps.map(comp => {
                    const selected = selectedComps.includes(comp.id);
                    return (
                      <button
                        key={comp.id}
                        onClick={() => toggleComp(comp.id)}
                        style={{
                          padding: '10px 16px',
                          borderRadius: 8,
                          border: `2px solid ${selected ? 'var(--primary)' : 'var(--border)'}`,
                          background: selected ? 'var(--primary-light)' : 'var(--surface)',
                          color: selected ? 'var(--primary)' : 'var(--text)',
                          fontWeight: 500, fontSize: 14, cursor: 'pointer',
                          transition: 'all 0.15s',
                          display: 'flex', alignItems: 'center', gap: 6
                        }}
                      >
                        {selected && <CheckCircle2 size={15} />}
                        {comp.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>
            {selectedComps.length > 0
              ? `${selectedComps.length * 5} questions · ~${selectedComps.length * 3} minutes`
              : 'Select at least one competency to begin'}
          </div>
          <button
            className="btn btn-primary btn-lg"
            onClick={startAssessment}
            disabled={selectedComps.length === 0 || loading}
          >
            {loading ? 'Loading...' : 'Start Assessment'} <ChevronRight size={18} />
          </button>
        </div>
      </div>
    </>
  );
}

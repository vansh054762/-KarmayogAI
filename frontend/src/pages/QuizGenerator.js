import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import api from '../utils/api';
import toast from 'react-hot-toast';
import { Upload, FileText, Trash2, Play, BookOpen, Clock } from 'lucide-react';

export default function QuizGenerator() {
  const [file, setFile] = useState(null);
  const [numQuestions, setNumQuestions] = useState(10);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [myQuizzes, setMyQuizzes] = useState([]);
  const [quizzesLoading, setQuizzesLoading] = useState(true);
  const navigate = useNavigate();

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt']
    },
    maxSize: 16 * 1024 * 1024,
    multiple: false,
    onDrop: (accepted, rejected) => {
      if (rejected.length > 0) { toast.error('Invalid file type or size (max 16MB)'); return; }
      if (accepted.length > 0) {
        setFile(accepted[0]);
        if (!title) setTitle(accepted[0].name.replace(/\.[^.]+$/, ''));
      }
    }
  });

  useEffect(() => {
    api.get('/quiz/my-quizzes').then(r => {
      setMyQuizzes(r.data.quizzes);
      setQuizzesLoading(false);
    }).catch(() => setQuizzesLoading(false));
  }, []);

  const handleUpload = async () => {
    if (!file) { toast.error('Please select a file first'); return; }
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('num_questions', numQuestions);
    formData.append('title', title || file.name);
    try {
      const res = await api.post('/quiz/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(`Generated ${res.data.total} questions!`);
      navigate(`/quiz/${res.data.quiz_id}`);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Generation failed');
      setLoading(false);
    }
  };

  const deleteQuiz = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this quiz?')) return;
    await api.delete(`/quiz/${id}`);
    setMyQuizzes(p => p.filter(q => q.id !== id));
    toast.success('Quiz deleted');
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <>
      <div className="topbar">
        <div>
          <h1>AI Quiz Generator</h1>
          <p>Upload any document and let AI generate MCQs automatically</p>
        </div>
      </div>

      <div className="page-content">
        <div className="grid-2" style={{ alignItems: 'start' }}>
          {/* Upload Panel */}
          <div>
            <div className="card card-body" style={{ marginBottom: 16 }}>
              <h3 style={{ marginBottom: 16, fontWeight: 600 }}>Upload Learning Material</h3>

              <div
                {...getRootProps()}
                className={`upload-zone ${isDragActive ? 'drag-active' : ''}`}
                style={{ marginBottom: 16 }}
              >
                <input {...getInputProps()} />
                {file ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'center' }}>
                    <FileText size={32} color="var(--primary)" />
                    <div>
                      <div style={{ fontWeight: 600 }}>{file.name}</div>
                      <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{formatSize(file.size)}</div>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); setFile(null); }}
                      style={{ marginLeft: 8, background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer' }}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                ) : (
                  <div>
                    <Upload size={40} color="var(--text-muted)" style={{ margin: '0 auto 12px', display: 'block' }} />
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>
                      {isDragActive ? 'Drop your file here' : 'Drag & drop or click to upload'}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                      PDF, DOCX, PPTX, TXT · Max 16MB
                    </div>
                  </div>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Quiz Title</label>
                <input className="form-input" placeholder="e.g., Data Analysis Chapter 3" value={title}
                  onChange={e => setTitle(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Number of Questions: <strong>{numQuestions}</strong></label>
                <input type="range" min={5} max={25} step={5} value={numQuestions}
                  onChange={e => setNumQuestions(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--primary)' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                  <span>5 (Quick)</span><span>15 (Standard)</span><span>25 (Comprehensive)</span>
                </div>
              </div>

              <button className="btn btn-primary btn-block btn-lg" onClick={handleUpload} disabled={loading || !file}>
                {loading ? (
                  <><span className="spinner" style={{ width: 18, height: 18, margin: 0, borderWidth: 2 }} /> Generating...</>
                ) : (
                  <><BookOpen size={18} /> Generate {numQuestions} Questions</>
                )}
              </button>
            </div>

            {/* How it works */}
            <div className="card card-body" style={{ background: 'var(--bg)' }}>
              <h4 style={{ marginBottom: 12, fontWeight: 600 }}>How AI Quiz Generation Works</h4>
              {[
                ['📄', 'Upload', 'PDF, DOCX, PPTX or TXT files are accepted'],
                ['🔍', 'Parse', 'Text is extracted and cleaned from your document'],
                ['🧠', 'Analyze', 'AI identifies key concepts and important passages'],
                ['❓', 'Generate', 'MCQs with 4 options, correct answer & explanation'],
                ['✅', 'Validate', 'Quality check ensures questions are accurate'],
              ].map(([icon, step, desc]) => (
                <div key={step} style={{ display: 'flex', gap: 12, marginBottom: 10 }}>
                  <span style={{ fontSize: 18 }}>{icon}</span>
                  <div>
                    <strong style={{ fontSize: 14 }}>{step}</strong>
                    <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* My Quizzes */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">My Generated Quizzes</div>
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{myQuizzes.length} quizzes</span>
            </div>
            <div className="card-body">
              {quizzesLoading ? <div className="spinner" style={{ width: 24, height: 24 }} /> :
               myQuizzes.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                  <BookOpen size={32} style={{ opacity: 0.3, marginBottom: 8 }} />
                  <p>No quizzes yet. Upload a document to get started.</p>
                </div>
              ) : (
                myQuizzes.map(q => (
                  <div key={q.id} className="card" style={{ marginBottom: 12, cursor: 'pointer', transition: 'box-shadow 0.15s' }}
                    onClick={() => navigate(`/quiz/${q.id}`)}
                    onMouseEnter={e => e.currentTarget.style.boxShadow = 'var(--shadow-md)'}
                    onMouseLeave={e => e.currentTarget.style.boxShadow = 'var(--shadow)'}
                  >
                    <div className="card-body" style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{q.title}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 12 }}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                              <BookOpen size={12} /> {q.question_count} questions
                            </span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                              <Clock size={12} /> {new Date(q.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button className="btn btn-primary btn-sm" onClick={e => { e.stopPropagation(); navigate(`/quiz/${q.id}`); }}>
                            <Play size={12} /> Take
                          </button>
                          <button className="btn btn-secondary btn-sm" onClick={(e) => deleteQuiz(q.id, e)}>
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

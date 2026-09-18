import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import toast from 'react-hot-toast';
import { Map, BookOpen, CheckCircle2, Clock, ChevronRight, Play } from 'lucide-react';

const DIFF_COLORS = { beginner: '#059669', intermediate: '#d97706', advanced: '#dc2626' };

export default function LearningPaths() {
  const [paths, setPaths] = useState([]);
  const [competencies, setCompetencies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get('/recommendations/learning-paths'),
      api.get('/assessment/competencies')
    ]).then(([pathsRes, compsRes]) => {
      setPaths(pathsRes.data.learning_paths);
      const allComps = Object.values(compsRes.data.domains).flat();
      setCompetencies(allComps);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const generatePath = async (compId) => {
    setGenerating(compId);
    try {
      const res = await api.post('/recommendations/learning-path', { competency_id: compId });
      setPaths(p => {
        const existing = p.find(x => x.competency_id === compId);
        if (existing) return p.map(x => x.competency_id === compId ? { ...res.data.learning_path, courses: res.data.courses, competency_name: x.competency_name } : x);
        const comp = competencies.find(c => c.id === compId);
        return [...p, { ...res.data.learning_path, courses: res.data.courses, competency_name: comp?.name }];
      });
      toast.success('Learning path generated!');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to generate path');
    } finally {
      setGenerating(null);
    }
  };

  const updateProgress = async (courseId, pct) => {
    await api.post('/progress/update-course', { course_id: courseId, progress_pct: pct });
    toast.success(pct >= 100 ? 'Course completed! 🎉' : 'Progress updated');
    const pathsRes = await api.get('/recommendations/learning-paths');
    setPaths(pathsRes.data.learning_paths);
  };

  if (loading) return <div className="spinner" />;

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Learning Paths</h1>
          <p>AI-generated sequential learning journeys to close your skill gaps</p>
        </div>
      </div>

      <div className="page-content">
        {/* Generate Path for Competency */}
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <div className="card-title">Generate Learning Path</div>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {competencies.map(comp => {
                const hasPath = paths.find(p => p.competency_id === comp.id);
                return (
                  <button
                    key={comp.id}
                    className={`btn ${hasPath ? 'btn-secondary' : 'btn-primary'} btn-sm`}
                    disabled={generating === comp.id}
                    onClick={() => generatePath(comp.id)}
                  >
                    {generating === comp.id ? 'Generating...' :
                     hasPath ? <><CheckCircle2 size={13} /> {comp.name}</> :
                     <><ChevronRight size={13} /> {comp.name}</>}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Learning Paths */}
        {paths.length === 0 ? (
          <div className="card card-body" style={{ textAlign: 'center', padding: '60px 20px' }}>
            <Map size={48} style={{ marginBottom: 12, opacity: 0.3, margin: '0 auto 12px' }} />
            <h3>No Learning Paths Yet</h3>
            <p style={{ color: 'var(--text-muted)', marginTop: 8 }}>
              Click a competency above to generate your personalized learning path.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {paths.map(path => (
              <div key={path.id} className="card">
                <div className="card-header" style={{ paddingBottom: 16 }}>
                  <div>
                    <div className="card-title">{path.competency_name}</div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                      <span className={`badge ${path.status === 'completed' ? 'badge-proficient' : 'badge-primary'}`}>
                        {path.status}
                      </span>
                      <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                        {(path.courses || []).length} courses · {path.completion_percentage?.toFixed(0)}% complete
                      </span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 22, fontWeight: 700 }}>{path.completion_percentage?.toFixed(0)}%</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>completion</div>
                  </div>
                </div>
                <div className="card-body" style={{ paddingTop: 0 }}>
                  {/* Progress Bar */}
                  <div className="progress-bar-wrap" style={{ height: 8, marginBottom: 20 }}>
                    <div className="progress-bar-fill" style={{
                      width: `${path.completion_percentage || 0}%`,
                      background: path.completion_percentage >= 100 ? '#27ae60' : 'var(--primary)'
                    }} />
                  </div>

                  {/* Course Sequence */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {(path.courses || []).map((course, idx) => (
                      <div key={course.id} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        {/* Step indicator */}
                        <div style={{
                          width: 32, height: 32, minWidth: 32,
                          borderRadius: '50%',
                          background: idx < path.current_step ? '#27ae60' : idx === path.current_step ? 'var(--primary)' : 'var(--border)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          color: idx <= path.current_step ? '#fff' : 'var(--text-muted)',
                          fontSize: 13, fontWeight: 700
                        }}>
                          {idx < path.current_step ? <CheckCircle2 size={16} /> : idx + 1}
                        </div>

                        {/* Connector line */}
                        {idx < (path.courses || []).length - 1 && (
                          <div style={{
                            position: 'absolute', left: 15, top: 32, width: 2, height: 10,
                            background: idx < path.current_step ? '#27ae60' : 'var(--border)'
                          }} />
                        )}

                        {/* Course Card */}
                        <div style={{
                          flex: 1, padding: '12px 16px',
                          border: `1px solid ${idx === path.current_step ? 'var(--primary)' : 'var(--border)'}`,
                          borderRadius: 8,
                          background: idx === path.current_step ? 'var(--primary-light)' :
                                      idx < path.current_step ? '#f0fdf4' : 'var(--surface)'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                              <div style={{ fontWeight: 600, fontSize: 14 }}>{course.title}</div>
                              <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 12, marginTop: 2 }}>
                                <span style={{ color: DIFF_COLORS[course.difficulty] || '#64748b', fontWeight: 600 }}>
                                  {course.difficulty}
                                </span>
                                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                  <Clock size={11} /> {course.duration_hours}h
                                </span>
                                <span><BookOpen size={11} style={{ display: 'inline', marginRight: 2 }} />{course.course_type}</span>
                              </div>
                            </div>
                            <div style={{ display: 'flex', gap: 6 }}>
                              {idx < path.current_step ? (
                                <span className="badge badge-proficient">Completed</span>
                              ) : idx === path.current_step ? (
                                <button
                                  className="btn btn-primary btn-sm"
                                  onClick={() => updateProgress(course.id, 100)}
                                >
                                  <Play size={12} /> Mark Complete
                                </button>
                              ) : (
                                <span className="badge" style={{ background: 'var(--bg)', color: 'var(--text-muted)' }}>Locked</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

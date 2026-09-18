import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import toast from 'react-hot-toast';
import { BookOpen, Clock, Star, ExternalLink, TrendingUp, Play } from 'lucide-react';

const DIFF_COLORS = { beginner: '#059669', intermediate: '#d97706', advanced: '#dc2626' };
const GAP_COLORS = { critical: '#e74c3c', moderate: '#e67e22', minor: '#f39c12', proficient: '#27ae60' };

export default function Recommendations() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(null);

  useEffect(() => {
    api.get('/recommendations/').then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const enroll = async (courseId, title) => {
    setEnrolling(courseId);
    try {
      await api.post('/igot/enroll', { course_id: courseId });
      toast.success(`Enrolled in "${title}"`);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Enrollment failed');
    } finally {
      setEnrolling(null);
    }
  };

  if (loading) return <div className="spinner" />;

  const recs = data?.recommendations || [];

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Personalized Recommendations</h1>
          <p>AI-curated courses based on your competency gaps</p>
        </div>
      </div>

      <div className="page-content">
        {recs.length === 0 ? (
          <div className="card card-body" style={{ textAlign: 'center', padding: '60px 20px' }}>
            <TrendingUp size={48} style={{ marginBottom: 12, opacity: 0.3 }} />
            <h3>No Recommendations Yet</h3>
            <p style={{ color: 'var(--text-muted)', marginTop: 8, marginBottom: 20 }}>
              {data?.message || 'Take an assessment to get personalized course recommendations.'}
            </p>
            <a href="/assessment" className="btn btn-primary">Take Assessment</a>
          </div>
        ) : (
          <>
            {data?.top_gap && (
              <div className="card card-body" style={{ marginBottom: 20, borderLeft: `4px solid ${GAP_COLORS[data.top_gap.gap_level]}`, background: 'var(--primary-light)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <TrendingUp size={18} color="var(--primary)" />
                  <div>
                    <strong>Priority Focus:</strong> {data.top_gap.competency_name} ({data.top_gap.score.toFixed(1)}%)
                    — {data.gap_count} gap{data.gap_count !== 1 ? 's' : ''} identified. Showing {recs.length} recommended courses.
                  </div>
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
              {recs.map((course, i) => (
                <div key={course.id} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
                  <div style={{ height: 6, borderRadius: '12px 12px 0 0', background: DIFF_COLORS[course.difficulty] || '#94a3b8' }} />
                  <div className="card-body" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <span className={`badge badge-${course.difficulty}`}>{course.difficulty}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
                        <Star size={12} fill="currentColor" />
                        <span>{Math.round(course.recommendation_score * 100)}% match</span>
                      </div>
                    </div>

                    <h3 style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.4 }}>{course.title}</h3>
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', flex: 1 }}>{course.description}</p>

                    <div style={{ padding: '8px 12px', background: 'var(--bg)', borderRadius: 6, fontSize: 12, color: 'var(--primary)', borderLeft: '2px solid var(--primary)' }}>
                      💡 {course.reason}
                    </div>

                    <div style={{ display: 'flex', gap: 12, fontSize: 13, color: 'var(--text-muted)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Clock size={13} /> {course.duration_hours}h
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <BookOpen size={13} /> {course.course_type}
                      </span>
                      {course.igot_course_id && (
                        <span style={{ fontSize: 11, background: '#eff6ff', color: '#1a56db', padding: '2px 6px', borderRadius: 4, fontWeight: 600 }}>
                          iGOT
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      <button
                        className="btn btn-primary btn-sm"
                        style={{ flex: 1 }}
                        disabled={enrolling === course.id}
                        onClick={() => enroll(course.id, course.title)}
                      >
                        <Play size={13} />
                        {enrolling === course.id ? 'Enrolling...' : 'Enroll & Start'}
                      </button>
                      {course.igot_course_id && (
                        <a
                          href={`https://igotkarmayogi.gov.in/course/${course.igot_course_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-secondary btn-sm"
                        >
                          <ExternalLink size={13} />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  );
}

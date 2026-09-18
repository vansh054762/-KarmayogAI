import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import toast from 'react-hot-toast';
import { Globe, BookOpen, Award, ExternalLink, Play, CheckCircle2 } from 'lucide-react';

export default function IGOTIntegration() {
  const [profile, setProfile] = useState(null);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get('/igot/profile'),
      api.get('/igot/courses')
    ]).then(([profRes, coursesRes]) => {
      setProfile(profRes.data);
      setCourses(coursesRes.data.courses);
      setLoading(false);
    }).catch(() => setLoading(false));
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

  return (
    <>
      <div className="topbar">
        <div>
          <h1>iGOT Karmayogi Integration</h1>
          <p>Connected to the Government of India's learning platform</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#27ae60', animation: 'pulse 2s infinite' }} />
          <span style={{ fontSize: 13, color: '#27ae60', fontWeight: 600 }}>Connected (Mock)</span>
        </div>
      </div>

      <div className="page-content">
        {/* iGOT Profile */}
        {profile && (
          <div className="card card-body" style={{
            background: 'linear-gradient(135deg, #0f172a, #1e3a5f)',
            color: '#fff', border: 'none', marginBottom: 24
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 20 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <Globe size={24} color="#3b82f6" />
                  <span style={{ fontSize: 16, fontWeight: 700 }}>iGOT Karmayogi Profile</span>
                </div>
                <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>{profile.name}</div>
                <div style={{ fontSize: 14, color: '#94a3b8' }}>{profile.designation} · {profile.department}</div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>
                  ID: {profile.igot_user_id}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 24 }}>
                {[
                  { label: 'Enrolled', value: profile.total_enrolled },
                  { label: 'Completed', value: profile.total_completed },
                  { label: 'Learning Hours', value: `${profile.learning_hours?.toFixed(1)}h` }
                ].map((s, i) => (
                  <div key={i} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 28, fontWeight: 800 }}>{s.value}</div>
                    <div style={{ fontSize: 12, color: '#94a3b8' }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Badges */}
            <div style={{ display: 'flex', gap: 12, marginTop: 20, flexWrap: 'wrap' }}>
              {profile.badges?.map((badge, i) => (
                <div key={i} style={{
                  padding: '6px 14px',
                  borderRadius: 20,
                  background: badge.earned ? 'rgba(59,130,246,.2)' : 'rgba(255,255,255,.05)',
                  border: `1px solid ${badge.earned ? '#3b82f6' : 'rgba(255,255,255,.1)'}`,
                  display: 'flex', alignItems: 'center', gap: 6,
                  opacity: badge.earned ? 1 : 0.4,
                  fontSize: 13, fontWeight: 500
                }}>
                  <Award size={14} color={badge.earned ? '#3b82f6' : '#94a3b8'} />
                  {badge.name}
                  {badge.earned && <CheckCircle2 size={12} color="#27ae60" />}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Integration Status */}
        <div className="card card-body" style={{ marginBottom: 24, borderLeft: '4px solid #27ae60' }}>
          <h4 style={{ marginBottom: 12 }}>Integration Status</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
            {[
              ['✅', 'Course Catalog', 'Synced from iGOT'],
              ['✅', 'Enrollment', 'Connected to iGOT API'],
              ['✅', 'Progress Sync', 'Real-time updates'],
              ['✅', 'Certificates', 'Available on completion'],
              ['✅', 'Competency Mapping', 'Aligned to iGOT framework'],
              ['⚙️', 'Live iGOT API', 'Mock mode (Prototype)'],
            ].map(([icon, label, desc]) => (
              <div key={label} style={{ display: 'flex', gap: 10, padding: '10px 12px', background: 'var(--bg)', borderRadius: 8 }}>
                <span style={{ fontSize: 18 }}>{icon}</span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{label}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* iGOT Course Catalog */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">iGOT Course Catalog</div>
              <div className="card-subtitle">{courses.length} government-approved courses</div>
            </div>
            <a href="https://igotkarmayogi.gov.in" target="_blank" rel="noreferrer"
              className="btn btn-secondary btn-sm">
              <ExternalLink size={13} /> Visit iGOT Portal
            </a>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
              {courses.map(course => (
                <div key={course.id} className="card" style={{ border: '1px solid var(--border)' }}>
                  <div style={{ height: 4, borderRadius: '12px 12px 0 0', background: { beginner: '#27ae60', intermediate: '#f39c12', advanced: '#e74c3c' }[course.difficulty] || '#94a3b8' }} />
                  <div className="card-body" style={{ padding: '14px 16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span className={`badge badge-${course.difficulty}`}>{course.difficulty}</span>
                      <span style={{ fontSize: 11, background: '#eff6ff', color: '#1a56db', padding: '2px 8px', borderRadius: 20, fontWeight: 700 }}>
                        iGOT
                      </span>
                    </div>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{course.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10, lineHeight: 1.5 }}>
                      {course.description?.slice(0, 80)}...
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 12, marginBottom: 10 }}>
                      <span>{course.duration_hours}h</span>
                      <span>{course.course_type}</span>
                      {course.certificate_available && <span>🎓 Certificate</span>}
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button
                        className="btn btn-primary btn-sm"
                        style={{ flex: 1 }}
                        disabled={enrolling === course.id}
                        onClick={() => enroll(course.id, course.title)}
                      >
                        <Play size={12} /> {enrolling === course.id ? 'Enrolling...' : 'Enroll'}
                      </button>
                      <a
                        href={course.igot_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-secondary btn-sm"
                      >
                        <ExternalLink size={12} />
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </>
  );
}

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import api from '../utils/api';
import { useAuth } from '../context/AuthContext';
import {
  ClipboardList, BookOpen, TrendingUp, Target,
  Award, AlertTriangle, CheckCircle2, ArrowRight,
  LayoutDashboard, Users, Map
} from 'lucide-react';

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/progress/dashboard').then(r => {
      setData(r.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="spinner" />;

  const stats = data?.stats || {};
  const radarData = data?.radar_data || [];
  const trend = data?.score_trend || [];
  const skillLevel = data?.skill_level || { label: 'Beginner', icon: LayoutDashboard, color: '#e74c3c' };
  const compScores = data?.competency_scores || [];

  const statCards = [
    { icon: LayoutDashboard, label: 'Overall Score', value: `${stats.overall_score || 0}%`, bg: '#eff6ff', color: '#1a56db' },
    { icon: Target, label: 'Assessments Taken', value: stats.total_assessments || 0, bg: '#f5f3ff', color: '#7c3aed' },
    { icon: BookOpen, label: 'Courses Enrolled', value: stats.courses_enrolled || 0, bg: '#ecfdf5', color: '#059669' },
    { icon: CheckCircle2, label: 'Courses Completed', value: stats.courses_completed || 0, bg: '#fefce8', color: '#d97706' },
    { icon: Map, label: 'Active Learning Paths', value: stats.active_learning_paths || 0, bg: '#fff1f2', color: '#e11d48' },
    { icon: Award, label: 'Competencies Mapped', value: stats.competencies_assessed || 0, bg: '#f0fdf4', color: '#16a34a' },
  ];

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Welcome back, {user?.name?.split(' ')[0]} 👋</h1>
          <p>Track your competencies and personalized learning journey</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Link to="/assessment" className="btn btn-primary btn-sm">
            <ClipboardList size={15} /> Take Assessment
          </Link>
          <Link to="/quiz-generator" className="btn btn-secondary btn-sm">
            <BookOpen size={15} /> Generate Quiz
          </Link>
        </div>
      </div>

      <div className="page-content">
        {/* Skill Level Banner */}
        <div className="card card-body" style={{ marginBottom: 20, background: `linear-gradient(135deg, #0f172a, #1e3a5f)`, color: '#fff', border: 'none' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 4 }}>Your Current Skill Level</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 32 }}>
                  <skillLevel.icon size={48} strokeWidth={1.5} />
                </span>
                <div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: skillLevel.color }}>{skillLevel.label}</div>
                  <div style={{ fontSize: 13, color: '#94a3b8' }}>
                    Overall score: {stats.overall_score || 0}% across {stats.competencies_assessed || 0} competencies
                  </div>
                </div>
              </div>
            </div>
            {stats.total_assessments === 0 && (
              <Link to="/assessment" className="btn btn-primary">
                Take Your First Assessment <ArrowRight size={15} />
              </Link>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="stats-grid" style={{ marginBottom: 24 }}>
          {statCards.map((s, i) => (
            <div key={i} className="stat-card">
              <div className="stat-icon" style={{ background: s.bg, color: s.color }}>
                <s.icon size={20} strokeWidth={2} />
              </div>
              <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        <div className="grid-2" style={{ marginBottom: 24 }}>
          {/* Radar Chart */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Competency Radar</div>
                <div className="card-subtitle">Your skill profile across all competencies</div>
              </div>
            </div>
            <div className="card-body">
              {radarData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="competency" tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Radar name="Score" dataKey="score" stroke="#1a56db" fill="#1a56db" fillOpacity={0.2} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                  <Target size={40} style={{ marginBottom: 8, opacity: 0.3 }} />
                  <p>Take an assessment to see your radar chart</p>
                </div>
              )}
            </div>
          </div>

          {/* Score Trend */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Score Trend</div>
                <div className="card-subtitle">Your recent assessment performance</div>
              </div>
            </div>
            <div className="card-body">
              {trend.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Tooltip formatter={(v) => [`${v}%`, 'Score']} />
                    <Line type="monotone" dataKey="score" stroke="#1a56db" strokeWidth={2.5} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                  <TrendingUp size={40} style={{ marginBottom: 8, opacity: 0.3 }} />
                  <p>No assessment data yet</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Competency Scores Table */}
        {compScores.length > 0 && (
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <div className="card-title">Competency Scores</div>
              <Link to="/assessment" className="btn btn-sm btn-secondary">Re-assess</Link>
            </div>
            <div className="card-body">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Competency</th>
                      <th>Score</th>
                      <th>Progress</th>
                      <th>Status</th>
                      <th>Last Assessed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compScores.map((c, i) => {
                      const level = c.score >= 85 ? 'proficient' : c.score >= 70 ? 'minor' : c.score >= 50 ? 'moderate' : 'critical';
                      const label = { proficient: 'Proficient', minor: 'Minor Gap', moderate: 'Moderate Gap', critical: 'Critical Gap' }[level];
                      return (
                        <tr key={i}>
                          <td style={{ fontWeight: 500 }}>{c.competency_name}</td>
                          <td style={{ fontWeight: 700 }}>{c.score.toFixed(1)}%</td>
                          <td style={{ width: 160 }}>
                            <div className="progress-bar-wrap" style={{ height: 8 }}>
                              <div className="progress-bar-fill" style={{
                                width: `${c.score}%`,
                                background: level === 'proficient' ? '#27ae60' : level === 'minor' ? '#f39c12' : level === 'moderate' ? '#e67e22' : '#e74c3c'
                              }} />
                            </div>
                          </td>
                          <td><span className={`badge badge-${level}`}>{label}</span></td>
                          <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{new Date(c.taken_at).toLocaleDateString()}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid-3">
          {[
            { icon: <AlertTriangle size={24} color="#e74c3c" />, bg: '#fef2f2', title: 'Identify Gaps', desc: 'Take a comprehensive skill assessment', to: '/assessment', cta: 'Start Assessment' },
            { icon: <BookOpen size={24} color="#1a56db" />, bg: '#eff6ff', title: 'Get Recommendations', desc: 'AI-powered personalized course suggestions', to: '/recommendations', cta: 'View Courses' },
            { icon: <Award size={24} color="#7c3aed" />, bg: '#f5f3ff', title: 'Generate Quiz', desc: 'Upload documents for AI MCQ generation', to: '/quiz-generator', cta: 'Upload & Generate' },
          ].map((a, i) => (
            <div key={i} className="card card-body" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ width: 48, height: 48, borderRadius: 12, background: a.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {a.icon}
              </div>
              <div style={{ fontWeight: 600 }}>{a.title}</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', flex: 1 }}>{a.desc}</div>
              <Link to={a.to} className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start' }}>
                {a.cta} <ArrowRight size={13} />
              </Link>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import api from '../utils/api';
import { TrendingUp, BookOpen, Clock } from 'lucide-react';

const STATUS_COLORS = { completed: '#27ae60', in_progress: '#f39c12', enrolled: '#1a56db', not_started: '#94a3b8' };

export default function Progress() {
  const [progress, setProgress] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/progress/course-progress'),
      api.get('/assessment/history')
    ]).then(([progRes, histRes]) => {
      setProgress(progRes.data.progress);
      setHistory(histRes.data.history);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="spinner" />;

  const statusCounts = progress.reduce((acc, p) => {
    acc[p.status] = (acc[p.status] || 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(statusCounts).map(([status, count]) => ({
    name: status.replace('_', ' '), value: count, color: STATUS_COLORS[status]
  }));

  const histByComp = history.reduce((acc, r) => {
    const name = r.competency_name || 'Unknown';
    if (!acc[name]) acc[name] = [];
    acc[name].push(r.score);
    return acc;
  }, {});

  const avgByComp = Object.entries(histByComp).map(([name, scores]) => ({
    name: name.split(' ').slice(0, 2).join(' '),
    avg: Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
  }));

  const totalHours = progress.filter(p => p.status === 'completed').reduce((acc, p) => acc + (p.duration_hours || 0), 0);

  return (
    <>
      <div className="topbar">
        <div>
          <h1>My Progress</h1>
          <p>Track your learning journey and course completion</p>
        </div>
      </div>

      <div className="page-content">
        {/* Summary Stats */}
        <div className="stats-grid" style={{ marginBottom: 24 }}>
          {[
            { icon: '📚', label: 'Total Enrolled', value: progress.length, color: '#1a56db', bg: '#eff6ff' },
            { icon: '✅', label: 'Completed', value: statusCounts.completed || 0, color: '#27ae60', bg: '#f0fdf4' },
            { icon: '▶️', label: 'In Progress', value: statusCounts.in_progress || 0, color: '#d97706', bg: '#fffbeb' },
            { icon: '⏱️', label: 'Hours Learned', value: `${totalHours.toFixed(1)}h`, color: '#7c3aed', bg: '#f5f3ff' },
          ].map((s, i) => (
            <div key={i} className="stat-card">
              <div className="stat-icon" style={{ background: s.bg }}>{s.icon}</div>
              <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        <div className="grid-2" style={{ marginBottom: 24 }}>
          {/* Pie Chart */}
          <div className="card">
            <div className="card-header"><div className="card-title">Course Status Distribution</div></div>
            <div className="card-body">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                      {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
                  <BookOpen size={36} style={{ opacity: 0.3, marginBottom: 8 }} />
                  <p>No enrolled courses yet</p>
                </div>
              )}
            </div>
          </div>

          {/* Avg Score by Competency */}
          <div className="card">
            <div className="card-header"><div className="card-title">Average Score by Competency</div></div>
            <div className="card-body">
              {avgByComp.length > 0 ? (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={avgByComp} margin={{ left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={v => [`${v}%`, 'Avg Score']} />
                    <Bar dataKey="avg" fill="#1a56db" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
                  <TrendingUp size={36} style={{ opacity: 0.3, marginBottom: 8 }} />
                  <p>Take assessments to see data</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Course Progress Table */}
        {progress.length > 0 && (
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header"><div className="card-title">Course Progress</div></div>
            <div className="card-body">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Course</th>
                      <th>Difficulty</th>
                      <th>Duration</th>
                      <th>Progress</th>
                      <th>Status</th>
                      <th>Started</th>
                    </tr>
                  </thead>
                  <tbody>
                    {progress.map((p, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 500 }}>{p.course_title}</td>
                        <td><span style={{ fontSize: 12, fontWeight: 600, color: { beginner: '#059669', intermediate: '#d97706', advanced: '#dc2626' }[p.difficulty] }}>{p.difficulty}</span></td>
                        <td style={{ color: 'var(--text-muted)' }}><Clock size={12} style={{ marginRight: 4 }} />{p.duration_hours}h</td>
                        <td style={{ width: 140 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div className="progress-bar-wrap" style={{ height: 6, flex: 1 }}>
                              <div className="progress-bar-fill" style={{
                                width: `${p.progress_pct}%`,
                                background: STATUS_COLORS[p.status]
                              }} />
                            </div>
                            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{p.progress_pct?.toFixed(0)}%</span>
                          </div>
                        </td>
                        <td>
                          <span className="badge" style={{
                            background: STATUS_COLORS[p.status] + '20',
                            color: STATUS_COLORS[p.status]
                          }}>
                            {p.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                          {p.started_at ? new Date(p.started_at).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Assessment History */}
        {history.length > 0 && (
          <div className="card">
            <div className="card-header"><div className="card-title">Assessment History</div></div>
            <div className="card-body">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Competency</th>
                      <th>Score</th>
                      <th>Correct</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.slice(0, 20).map((r, i) => {
                      const level = r.score >= 85 ? 'proficient' : r.score >= 70 ? 'minor' : r.score >= 50 ? 'moderate' : 'critical';
                      return (
                        <tr key={i}>
                          <td style={{ fontWeight: 500 }}>{r.competency_name}</td>
                          <td><span className={`badge badge-${level}`}>{r.score.toFixed(1)}%</span></td>
                          <td style={{ color: 'var(--text-muted)' }}>{r.correct_answers}/{r.total_questions}</td>
                          <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{new Date(r.taken_at).toLocaleString()}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

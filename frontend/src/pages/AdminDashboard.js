import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../utils/api';
import { Users, TrendingUp, AlertTriangle, Award } from 'lucide-react';

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get('/admin/stats'), api.get('/admin/users')])
      .then(([statsRes, usersRes]) => {
        setData(statsRes.data);
        setUsers(usersRes.data.users);
        setLoading(false);
      }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="spinner" />;

  const stats = data?.platform_stats || {};
  const compAnalytics = data?.competency_analytics || [];

  return (
    <>
      <div className="topbar">
        <div><h1>Admin Dashboard</h1><p>Platform-wide analytics and user management</p></div>
      </div>

      <div className="page-content">
        {/* Stats */}
        <div className="stats-grid" style={{ marginBottom: 24 }}>
          {[
            { icon: <Users size={22} />, label: 'Total Users', value: stats.total_users || 0, color: '#1a56db', bg: '#eff6ff' },
            { icon: <TrendingUp size={22} />, label: 'Total Assessments', value: stats.total_assessments || 0, color: '#7c3aed', bg: '#f5f3ff' },
            { icon: <Award size={22} />, label: 'Completions', value: stats.total_completions || 0, color: '#059669', bg: '#ecfdf5' },
            { icon: <AlertTriangle size={22} />, label: 'Active Users (7d)', value: stats.active_users_7d || 0, color: '#d97706', bg: '#fffbeb' },
          ].map((s, i) => (
            <div key={i} className="stat-card">
              <div className="stat-icon" style={{ background: s.bg, color: s.color }}>{s.icon}</div>
              <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        <div className="grid-2" style={{ marginBottom: 24 }}>
          {/* Competency Analytics Chart */}
          <div className="card">
            <div className="card-header"><div className="card-title">Average Score by Competency</div></div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={compAnalytics} margin={{ left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="competency" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={v => [`${v}%`, 'Avg Score']} />
                  <Bar dataKey="avg_score" fill="#1a56db" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Weakest & Strongest */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card">
              <div className="card-header"><div className="card-title" style={{ color: '#e74c3c' }}>⚠️ Weakest Competencies (Platform-wide)</div></div>
              <div className="card-body">
                {(data?.weakest_competencies || []).map((c, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{c.competency}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{c.assessments_taken} assessments · {c.users_assessed} users</div>
                    </div>
                    <span className="badge badge-critical">{c.avg_score}%</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card">
              <div className="card-header"><div className="card-title" style={{ color: '#27ae60' }}>✅ Strongest Competencies</div></div>
              <div className="card-body">
                {(data?.strongest_competencies || []).map((c, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{c.competency}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{c.users_assessed} users assessed</div>
                    </div>
                    <span className="badge badge-proficient">{c.avg_score}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Users Table */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">All Users</div>
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{users.length} users</span>
          </div>
          <div className="card-body">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Department</th>
                    <th>Avg Score</th>
                    <th>Assessments</th>
                    <th>Completions</th>
                    <th>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 500 }}>{u.name}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{u.email}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{u.department || '—'}</td>
                      <td>
                        {u.avg_score !== null
                          ? <span className={`badge badge-${u.avg_score >= 85 ? 'proficient' : u.avg_score >= 70 ? 'minor' : u.avg_score >= 50 ? 'moderate' : 'critical'}`}>
                              {u.avg_score}%
                            </span>
                          : <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>—</span>}
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{u.assessments_taken}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{u.courses_completed}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{new Date(u.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

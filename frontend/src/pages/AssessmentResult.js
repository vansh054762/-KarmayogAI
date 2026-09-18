import React from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts';
import { AlertTriangle, CheckCircle2, TrendingUp, BookOpen, ArrowRight } from 'lucide-react';

const GAP_COLORS = { critical: '#e74c3c', moderate: '#e67e22', minor: '#f39c12', proficient: '#27ae60' };

export default function AssessmentResult() {
  const { state } = useLocation();
  const navigate = useNavigate();

  if (!state) {
    navigate('/assessment');
    return null;
  }

  const { gap_analysis, assessment_results } = state;
  const { gaps, strengths, overall_score, summary, top_priority_gap } = gap_analysis;

  const chartData = assessment_results.map(r => ({
    name: r.competency_name.split(' ').slice(0, 2).join(' '),
    score: r.score,
    fill: GAP_COLORS[r.score >= 85 ? 'proficient' : r.score >= 70 ? 'minor' : r.score >= 50 ? 'moderate' : 'critical']
  }));

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Assessment Results</h1>
          <p>Your competency gap analysis is ready</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Link to="/recommendations" className="btn btn-primary btn-sm">
            <BookOpen size={15} /> View Recommendations
          </Link>
          <Link to="/assessment" className="btn btn-secondary btn-sm">Retake Assessment</Link>
        </div>
      </div>

      <div className="page-content" style={{ maxWidth: 960, margin: '0 auto' }}>
        {/* Summary Banner */}
        <div className="card card-body" style={{
          background: `linear-gradient(135deg, #0f172a, #1e3a5f)`,
          color: '#fff', border: 'none', marginBottom: 24
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 4 }}>Overall Score</div>
              <div style={{ fontSize: 48, fontWeight: 800, lineHeight: 1 }}>{overall_score.toFixed(1)}%</div>
              <div style={{ fontSize: 14, color: '#94a3b8', marginTop: 8, maxWidth: 500 }}>{summary}</div>
            </div>
            <div style={{ display: 'flex', gap: 24 }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: '#e74c3c' }}>{gaps.filter(g => g.gap_level === 'critical').length}</div>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>Critical Gaps</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: '#e67e22' }}>{gaps.filter(g => g.gap_level === 'moderate').length}</div>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>Moderate Gaps</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: '#27ae60' }}>{strengths.length}</div>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>Strengths</div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: 24 }}>
          {/* Score Chart */}
          <div className="card">
            <div className="card-header"><div className="card-title">Score by Competency</div></div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData} margin={{ left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={v => [`${v.toFixed(1)}%`, 'Score']} />
                  <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Priority Gap */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Priority Focus Area</div>
            </div>
            <div className="card-body">
              {top_priority_gap ? (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <AlertTriangle size={24} color={GAP_COLORS[top_priority_gap.gap_level]} />
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 18 }}>{top_priority_gap.competency_name}</div>
                      <span className={`badge badge-${top_priority_gap.gap_level}`}>{top_priority_gap.label}</span>
                    </div>
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 800, marginBottom: 8, color: GAP_COLORS[top_priority_gap.gap_level] }}>
                    {top_priority_gap.score.toFixed(1)}%
                  </div>
                  <div className="progress-bar-wrap" style={{ height: 10, marginBottom: 16 }}>
                    <div className="progress-bar-fill" style={{ width: `${top_priority_gap.score}%`, background: GAP_COLORS[top_priority_gap.gap_level] }} />
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>Improvement suggestions:</div>
                  <ul style={{ paddingLeft: 18 }}>
                    {(top_priority_gap.suggestions || []).slice(0, 3).map((s, i) => (
                      <li key={i} style={{ fontSize: 14, color: 'var(--text)', marginBottom: 6 }}>{s}</li>
                    ))}
                  </ul>
                  <Link to="/recommendations" className="btn btn-primary btn-sm" style={{ marginTop: 12 }}>
                    Get Course Recommendations <ArrowRight size={14} />
                  </Link>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                  <CheckCircle2 size={40} color="#27ae60" style={{ marginBottom: 8 }} />
                  <div style={{ fontWeight: 600, color: '#27ae60' }}>No Gaps Detected!</div>
                  <p style={{ fontSize: 13, marginTop: 4 }}>You are proficient in all assessed areas.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* All Gaps */}
        {gaps.length > 0 && (
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <div className="card-title">All Competency Gaps</div>
              <Link to="/learning-paths" className="btn btn-sm btn-secondary">
                <TrendingUp size={14} /> View Learning Paths
              </Link>
            </div>
            <div className="card-body">
              {gaps.map((gap, i) => (
                <div key={i} className="gap-card" style={{ borderLeftColor: GAP_COLORS[gap.gap_level] }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 15 }}>{gap.competency_name}</div>
                      <span className={`badge badge-${gap.gap_level}`} style={{ marginTop: 4 }}>{gap.label}</span>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 28, fontWeight: 800, color: GAP_COLORS[gap.gap_level] }}>
                        {gap.score.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <div className="progress-bar-wrap" style={{ height: 6, marginTop: 12 }}>
                    <div className="progress-bar-fill" style={{ width: `${gap.score}%`, background: GAP_COLORS[gap.gap_level] }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Strengths */}
        {strengths.length > 0 && (
          <div className="card">
            <div className="card-header"><div className="card-title">Your Strengths ✨</div></div>
            <div className="card-body">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                {strengths.map((s, i) => (
                  <div key={i} style={{
                    padding: '10px 16px', borderRadius: 8,
                    background: '#f0fdf4', border: '1px solid #bbf7d0',
                    display: 'flex', alignItems: 'center', gap: 8
                  }}>
                    <CheckCircle2 size={16} color="#27ae60" />
                    <span style={{ fontWeight: 500 }}>{s.competency_name}</span>
                    <span style={{ fontWeight: 700, color: '#27ae60' }}>{s.score.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

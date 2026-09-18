import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard, ClipboardList, BookOpen, BrainCircuit,
  Upload, TrendingUp, Map, Globe, ShieldCheck, LogOut, GraduationCap
} from 'lucide-react';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/assessment', icon: ClipboardList, label: 'Skill Assessment' },
  { to: '/recommendations', icon: BookOpen, label: 'Recommendations' },
  { to: '/learning-paths', icon: Map, label: 'Learning Paths' },
  { to: '/quiz-generator', icon: Upload, label: 'AI Quiz Generator' },
  { to: '/progress', icon: TrendingUp, label: 'My Progress' },
  { to: '/igot', icon: Globe, label: 'iGOT Integration' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <GraduationCap size={28} color="#3b82f6" />
          <div>
            <h2>KarmayogAI</h2>
            <span>Adaptive Learning Platform</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-label">Main Menu</div>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}

          {user?.role === 'admin' && (
            <>
              <div className="nav-section-label" style={{ marginTop: 8 }}>Admin</div>
              <NavLink
                to="/admin"
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                <ShieldCheck size={18} />
                Admin Dashboard
              </NavLink>
            </>
          )}
        </nav>

        <div style={{ padding: '16px 20px', borderTop: '1px solid rgba(255,255,255,.07)' }}>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>{user?.name}</div>
            <div style={{ fontSize: 12, color: '#64748b' }}>{user?.designation || user?.role}</div>
          </div>
          <button
            onClick={handleLogout}
            className="nav-item"
            style={{ width: '100%', border: 'none', background: 'none', color: '#94a3b8' }}
          >
            <LogOut size={18} />
            Sign Out
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';
import { GraduationCap } from 'lucide-react';

export default function Register() {
  const [form, setForm] = useState({
    name: '', email: '', password: '', department: '', designation: '', role: 'employee'
  });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.password.length < 6) { toast.error('Password must be at least 6 characters'); return; }
    setLoading(true);
    try {
      await register(form);
      toast.success('Account created! Welcome to KarmayogAI.');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  return (
    <div className="auth-container">
      <div className="auth-card" style={{ maxWidth: 500 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <GraduationCap size={40} color="#1a56db" style={{ marginBottom: 10 }} />
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Create Account</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Join KarmayogAI Learning Platform</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Full Name *</label>
              <input className="form-input" placeholder="Rajesh Kumar" value={form.name} onChange={set('name')} required />
            </div>
            <div className="form-group">
              <label className="form-label">Email *</label>
              <input className="form-input" type="email" placeholder="rajesh@gov.in" value={form.email} onChange={set('email')} required />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Password *</label>
            <input className="form-input" type="password" placeholder="Min 6 characters" value={form.password} onChange={set('password')} required />
          </div>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Department</label>
              <input className="form-input" placeholder="Ministry of Finance" value={form.department} onChange={set('department')} />
            </div>
            <div className="form-group">
              <label className="form-label">Designation</label>
              <input className="form-input" placeholder="Section Officer" value={form.designation} onChange={set('designation')} />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Role</label>
            <select className="form-input form-select" value={form.role} onChange={set('role')}>
              <option value="employee">Employee</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button type="submit" className="btn btn-primary btn-block btn-lg" disabled={loading}>
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: 16, fontSize: 14, color: 'var(--text-muted)' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--primary)', fontWeight: 600 }}>Sign In</Link>
        </p>
      </div>
    </div>
  );
}

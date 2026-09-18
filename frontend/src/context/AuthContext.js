import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../utils/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('karmayog_token'));
  const [loading, setLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    try {
      const res = await api.get('/auth/profile');
      setUser(res.data);
    } catch {
      localStorage.removeItem('karmayog_token');
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { loadProfile(); }, [loadProfile]);

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    const { token: t, user: u } = res.data;
    localStorage.setItem('karmayog_token', t);
    setToken(t);
    setUser(u);
    return u;
  };

  const register = async (data) => {
    const res = await api.post('/auth/register', data);
    const { token: t, user: u } = res.data;
    localStorage.setItem('karmayog_token', t);
    setToken(t);
    setUser(u);
    return u;
  };

  const logout = () => {
    localStorage.removeItem('karmayog_token');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    const res = await api.get('/auth/profile');
    setUser(res.data);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

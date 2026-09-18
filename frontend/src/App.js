import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Assessment from './pages/Assessment';
import AssessmentResult from './pages/AssessmentResult';
import Recommendations from './pages/Recommendations';
import QuizGenerator from './pages/QuizGenerator';
import GeneratedQuizTake from './pages/GeneratedQuizTake';
import Progress from './pages/Progress';
import LearningPaths from './pages/LearningPaths';
import IGOTIntegration from './pages/IGOTIntegration';
import AdminDashboard from './pages/AdminDashboard';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="spinner" />;
  return user ? children : <Navigate to="/login" replace />;
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="spinner" />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />;
  return children;
}

function PublicRoute({ children }) {
  const { user } = useAuth();
  return user ? <Navigate to="/dashboard" replace /> : children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" toastOptions={{ duration: 3500 }} />
        <Routes>
          <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
          <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/assessment" element={<Assessment />} />
            <Route path="/assessment/result" element={<AssessmentResult />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/learning-paths" element={<LearningPaths />} />
            <Route path="/quiz-generator" element={<QuizGenerator />} />
            <Route path="/quiz/:quizId" element={<GeneratedQuizTake />} />
            <Route path="/progress" element={<Progress />} />
            <Route path="/igot" element={<IGOTIntegration />} />
            <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

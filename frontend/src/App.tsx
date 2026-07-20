import React, { useState } from 'react';
import axios from 'axios';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { clearSession, getSession, portalPath, saveSession, Session } from './auth';
import Dashboard from './pages/Dashboard';
import ReviewPage from './pages/ReviewPage';
import HistoryPage from './pages/HistoryPage';
import SearchPage from './pages/SearchPage';
import PatientPage from './pages/PatientPage';

const API = process.env.REACT_APP_API_URL || 'http://localhost:9000';

function Login({ onLogin }: { onLogin: (session: Session) => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true); setError('');
    try {
      const response = await axios.post(`${API}/auth/login`, { username, password });
      const session = saveSession(response.data.access_token);
      if (!session) throw new Error('Invalid access token');
      onLogin(session);
    } catch {
      setError('Invalid username or password.');
    } finally { setLoading(false); }
  };

  return <div className="login-page"><div className="login-card">
    <div className="login-logo">🏥</div><h1>MED AI</h1><p className="login-subtitle">Secure medical document portal</p>
    <form onSubmit={submit}>
      <div className="form-group"><label>Username</label><input value={username} onChange={e => setUsername(e.target.value)} autoFocus required /></div>
      <div className="form-group"><label>Password</label><input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></div>
      {error && <div className="login-error">{error}</div>}
      <button className="login-btn" disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</button>
    </form>
  </div></div>;
}

function ProtectedRoute({ session, roles, children }: { session: Session | null; roles: Session['role'][]; children: React.ReactElement }) {
  const location = useLocation();
  if (!session) return <Navigate to="/login" replace state={{ from: location }} />;
  return roles.includes(session.role) ? children : <Navigate to={portalPath(session.role)} replace />;
}

function AppRoutes() {
  const [session, setSession] = useState<Session | null>(() => getSession());
  const navigate = useNavigate();
  const logout = () => { clearSession(); setSession(null); navigate('/login', { replace: true }); };
  const signIn = (nextSession: Session) => { setSession(nextSession); navigate(portalPath(nextSession.role), { replace: true }); };
  const reviewerRoles: Session['role'][] = ['admin', 'reviewer'];

  return <Routes>
    <Route path="/login" element={session ? <Navigate to={portalPath(session.role)} replace /> : <Login onLogin={signIn} />} />
    <Route path="/dashboard" element={<ProtectedRoute session={session} roles={reviewerRoles}><Dashboard session={session!} onLogout={logout} /></ProtectedRoute>} />
    <Route path="/review/:id" element={<ProtectedRoute session={session} roles={reviewerRoles}><ReviewPage session={session!} /></ProtectedRoute>} />
    <Route path="/history" element={<ProtectedRoute session={session} roles={reviewerRoles}><HistoryPage session={session!} /></ProtectedRoute>} />
    <Route path="/search" element={<ProtectedRoute session={session} roles={['doctor']}><SearchPage session={session!} onLogout={logout} /></ProtectedRoute>} />
    <Route path="/patient/:id" element={<ProtectedRoute session={session} roles={['doctor']}><PatientPage session={session!} /></ProtectedRoute>} />
    <Route path="/" element={<Navigate to={session ? portalPath(session.role) : '/login'} replace />} />
    <Route path="*" element={<Navigate to={session ? portalPath(session.role) : '/login'} replace />} />
  </Routes>;
}

export default function App() { return <BrowserRouter><AppRoutes /></BrowserRouter>; }

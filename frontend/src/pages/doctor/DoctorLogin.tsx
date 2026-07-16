import React, { useState } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_API_URL || 'http://localhost:9000';

interface Props {
  onLogin: (token: string, name: string, username: string) => void;
}

export default function DoctorLogin({ onLogin }: Props) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await axios.post(`${API}/auth/login`, { username, password });
      if (res.data.role !== 'doctor' && res.data.role !== 'admin') {
        setError('Access denied: doctor accounts only');
        return;
      }
      sessionStorage.setItem('doctor_token', res.data.access_token);
      sessionStorage.setItem('doctor_name', res.data.username);
      onLogin(res.data.access_token, res.data.username, res.data.username);
    } catch {
      setError('Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">🏥</div>
        <h1>MED AI</h1>
        <p className="login-subtitle">Doctor Patient Portal</p>
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => { setUsername(e.target.value); setError(''); }}
              placeholder="Enter your username"
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => { setPassword(e.target.value); setError(''); }}
              placeholder="Enter your password"
            />
          </div>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <div className="login-hint">
          <p>Doctor accounts:</p>
          <p>• dr.smith / medai2025</p>
          <p>• dr.jones / jones2025</p>
          <p>• dr.patel / patel2025</p>
          <p>• dr.chen / chen2025</p>
          <p>• dr.williams / williams2025</p>
        </div>
      </div>
    </div>
  );
}

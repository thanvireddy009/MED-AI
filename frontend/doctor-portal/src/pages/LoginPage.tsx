import React, { useState } from 'react';

const CREDENTIALS = [
  { username: 'dr.smith', password: 'medai2025', name: 'Dr. John Smith' },
  { username: 'dr.jones', password: 'jones2025', name: 'Dr. Sarah Jones' },
  { username: 'dr.patel', password: 'patel2025', name: 'Dr. Raj Patel' },
  { username: 'dr.chen', password: 'chen2025', name: 'Dr. Linda Chen' },
  { username: 'dr.williams', password: 'williams2025', name: 'Dr. Marcus Williams' },
];

export default function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    const valid = CREDENTIALS.find(c => c.username === username && c.password === password);
    if (valid) {
      sessionStorage.setItem('doctor_auth', valid.username);
      sessionStorage.setItem('doctor_name', valid.name);
      onLogin();
    } else {
      setError('Invalid username or password');
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
          <button type="submit" className="login-btn">Sign In</button>
        </form>
        <div className="login-hint">
          <p>Available accounts:</p>
          <p>• Dr. John Smith — dr.smith / medai2025</p>
          <p>• Dr. Sarah Jones — dr.jones / jones2025</p>
          <p>• Dr. Raj Patel — dr.patel / patel2025</p>
          <p>• Dr. Linda Chen — dr.chen / chen2025</p>
          <p>• Dr. Marcus Williams — dr.williams / williams2025</p>
        </div>
      </div>
    </div>
  );
}

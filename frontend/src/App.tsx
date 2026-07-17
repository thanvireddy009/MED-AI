import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import axios from 'axios';
import Dashboard from './pages/Dashboard';
import ReviewPage from './pages/ReviewPage';
import HistoryPage from './pages/HistoryPage';
import './App.css';

const API = process.env.REACT_APP_API_URL || 'http://localhost:9000';

// Auto-login with reviewer credentials — no login page needed
async function ensureToken() {
  if (localStorage.getItem('token')) return;
  try {
    const res = await axios.post(`${API}/auth/login`, {
      username: 'reviewer',
      password: 'review2025',
    });
    localStorage.setItem('token', res.data.access_token);
  } catch (e) {
    console.error('Auto-login failed', e);
  }
}

function App() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    ensureToken().then(() => setReady(true));
  }, []);

  if (!ready) return <div className="loading">Loading...</div>;

  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-brand">🏥 MED AI Review</div>
          <div className="nav-links">
            <Link to="/">Dashboard</Link>
            <Link to="/history">Review History</Link>
          </div>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/review/:id" element={<ReviewPage />} />
            <Route path="/history" element={<HistoryPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

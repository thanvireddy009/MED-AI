import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ReviewPage from './pages/ReviewPage';
import HistoryPage from './pages/HistoryPage';
import ReviewerLogin from './pages/ReviewerLogin';
import './App.css';

function App() {
  const [loggedIn, setLoggedIn] = useState(!!localStorage.getItem('token'));

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    setLoggedIn(false);
  };

  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-brand">🏥 MED AI Review</div>
          {loggedIn && (
            <div className="nav-links">
              <Link to="/">Dashboard</Link>
              <Link to="/history">Review History</Link>
              <span
                style={{ color: '#94a3b8', cursor: 'pointer', marginLeft: '1.5rem', fontSize: '0.85rem' }}
                onClick={handleLogout}
              >
                Sign Out ({localStorage.getItem('username')})
              </span>
            </div>
          )}
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={
              loggedIn
                ? <Dashboard />
                : <ReviewerLogin onLogin={() => setLoggedIn(true)} />
            } />
            <Route path="/review/:id" element={loggedIn ? <ReviewPage /> : <Navigate to="/" />} />
            <Route path="/history" element={loggedIn ? <HistoryPage /> : <Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

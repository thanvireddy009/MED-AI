import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ReviewPage from './pages/ReviewPage';
import HistoryPage from './pages/HistoryPage';
import ReviewerLogin from './pages/ReviewerLogin';
import DoctorLogin from './pages/doctor/DoctorLogin';
import DoctorSearch from './pages/doctor/DoctorSearch';
import DoctorPatient from './pages/doctor/DoctorPatient';
import './App.css';

function App() {
  const [reviewerLoggedIn, setReviewerLoggedIn] = useState(!!localStorage.getItem('token'));
  const [doctorLoggedIn, setDoctorLoggedIn] = useState(!!sessionStorage.getItem('doctor_token'));

  const handleDoctorLogin = () => setDoctorLoggedIn(true);

  const handleDoctorLogout = () => {
    sessionStorage.removeItem('doctor_token');
    sessionStorage.removeItem('doctor_name');
    setDoctorLoggedIn(false);
  };

  const handleReviewerLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    setReviewerLoggedIn(false);
  };

  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-brand">🏥 MED AI</div>
          <div className="nav-links">
            {reviewerLoggedIn && (
              <>
                <Link to="/">Dashboard</Link>
                <Link to="/history">Review History</Link>
                <span
                  style={{ color: '#94a3b8', cursor: 'pointer', marginLeft: '1.5rem', fontSize: '0.85rem' }}
                  onClick={handleReviewerLogout}
                >
                  Sign Out ({localStorage.getItem('username')})
                </span>
              </>
            )}
            <Link to="/doctor" style={{ marginLeft: '1.5rem' }}>Doctor Portal</Link>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            {/* Reviewer routes */}
            <Route path="/" element={
              reviewerLoggedIn
                ? <Dashboard />
                : <ReviewerLogin onLogin={() => setReviewerLoggedIn(true)} />
            } />
            <Route path="/review/:id" element={
              reviewerLoggedIn ? <ReviewPage /> : <Navigate to="/" />
            } />
            <Route path="/history" element={
              reviewerLoggedIn ? <HistoryPage /> : <Navigate to="/" />
            } />

            {/* Doctor portal routes */}
            <Route path="/doctor" element={
              doctorLoggedIn
                ? <DoctorSearch onLogout={handleDoctorLogout} />
                : <DoctorLogin onLogin={handleDoctorLogin} />
            } />
            <Route path="/doctor/patient/:id" element={
              doctorLoggedIn ? <DoctorPatient /> : <Navigate to="/doctor" />
            } />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

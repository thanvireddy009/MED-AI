import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import SearchPage from './pages/SearchPage';
import PatientPage from './pages/PatientPage';
import './App.css';

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!sessionStorage.getItem('doctor_token'));

  const handleLogin = () => setLoggedIn(true);

  const handleLogout = () => {
    sessionStorage.removeItem('doctor_token');
    sessionStorage.removeItem('doctor_name');
    setLoggedIn(false);
  };

  return (
    <Router>
      <Routes>
        <Route path="/" element={
          loggedIn
            ? <SearchPage onLogout={handleLogout} />
            : <LoginPage onLogin={handleLogin} />
        } />
        <Route path="/patient/:id" element={
          loggedIn ? <PatientPage /> : <Navigate to="/" />
        } />
      </Routes>
    </Router>
  );
}

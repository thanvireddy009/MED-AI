import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import SearchPage from './pages/SearchPage';
import PatientPage from './pages/PatientPage';
import './App.css';

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!sessionStorage.getItem('doctor_auth'));

  return (
    <Router>
      <Routes>
        <Route path="/login" element={
          loggedIn ? <Navigate to="/" /> : <LoginPage onLogin={() => setLoggedIn(true)} />
        } />
        <Route path="/" element={
          loggedIn
            ? <SearchPage onLogout={() => { sessionStorage.clear(); setLoggedIn(false); }} />
            : <Navigate to="/login" />
        } />
        <Route path="/patient/:id" element={
          loggedIn ? <PatientPage /> : <Navigate to="/login" />
        } />
      </Routes>
    </Router>
  );
}

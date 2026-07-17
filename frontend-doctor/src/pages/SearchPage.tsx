import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API = process.env.REACT_APP_API_URL || 'http://localhost:9000';

export default function SearchPage({ onLogout }: { onLogout: () => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const navigate = useNavigate();
  const doctorName = sessionStorage.getItem('doctor_name') || '';
  const token = sessionStorage.getItem('doctor_token') || '';

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API}/api/documents/search`, {
        params: { query },
        headers: { Authorization: `Bearer ${token}` },
      });
      setResults(res.data);
      setSearched(true);
    } catch {
      alert('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="portal-layout">
      <nav className="portal-nav">
        <div className="nav-brand">🏥 MED AI — Doctor Portal</div>
        <div className="nav-right">
          <span className="doctor-name">👤 {doctorName}</span>
          <button className="logout-btn" onClick={onLogout}>Sign Out</button>
        </div>
      </nav>
      <div className="portal-content">
        <div className="search-hero">
          <h1>Patient Record Search</h1>
          <p>Search approved medical reports by patient name or patient ID</p>
          <div className="search-bar">
            <input
              type="text"
              placeholder="Patient name or ID (e.g. PT-2025-001, Susan Clarke)"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              className="search-input"
            />
            <button onClick={handleSearch} disabled={loading} className="search-btn">
              {loading ? 'Searching...' : '🔍 Search'}
            </button>
          </div>
        </div>
        {searched && (
          <div className="results-section">
            {results.length === 0 ? (
              <div className="no-results">
                <p>No approved reports found for "<strong>{query}</strong>"</p>
                <small>Only approved documents are accessible.</small>
              </div>
            ) : (
              <>
                <p className="results-count">{results.length} approved report(s) found</p>
                <div className="results-grid">
                  {results.map(doc => {
                    const pi = (doc.validated_data || doc.extracted_data)?.patient_information || {};
                    return (
                      <div className="result-card" key={doc.id} onClick={() => navigate(`/patient/${doc.id}`)}>
                        <div className="card-header">
                          <span className="patient-name">{pi.full_name || 'Unknown Patient'}</span>
                          <span className="patient-id">{pi.patient_identifier || '—'}</span>
                        </div>
                        <div className="card-details">
                          <div><span>Date of Birth</span><strong>{pi.date_of_birth || '—'}</strong></div>
                          <div><span>Sex</span><strong>{pi.sex || '—'}</strong></div>
                          <div><span>Age</span><strong>{pi.age || '—'}</strong></div>
                          <div><span>Weight</span><strong>{pi.weight || '—'}</strong></div>
                        </div>
                        <div className="card-footer">
                          <span>📄 {doc.file_name}</span>
                          <span className="view-link">View Full Report →</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

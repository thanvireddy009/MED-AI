import React, { useState } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function DoctorPortal() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSelected(null);
    try {
      const res = await axios.get(`${API}/api/documents/search`, { params: { query } });
      setResults(res.data);
      setSearched(true);
    } catch (err) {
      alert('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const getPatientData = (doc: any) => doc.validated_data || doc.extracted_data || {};

  const sections = [
    { key: 'patient_information', label: 'Patient Information' },
    { key: 'adverse_events', label: 'Adverse Events' },
    { key: 'suspect_drug', label: 'Suspect Drug' },
    { key: 'medical_history', label: 'Medical History' },
    { key: 'laboratory_tests', label: 'Laboratory Tests' },
    { key: 'reporter_information', label: 'Reporter Information' },
  ];

  return (
    <div className="doctor-portal">
      <h1>Doctor Patient Portal</h1>
      <p className="portal-subtitle">Search approved reports by patient name or patient ID</p>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Enter patient name or patient ID (e.g. PT-2025-001)"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          className="search-input"
        />
        <button onClick={handleSearch} disabled={loading} className="search-btn">
          {loading ? 'Searching...' : '🔍 Search'}
        </button>
      </div>

      {searched && !selected && (
        <div className="search-results">
          {results.length === 0 ? (
            <div className="no-results">No approved reports found for "{query}"</div>
          ) : (
            <>
              <p className="results-count">{results.length} report(s) found</p>
              {results.map(doc => {
                const pi = getPatientData(doc)?.patient_information || {};
                return (
                  <div className="result-card" key={doc.id} onClick={() => setSelected(doc)}>
                    <div className="result-main">
                      <span className="result-name">{pi.full_name || 'Unknown'}</span>
                      <span className="result-id">{pi.patient_identifier || '—'}</span>
                    </div>
                    <div className="result-meta">
                      <span>DOB: {pi.date_of_birth || '—'}</span>
                      <span>Sex: {pi.sex || '—'}</span>
                      <span>File: {doc.file_name}</span>
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}

      {selected && (
        <div className="patient-record">
          <div className="record-header">
            <button className="back-btn" onClick={() => setSelected(null)}>← Back to results</button>
            <h2>{getPatientData(selected)?.patient_information?.full_name || 'Patient Record'}</h2>
            <span className="approved-badge">✓ Approved</span>
          </div>
          <div className="record-grid">
            {sections.map(({ key, label }) => {
              const sectionData = getPatientData(selected)?.[key];
              if (!sectionData) return null;
              if (Array.isArray(sectionData)) {
                return (
                  <div className="record-section" key={key}>
                    <h3>{label}</h3>
                    {sectionData.map((item: any, i: number) => (
                      <div className="array-item" key={i}>
                        {Object.entries(item).map(([field, value]) => (
                          <div className="record-field" key={field}>
                            <span className="field-label">{field.replace(/_/g, ' ')}</span>
                            <span className="field-value">{String(value || '—')}</span>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                );
              }
              return (
                <div className="record-section" key={key}>
                  <h3>{label}</h3>
                  {Object.entries(sectionData).map(([field, value]) => (
                    <div className="record-field" key={field}>
                      <span className="field-label">{field.replace(/_/g, ' ')}</span>
                      <span className="field-value">{String(value || '—')}</span>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

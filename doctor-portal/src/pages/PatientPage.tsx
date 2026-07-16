import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function PatientPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<any>(null);
  const doctorName = sessionStorage.getItem('doctor_name') || sessionStorage.getItem('doctor_auth');

  useEffect(() => {
    axios.get(`${API}/api/documents/${id}`).then(res => setDoc(res.data));
  }, [id]);

  if (!doc) return <div className="loading">Loading patient record...</div>;

  const data = doc.validated_data || doc.extracted_data || {};

  const sections = [
    { key: 'patient_information', label: '👤 Patient Information' },
    { key: 'adverse_events', label: '⚠️ Adverse Events' },
    { key: 'suspect_drug', label: '💊 Suspect Drug' },
    { key: 'medical_history', label: '📋 Medical History' },
    { key: 'laboratory_tests', label: '🔬 Laboratory Tests' },
    { key: 'reporter_information', label: '👨‍⚕️ Reporter Information' },
  ];

  return (
    <div className="portal-layout">
      <nav className="portal-nav">
        <div className="nav-brand">🏥 MED AI — Doctor Portal</div>
        <div className="nav-right">
          <span className="doctor-name">👤 {doctorName}</span>
          <button className="logout-btn" onClick={() => navigate('/')}>← Back to Search</button>
        </div>
      </nav>

      <div className="portal-content">
        <div className="patient-header">
          <div>
            <h1>{data?.patient_information?.full_name || 'Patient Record'}</h1>
            <p>{data?.patient_information?.patient_identifier} • {doc.file_name}</p>
          </div>
          <span className="approved-tag">✓ Approved Report</span>
        </div>

        <div className="sections-grid">
          {sections.map(({ key, label }) => {
            const sectionData = data[key];
            if (!sectionData) return null;

            if (Array.isArray(sectionData)) {
              if (!sectionData.length || sectionData.every((i: any) => Object.values(i).every(v => !v || v === 'N/A'))) return null;
              return (
                <div className="section-card" key={key}>
                  <h2>{label}</h2>
                  {sectionData.map((item: any, i: number) => (
                    <div className="array-item" key={i}>
                      {Object.entries(item).filter(([, v]) => v && v !== 'N/A').map(([field, value]) => (
                        <div className="field-row" key={field}>
                          <span className="field-label">{field.replace(/_/g, ' ')}</span>
                          <span className="field-value">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              );
            }

            const entries = Object.entries(sectionData).filter(([, v]) => v && v !== 'N/A');
            if (!entries.length) return null;

            return (
              <div className="section-card" key={key}>
                <h2>{label}</h2>
                {entries.map(([field, value]) => (
                  <div className="field-row" key={field}>
                    <span className="field-label">{field.replace(/_/g, ' ')}</span>
                    <span className="field-value">{String(value)}</span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

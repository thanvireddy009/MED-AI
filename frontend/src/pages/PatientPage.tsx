import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate, useParams } from 'react-router-dom';
import { Session } from '../auth';
const API = process.env.REACT_APP_API_URL || 'http://localhost:9000';
const sections = [['patient_information', '👤 Patient Information'], ['adverse_events', '⚠️ Adverse Events'], ['suspect_drug', '💊 Suspect Drug'], ['medical_history', '📋 Medical History'], ['laboratory_tests', '🔬 Laboratory Tests'], ['reporter_information', '👨‍⚕️ Reporter Information']];
export default function PatientPage({ session }: { session: Session }) {
  const { id } = useParams(); const navigate = useNavigate(); const [doc, setDoc] = useState<any>(null);
  useEffect(() => { axios.get(`${API}/api/documents/${id}`, { headers: { Authorization: `Bearer ${session.token}` } }).then(r => setDoc(r.data)).catch(() => navigate('/search', { replace: true })); }, [id, navigate, session.token]);
  if (!doc) return <div className="loading">Loading patient record…</div>;
  const data = doc.validated_data || doc.extracted_data || {};
  const rows = (item: Record<string, unknown>) => Object.entries(item).filter(([, value]) => value && value !== 'N/A').map(([field, value]) => <div className="field-row" key={field}><span className="field-label">{field.replace(/_/g, ' ')}</span><span className="field-value">{String(value)}</span></div>);
  return <div className="portal-layout"><nav className="portal-nav"><div className="nav-brand">🏥 MED AI — Doctor Portal</div><button className="logout-btn" onClick={() => navigate('/search')}>← Back to Search</button></nav><main className="portal-content"><div className="patient-header"><div><h1>{data.patient_information?.full_name || 'Patient Record'}</h1><p>{data.patient_information?.patient_identifier} • {doc.file_name}</p></div><span className="approved-tag">✓ Approved report</span></div><div className="sections-grid">{sections.map(([key, label]) => { const value = data[key]; if (!value) return null; const items = Array.isArray(value) ? value : [value]; const content = items.map((item: Record<string, unknown>, index: number) => <div className="array-item" key={index}>{rows(item)}</div>); return content.some(Boolean) ? <section className="section-card" key={key}><h2>{label}</h2>{content}</section> : null; })}</div></main></div>;
}

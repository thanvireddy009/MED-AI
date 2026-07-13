import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ReviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<any>(null);
  const [data, setData] = useState<any>(null);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    fetchDoc();
    fetchHistory();
  }, [id]);

  const fetchDoc = async () => {
    const res = await axios.get(`${API}/api/documents/${id}`);
    setDoc(res.data);
    setData(res.data.extracted_data || null);
    setNotes(res.data.review_notes || '');
  };

  const fetchHistory = async () => {
    const res = await axios.get(`${API}/api/reviews/${id}`);
    setHistory(res.data);
  };

  const handleLoadExtracted = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API}/api/documents/${id}/load-extracted`);
      setData(res.data.extracted_data);
      setDoc(res.data);
      alert('✓ Extracted data loaded successfully!');
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to load extracted data');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (section: string, field: string, value: string) => {
    setData((prev: any) => ({
      ...prev,
      [section]: { ...prev[section], [field]: value }
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    await axios.put(`${API}/api/documents/${id}/data`, {
      extracted_data: data,
      validated_data: data
    });
    setSaving(false);
    alert('Saved!');
  };

  const handleApprove = async () => {
    if (!window.confirm('Approve this document?')) return;
    await axios.put(`${API}/api/documents/${id}/approve`, { notes, updated_data: data });
    navigate('/');
  };

  const handleReject = async () => {
    const reason = window.prompt('Reason for rejection:');
    if (!reason) return;
    await axios.put(`${API}/api/documents/${id}/reject`, { notes: reason });
    navigate('/');
  };

  if (!doc) return <div className="loading">Loading document...</div>;

  const sections = [
    { key: 'patient_information', label: 'Patient Information' },
    { key: 'adverse_events', label: 'Adverse Events' },
    { key: 'suspect_drug', label: 'Suspect Drug' },
    { key: 'medical_history', label: 'Medical History' },
    { key: 'reporter_information', label: 'Reporter Information' },
  ];

  return (
    <div className="review-page">
      <div className="review-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Back</button>
        <h2>{doc.file_name}</h2>
        <span className={`status-badge status-${doc.status}`}>{doc.status}</span>
      </div>

      <div className="review-layout">
        {/* PDF Viewer */}
        <div className="pdf-panel">
          <h3>Original Document</h3>
          <iframe
            src={`${API}/uploads/${doc.file_path.split('/').pop()}`}
            width="100%"
            height="700px"
            title="PDF Preview"
          />
        </div>

        {/* Extracted Data Editor */}
        <div className="data-panel">
          <h3>Extracted Data</h3>

          {!data ? (
            <div className="no-data">
              <p>No extracted data yet for this document.</p>
              <button className="load-btn" onClick={handleLoadExtracted} disabled={loading}>
                {loading ? 'Loading...' : '⚡ Load Extracted Data'}
              </button>
            </div>
          ) : (
            <>
              <div style={{display:'flex', justifyContent:'flex-end', marginBottom:'0.75rem'}}>
                <button className="load-btn-small" onClick={handleLoadExtracted} disabled={loading}>
                  {loading ? 'Reloading...' : '↻ Reload from JSON'}
                </button>
              </div>

              {sections.map(({ key, label }) => (
                data[key] && typeof data[key] === 'object' && !Array.isArray(data[key]) && (
                  <div className="section-card" key={key}>
                    <h4>{label}</h4>
                    {Object.entries(data[key] || {}).map(([field, value]) => (
                      <div className="field-row" key={field}>
                        <label>{field.replace(/_/g, ' ')}</label>
                        <input
                          value={String(value || '')}
                          onChange={e => handleFieldChange(key, field, e.target.value)}
                          className={value === 'N/A' ? 'field-na' : ''}
                        />
                      </div>
                    ))}
                  </div>
                )
              ))}

              <div className="notes-section">
                <label>Review Notes</label>
                <textarea
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  placeholder="Add review notes..."
                  rows={3}
                />
              </div>

              <div className="action-buttons">
                <button className="save-btn" onClick={handleSave} disabled={saving}>
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
                <button className="approve-btn" onClick={handleApprove}>✓ Approve</button>
                <button className="reject-btn" onClick={handleReject}>✗ Reject</button>
              </div>
            </>
          )}

          {history.length > 0 && (
            <div className="history-section">
              <h4>Review History</h4>
              {history.map((h: any) => (
                <div className="history-item" key={h.id}>
                  <span className={`status-badge status-${h.action}`}>{h.action}</span>
                  <span>{new Date(h.reviewed_at).toLocaleString()}</span>
                  {h.notes && <span>— {h.notes}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

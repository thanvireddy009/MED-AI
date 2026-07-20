import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import { Session } from '../auth';

const API = process.env.REACT_APP_API_URL || 'http://localhost:9000';
const headers = (token: string) => ({ Authorization: `Bearer ${token}` });

interface Document { id: string; file_name: string; upload_date: string; status: string; review_notes: string; }

export default function Dashboard({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();
  const refresh = async () => { try { setDocuments((await axios.get(`${API}/api/documents`, { headers: headers(session.token) })).data); } finally { setLoading(false); } };
  useEffect(() => { refresh(); }, []);
  const upload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files?.[0]) return;
    setUploading(true);
    try { const form = new FormData(); form.append('file', event.target.files[0]); await axios.post(`${API}/api/documents/upload`, form, { headers: headers(session.token) }); await refresh(); }
    catch { alert('Upload failed.'); } finally { setUploading(false); event.target.value = ''; }
  };
  const remove = async (id: string) => { if (!window.confirm('Delete this document?')) return; await axios.delete(`${API}/api/documents/${id}`, { headers: headers(session.token) }); refresh(); };
  const color: Record<string, string> = { pending: '#f59e0b', reviewed: '#3b82f6', approved: '#10b981', rejected: '#ef4444' };
  return <div className="app"><nav className="navbar"><div className="nav-brand">🏥 MED AI Review</div><div className="nav-links"><Link to="/dashboard">Dashboard</Link><Link to="/history">Review History</Link><button onClick={onLogout}>Sign out</button></div></nav><main className="main-content">
    <div className="dashboard-header"><h1>Document Review Dashboard</h1><label className="upload-btn">{uploading ? 'Uploading…' : '+ Upload PDF'}<input type="file" accept=".pdf" hidden onChange={upload} /></label></div>
    <div className="stats-row">{['pending', 'reviewed', 'approved', 'rejected'].map(status => <div className="stat-card" key={status}><span className="stat-count">{documents.filter(d => d.status === status).length}</span><span className="stat-label">{status}</span></div>)}</div>
    {loading ? <p className="loading">Loading…</p> : <table className="doc-table"><thead><tr><th>File name</th><th>Uploaded</th><th>Status</th><th>Notes</th><th>Actions</th></tr></thead><tbody>{documents.map(doc => <tr key={doc.id}><td>{doc.file_name}</td><td>{new Date(doc.upload_date).toLocaleDateString()}</td><td><span className="status-badge" style={{ background: color[doc.status] }}>{doc.status}</span></td><td>{doc.review_notes || '—'}</td><td className="action-btns"><button onClick={() => navigate(`/review/${doc.id}`)}>Review</button><button className="delete-btn" onClick={() => remove(doc.id)}>Delete</button></td></tr>)}{!documents.length && <tr><td colSpan={5} className="empty">No documents yet — upload a PDF to get started.</td></tr>}</tbody></table>}
  </main></div>;
}

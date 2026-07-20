import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Session } from '../auth';
const API = process.env.REACT_APP_API_URL || 'http://localhost:9000';
export default function HistoryPage({ session }: { session: Session }) {
  const [history, setHistory] = useState<any[]>([]);
  useEffect(() => { axios.get(`${API}/api/reviews`, { headers: { Authorization: `Bearer ${session.token}` } }).then(r => setHistory(r.data)); }, [session.token]);
  return <div className="app"><nav className="navbar"><div className="nav-brand">🏥 MED AI Review</div><div className="nav-links"><Link to="/dashboard">Dashboard</Link><Link to="/history">Review History</Link></div></nav><main className="main-content history-page"><h1>Review History</h1><table className="doc-table"><thead><tr><th>File</th><th>Action</th><th>Reviewer</th><th>Date</th><th>Notes</th></tr></thead><tbody>{history.map(item => <tr key={item.id}><td>{item.file_name}</td><td><span className={`status-badge status-${item.action}`}>{item.action}</span></td><td>{item.reviewer}</td><td>{new Date(item.reviewed_at).toLocaleString()}</td><td>{item.notes || '—'}</td></tr>)}{!history.length && <tr><td colSpan={5} className="empty">No review history yet.</td></tr>}</tbody></table></main></div>;
}

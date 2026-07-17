import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_API_URL || 'http://localhost:9000';
const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('token') || ''}` });

export default function HistoryPage() {
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    axios.get(`${API}/api/reviews`, { headers: authHeaders() }).then(res => setHistory(res.data));
  }, []);

  return (
    <div className="history-page">
      <h1>Review History</h1>
      <table className="doc-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Action</th>
            <th>Reviewer</th>
            <th>Date</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {history.map(h => (
            <tr key={h.id}>
              <td>{h.file_name}</td>
              <td><span className={`status-badge status-${h.action}`}>{h.action}</span></td>
              <td>{h.reviewer}</td>
              <td>{new Date(h.reviewed_at).toLocaleString()}</td>
              <td>{h.notes || '—'}</td>
            </tr>
          ))}
          {!history.length && (
            <tr><td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>No review history yet</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

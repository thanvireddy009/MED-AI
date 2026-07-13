import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface Document {
  id: string;
  file_name: string;
  upload_date: string;
  status: string;
  review_notes: string;
}

export default function Dashboard() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => { fetchDocuments(); }, []);

  const fetchDocuments = async () => {
    try {
      const res = await axios.get(`${API}/api/documents`);
      setDocuments(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('pdf', e.target.files[0]);
    try {
      await axios.post(`${API}/api/documents/upload`, formData);
      fetchDocuments();
    } catch (err) {
      alert('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this document?')) return;
    await axios.delete(`${API}/api/documents/${id}`);
    fetchDocuments();
  };

  const statusColor: Record<string, string> = {
    pending: '#f59e0b',
    reviewed: '#3b82f6',
    approved: '#10b981',
    rejected: '#ef4444',
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Document Review Dashboard</h1>
        <label className="upload-btn">
          {uploading ? 'Uploading...' : '+ Upload PDF'}
          <input type="file" accept=".pdf" onChange={handleUpload} hidden />
        </label>
      </div>

      <div className="stats-row">
        {['pending', 'reviewed', 'approved', 'rejected'].map(s => (
          <div className="stat-card" key={s}>
            <span className="stat-count">{documents.filter(d => d.status === s).length}</span>
            <span className="stat-label">{s}</span>
          </div>
        ))}
      </div>

      {loading ? <p>Loading...</p> : (
        <table className="doc-table">
          <thead>
            <tr>
              <th>File Name</th>
              <th>Uploaded</th>
              <th>Status</th>
              <th>Notes</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map(doc => (
              <tr key={doc.id}>
                <td>{doc.file_name}</td>
                <td>{new Date(doc.upload_date).toLocaleDateString()}</td>
                <td>
                  <span className="status-badge" style={{ background: statusColor[doc.status] }}>
                    {doc.status}
                  </span>
                </td>
                <td>{doc.review_notes || '—'}</td>
                <td className="action-btns">
                  <button onClick={() => navigate(`/review/${doc.id}`)}>Review</button>
                  <button className="delete-btn" onClick={() => handleDelete(doc.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {!documents.length && (
              <tr><td colSpan={5} style={{textAlign:'center', padding:'2rem'}}>No documents yet — upload a PDF to get started</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

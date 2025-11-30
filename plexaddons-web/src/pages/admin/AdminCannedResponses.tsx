import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../../services/api';
import type { CannedResponse, TicketCategory } from '../../types';
import Spinner from '../../components/Spinner';
import './AdminCannedResponses.css';

const CATEGORY_LABELS: Record<string, string> = {
  general: 'General',
  billing: 'Billing',
  technical: 'Technical',
  feature_request: 'Feature Request',
  bug_report: 'Bug Report',
};

export default function AdminCannedResponses() {
  const [responses, setResponses] = useState<CannedResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInactive, setShowInactive] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  
  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    category: '' as TicketCategory | '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadResponses();
  }, [showInactive]);

  const loadResponses = async () => {
    try {
      setLoading(true);
      const data = await api.listCannedResponses(undefined, showInactive);
      setResponses(data.responses || []);
    } catch (err: any) {
      toast.error(err.message || 'Failed to load canned responses');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingId(null);
    setFormData({ title: '', content: '', category: '' });
    setShowForm(true);
  };

  const handleEdit = (response: CannedResponse) => {
    setEditingId(response.id);
    setFormData({
      title: response.title,
      content: response.content,
      category: response.category || '',
    });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim() || !formData.content.trim()) {
      toast.error('Title and content are required');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        title: formData.title,
        content: formData.content,
        category: formData.category || undefined,
      };

      if (editingId) {
        await api.updateCannedResponse(editingId, payload);
        toast.success('Response updated');
      } else {
        await api.createCannedResponse(payload);
        toast.success('Response created');
      }

      setShowForm(false);
      setEditingId(null);
      setFormData({ title: '', content: '', category: '' });
      await loadResponses();
    } catch (err: any) {
      toast.error(err.message || 'Failed to save response');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (response: CannedResponse) => {
    toast.promise(
      api.updateCannedResponse(response.id, { is_active: !response.is_active }).then(() => loadResponses()),
      {
        loading: response.is_active ? 'Deactivating...' : 'Activating...',
        success: response.is_active ? 'Response deactivated' : 'Response activated',
        error: (err: any) => err.message || 'Failed to update status',
      }
    );
  };

  const handleDelete = async (response: CannedResponse) => {
    toast.promise(
      api.deleteCannedResponse(response.id).then(() => loadResponses()),
      {
        loading: 'Deleting response...',
        success: 'Response deleted',
        error: (err: any) => err.message || 'Failed to delete response',
      }
    );
  };

  const filteredResponses = responses.filter((r) => {
    if (categoryFilter === 'all') return true;
    if (categoryFilter === 'none') return !r.category;
    return r.category === categoryFilter;
  });

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="admin-canned-responses">
        <div className="loading-state">
          <Spinner size={40} />
        </div>
      </div>
    );
  }

  return (
    <div className="admin-canned-responses">
      <div className="page-header">
        <div>
          <h1>Canned Responses</h1>
          <p>Create and manage reusable ticket responses</p>
        </div>
        <button className="btn btn-primary" onClick={handleCreate}>
          + New Response
        </button>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <label>Category:</label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Categories</option>
            <option value="none">No Category</option>
            {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            Show inactive
          </label>
        </div>
      </div>

      {filteredResponses.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📝</div>
          <h2>No canned responses found</h2>
          <p>Create your first canned response to speed up ticket replies.</p>
          <button className="btn btn-primary" onClick={handleCreate}>
            Create Response
          </button>
        </div>
      ) : (
        <div className="responses-grid">
          {filteredResponses.map((response) => (
            <div key={response.id} className={`response-card ${!response.is_active ? 'inactive' : ''}`}>
              <div className="response-header">
                <h3>{response.title}</h3>
                <div className="response-badges">
                  {response.category && (
                    <span className="category-badge">{CATEGORY_LABELS[response.category]}</span>
                  )}
                  {!response.is_active && (
                    <span className="status-badge inactive">Inactive</span>
                  )}
                </div>
              </div>
              <div className="response-content">
                {response.content.length > 200 
                  ? response.content.substring(0, 200) + '...' 
                  : response.content}
              </div>
              <div className="response-meta">
                <span className="usage-count">Used {response.usage_count} times</span>
                <span className="created-by">
                  by {response.creator_username || 'Unknown'} on {formatDate(response.created_at)}
                </span>
              </div>
              <div className="response-actions">
                <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(response)}>
                  Edit
                </button>
                <button 
                  className={`btn btn-sm ${response.is_active ? 'btn-warning' : 'btn-success'}`}
                  onClick={() => handleToggleActive(response)}
                >
                  {response.is_active ? 'Deactivate' : 'Activate'}
                </button>
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(response)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => !saving && setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingId ? 'Edit Response' : 'New Response'}</h2>
              <button 
                className="modal-close" 
                onClick={() => !saving && setShowForm(false)}
                disabled={saving}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="title">Title *</label>
                <input
                  type="text"
                  id="title"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g., Greeting, Resolution Confirmation"
                  required
                  disabled={saving}
                />
              </div>
              <div className="form-group">
                <label htmlFor="category">Category</label>
                <select
                  id="category"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value as TicketCategory | '' })}
                  disabled={saving}
                >
                  <option value="">No specific category</option>
                  {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="content">Content *</label>
                <textarea
                  id="content"
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  placeholder="Enter the response template..."
                  rows={8}
                  required
                  disabled={saving}
                />
                <span className="form-hint">
                  Tip: You can use placeholders like {'{username}'} or {'{ticket_id}'} for dynamic content.
                </span>
              </div>
              <div className="modal-actions">
                <button 
                  type="button" 
                  className="btn btn-secondary"
                  onClick={() => setShowForm(false)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : editingId ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

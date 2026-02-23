import { useState, useEffect, FormEvent } from 'react';
import { api } from '../services/api';
import { toast } from 'sonner';
import { WebhookEndpoint, WebhookDelivery, WebhookEndpointCreate, WebhookEndpointUpdate, WEBHOOK_EVENTS } from '../types';
import './WebhookManager.css';

export default function WebhookManager() {
  const [endpoints, setEndpoints] = useState<WebhookEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingEndpoint, setEditingEndpoint] = useState<WebhookEndpoint | null>(null);
  const [expandedDeliveries, setExpandedDeliveries] = useState<number | null>(null);
  const [deliveries, setDeliveries] = useState<Record<number, WebhookDelivery[]>>({});
  const [newSecret, setNewSecret] = useState<{ id: number; secret: string } | null>(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formEvents, setFormEvents] = useState<string[]>([]);
  const [formTemplate, setFormTemplate] = useState('');
  const [formActive, setFormActive] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadEndpoints();
  }, []);

  const loadEndpoints = async () => {
    try {
      const data = await api.listWebhookEndpoints();
      setEndpoints(data);
    } catch {
      toast.error('Failed to load webhook endpoints');
    } finally {
      setLoading(false);
    }
  };

  const openCreateForm = () => {
    setEditingEndpoint(null);
    setFormName('');
    setFormUrl('');
    setFormEvents([]);
    setFormTemplate('');
    setFormActive(true);
    setShowForm(true);
  };

  const openEditForm = (ep: WebhookEndpoint) => {
    setEditingEndpoint(ep);
    setFormName(ep.name);
    setFormUrl(ep.url);
    setFormEvents(ep.event_filter || []);
    setFormTemplate(ep.payload_template || '');
    setFormActive(ep.is_active);
    setShowForm(true);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingEndpoint) {
        const update: WebhookEndpointUpdate = {
          name: formName,
          url: formUrl,
          is_active: formActive,
          event_filter: formEvents.length > 0 ? formEvents : undefined,
          payload_template: formTemplate || undefined,
        };
        const updated = await api.updateWebhookEndpoint(editingEndpoint.id, update);
        setEndpoints(prev => prev.map(ep => ep.id === updated.id ? updated : ep));
        toast.success('Endpoint updated');
      } else {
        const create: WebhookEndpointCreate = {
          name: formName,
          url: formUrl,
          event_filter: formEvents.length > 0 ? formEvents : undefined,
          payload_template: formTemplate || undefined,
        };
        const created = await api.createWebhookEndpoint(create);
        setEndpoints(prev => [...prev, created]);
        setNewSecret({ id: created.id, secret: created.secret });
        toast.success('Endpoint created! Copy the secret below.');
      }
      setShowForm(false);
    } catch (err: any) {
      toast.error(err.message || 'Failed to save endpoint');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this webhook endpoint? This cannot be undone.')) return;
    try {
      await api.deleteWebhookEndpoint(id);
      setEndpoints(prev => prev.filter(ep => ep.id !== id));
      toast.success('Endpoint deleted');
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete endpoint');
    }
  };

  const handleTest = async (id: number) => {
    try {
      const result = await api.testWebhookEndpoint(id);
      if (result.success) {
        toast.success(`Test successful! Status: ${result.status_code}`);
      } else {
        toast.error(`Test failed: ${result.error}`);
      }
    } catch (err: any) {
      toast.error(err.message || 'Test failed');
    }
  };

  const handleRotateSecret = async (id: number) => {
    if (!confirm('Regenerate the secret? You\'ll need to update it in your server.')) return;
    try {
      const result = await api.rotateWebhookEndpointSecret(id);
      setNewSecret({ id, secret: result.secret });
      toast.success('Secret rotated! Copy it now.');
    } catch (err: any) {
      toast.error(err.message || 'Failed to rotate secret');
    }
  };

  const toggleDeliveries = async (endpointId: number) => {
    if (expandedDeliveries === endpointId) {
      setExpandedDeliveries(null);
      return;
    }
    setExpandedDeliveries(endpointId);
    if (!deliveries[endpointId]) {
      try {
        const data = await api.getWebhookDeliveries(endpointId);
        setDeliveries(prev => ({ ...prev, [endpointId]: data }));
      } catch {
        toast.error('Failed to load deliveries');
      }
    }
  };

  const handleRetry = async (deliveryId: number, endpointId: number) => {
    try {
      const result = await api.retryWebhookDelivery(deliveryId);
      if (result.success) {
        toast.success('Retry successful!');
      } else {
        toast.error(`Retry failed: ${result.error}`);
      }
      // Refresh deliveries
      const data = await api.getWebhookDeliveries(endpointId);
      setDeliveries(prev => ({ ...prev, [endpointId]: data }));
    } catch (err: any) {
      toast.error(err.message || 'Retry failed');
    }
  };

  const toggleEvent = (eventValue: string) => {
    setFormEvents(prev =>
      prev.includes(eventValue)
        ? prev.filter(e => e !== eventValue)
        : [...prev, eventValue]
    );
  };

  const copySecret = (secret: string) => {
    navigator.clipboard.writeText(secret);
    toast.success('Secret copied to clipboard');
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return <div className="webhook-manager"><p>Loading...</p></div>;
  }

  return (
    <div className="webhook-manager">
      <p className="section-description">
        Manage webhook endpoints to receive real-time notifications about your addon events.
        You can create up to 10 endpoints with per-event filtering and custom payload templates.
      </p>

      {newSecret && (
        <div className="secret-display">
          <span>⚠️ Copy this secret now — it won't be shown again:</span>
          <code>{newSecret.secret}</code>
          <button className="btn btn-secondary btn-sm" onClick={() => copySecret(newSecret.secret)}>
            Copy
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => setNewSecret(null)}>
            Dismiss
          </button>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="endpoint-count">{endpoints.length}/10 endpoints</span>
        <button className="btn btn-primary btn-sm" onClick={openCreateForm} disabled={endpoints.length >= 10}>
          + Add Endpoint
        </button>
      </div>

      {endpoints.length === 0 ? (
        <div className="no-endpoints">
          <p>No webhook endpoints configured yet.</p>
          <p>Create one to start receiving event notifications.</p>
        </div>
      ) : (
        <div className="webhook-endpoints-list">
          {endpoints.map(ep => (
            <div key={ep.id} className={`webhook-endpoint-card ${ep.is_active ? '' : 'inactive'}`}>
              <div className="endpoint-header">
                <div className="endpoint-header-left">
                  <h4>{ep.name}</h4>
                  <span className={`endpoint-status ${ep.is_active ? 'active' : 'inactive'}`}>
                    {ep.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="endpoint-actions">
                  <button className="btn btn-secondary btn-sm" onClick={() => handleTest(ep.id)}>
                    Test
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => toggleDeliveries(ep.id)}>
                    {expandedDeliveries === ep.id ? 'Hide Log' : 'Log'}
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => openEditForm(ep)}>
                    Edit
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => handleRotateSecret(ep.id)}>
                    Rotate
                  </button>
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(ep.id)}>
                    Delete
                  </button>
                </div>
              </div>

              <div className="endpoint-url">{ep.url}</div>

              <div className="endpoint-events">
                {ep.event_filter && ep.event_filter.length > 0
                  ? ep.event_filter.map(evt => (
                      <span key={evt} className="event-tag">{evt}</span>
                    ))
                  : <span className="event-tag all">All events</span>
                }
              </div>

              {expandedDeliveries === ep.id && (
                <div className="deliveries-panel">
                  <h5>Recent Deliveries</h5>
                  {(deliveries[ep.id] || []).length === 0 ? (
                    <div className="no-deliveries">
                      <p>No deliveries yet</p>
                    </div>
                  ) : (
                    <div className="deliveries-list">
                      {(deliveries[ep.id] || []).map(d => (
                        <div key={d.id} className="delivery-row">
                          <span className={`delivery-status-badge ${d.status}`}>
                            {d.status}
                          </span>
                          <span className="delivery-event">{d.event_type}</span>
                          <span className="delivery-time">
                            {d.status_code && `${d.status_code} · `}
                            {formatTime(d.created_at)}
                            {d.attempt > 1 && ` (attempt ${d.attempt})`}
                          </span>
                          {d.status === 'failed' && (
                            <div className="delivery-actions">
                              <button className="btn btn-secondary btn-sm" onClick={() => handleRetry(d.id, ep.id)}>
                                Retry
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <div className="endpoint-form-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowForm(false); }}>
          <div className="endpoint-form">
            <h3>{editingEndpoint ? 'Edit Endpoint' : 'New Webhook Endpoint'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={formName}
                  onChange={e => setFormName(e.target.value)}
                  placeholder="e.g. Production Server"
                  required
                  maxLength={100}
                />
              </div>

              <div className="form-group">
                <label>URL</label>
                <input
                  type="url"
                  value={formUrl}
                  onChange={e => setFormUrl(e.target.value)}
                  placeholder="https://your-server.com/webhook"
                  required
                />
                <small>We support Discord webhook URLs with automatic embed formatting.</small>
              </div>

              {editingEndpoint && (
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={formActive}
                      onChange={e => setFormActive(e.target.checked)}
                    />{' '}
                    Active
                  </label>
                </div>
              )}

              <div className="form-group">
                <label>Event Filter (optional — leave empty for all events)</label>
                <div className="event-checkboxes">
                  {WEBHOOK_EVENTS.map(evt => (
                    <label key={evt.value}>
                      <input
                        type="checkbox"
                        checked={formEvents.includes(evt.value)}
                        onChange={() => toggleEvent(evt.value)}
                      />
                      {evt.label}
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>Payload Template (optional)</label>
                <textarea
                  value={formTemplate}
                  onChange={e => setFormTemplate(e.target.value)}
                  placeholder='{"event": "{{event}}", "addon": "{{addon.name}}"}'
                  rows={4}
                />
                <small>
                  JSON template with {'{{variable}}'} placeholders. Leave empty for default format.
                  Discord URLs ignore templates and use embeds automatically.
                </small>
              </div>

              <div className="button-row">
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : editingEndpoint ? 'Update' : 'Create'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

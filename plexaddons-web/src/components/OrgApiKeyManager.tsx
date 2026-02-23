import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type { OrgApiKey } from '../types';

interface Props {
  orgSlug: string;
}

export default function OrgApiKeyManager({ orgSlug }: Props) {
  const [keys, setKeys] = useState<OrgApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyRevealed, setNewKeyRevealed] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadKeys();
  }, [orgSlug]);

  const loadKeys = async () => {
    try {
      setLoading(true);
      const res = await api.listOrgApiKeys(orgSlug);
      setKeys(res.api_keys);
    } catch (err: any) {
      toast.error(err.message || 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setSaving(true);
    try {
      const created = await api.createOrgApiKey(orgSlug, { name: newKeyName });
      setNewKeyRevealed(created.key);
      setNewKeyName('');
      setShowCreate(false);
      await loadKeys();
      toast.success('API key created! Copy it now — it won\'t be shown again.');
    } catch (err: any) {
      toast.error(err.message || 'Failed to create API key');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (keyId: number) => {
    if (!confirm('Delete this API key? This cannot be undone.')) return;
    try {
      await api.deleteOrgApiKey(orgSlug, keyId);
      setKeys(prev => prev.filter(k => k.id !== keyId));
      toast.success('API key deleted');
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete API key');
    }
  };

  const copyKey = () => {
    if (newKeyRevealed) {
      navigator.clipboard.writeText(newKeyRevealed);
      toast.success('Key copied to clipboard');
    }
  };

  return (
    <div className="org-api-keys">
      <div className="section-header">
        <h3>Organization API Keys</h3>
        <button className="btn btn-sm btn-primary" onClick={() => setShowCreate(true)}>
          + Create Key
        </button>
      </div>

      {newKeyRevealed && (
        <div className="key-revealed">
          <p><strong>New API Key (copy now — won't be shown again):</strong></p>
          <div className="key-display">
            <code>{newKeyRevealed}</code>
            <button className="btn btn-sm btn-secondary" onClick={copyKey}>Copy</button>
          </div>
          <button className="btn btn-sm" onClick={() => setNewKeyRevealed(null)}>Dismiss</button>
        </div>
      )}

      {loading ? (
        <div className="spinner" />
      ) : keys.length === 0 ? (
        <p className="no-data">No API keys yet.</p>
      ) : (
        <div className="api-keys-list">
          {keys.map(key => (
            <div key={key.id} className="api-key-row">
              <div className="api-key-info">
                <strong>{key.name}</strong>
                <span className="key-prefix">{key.key_prefix}...</span>
                {key.created_by_username && (
                  <span className="key-creator">by {key.created_by_username}</span>
                )}
                <span className="key-date">
                  Created {new Date(key.created_at).toLocaleDateString()}
                </span>
                {key.last_used_at && (
                  <span className="key-used">
                    Last used {new Date(key.last_used_at).toLocaleDateString()}
                  </span>
                )}
                {key.expires_at && (
                  <span className="key-expires">
                    Expires {new Date(key.expires_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete(key.id)}>
                Delete
              </button>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <div className="modal-overlay" onClick={() => !saving && setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Create Organization API Key</h3>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label htmlFor="keyName">Key Name *</label>
                <input
                  type="text"
                  id="keyName"
                  value={newKeyName}
                  onChange={e => setNewKeyName(e.target.value)}
                  required
                  placeholder="e.g. CI/CD Pipeline"
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)} disabled={saving}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

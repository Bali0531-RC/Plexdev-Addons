import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { toast } from 'sonner';
import './ApiKeysManager.css';

interface ApiKeyScope {
  scope: string;
  name: string;
  description: string;
  min_tier: string;
}

interface ApiKey {
  id: number;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  usage_count: number;
  created_at: string;
}

interface CreateKeyData {
  name: string;
  scopes: string[];
  expires_at?: string;
}

export default function ApiKeysManager() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [availableScopes, setAvailableScopes] = useState<ApiKeyScope[]>([]);
  const [maxKeys, setMaxKeys] = useState(0);
  const [_tier, setTier] = useState('');  // eslint-disable-line @typescript-eslint/no-unused-vars
  const [loading, setLoading] = useState(true);
  
  // Create key modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [expiresIn, setExpiresIn] = useState<string>('never');
  const [creating, setCreating] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  
  // Revoke/delete state
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [keysData, scopesData] = await Promise.all([
        api.listApiKeys(),
        api.getAvailableScopes(),
      ]);
      setKeys(keysData.keys);
      setAvailableScopes(scopesData.scopes);
      setMaxKeys(scopesData.max_keys);
      setTier(scopesData.tier);
    } catch (err) {
      console.error('Failed to fetch API keys:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a name for the key');
      return;
    }
    if (selectedScopes.length === 0) {
      toast.error('Please select at least one permission');
      return;
    }

    setCreating(true);
    try {
      const data: CreateKeyData = {
        name: newKeyName.trim(),
        scopes: selectedScopes,
      };
      
      if (expiresIn !== 'never') {
        const now = new Date();
        switch (expiresIn) {
          case '7d':
            now.setDate(now.getDate() + 7);
            break;
          case '30d':
            now.setDate(now.getDate() + 30);
            break;
          case '90d':
            now.setDate(now.getDate() + 90);
            break;
          case '1y':
            now.setFullYear(now.getFullYear() + 1);
            break;
        }
        data.expires_at = now.toISOString();
      }

      const result = await api.createApiKey(data);
      setNewlyCreatedKey(result.api_key);
      setKeys([result.key, ...keys]);
      toast.success('API key created! Make sure to copy it now.');
    } catch (err: any) {
      toast.error(err.message || 'Failed to create API key');
    } finally {
      setCreating(false);
    }
  };

  const handleRevokeKey = async (keyId: number) => {
    if (!confirm('Revoke this API key? It will stop working immediately.')) return;
    
    setActionLoading(keyId);
    try {
      await api.revokeApiKey(keyId);
      setKeys(keys.map(k => k.id === keyId ? { ...k, is_active: false } : k));
      toast.success('API key revoked');
    } catch (err: any) {
      toast.error(err.message || 'Failed to revoke key');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteKey = async (keyId: number) => {
    if (!confirm('Permanently delete this API key? This cannot be undone.')) return;
    
    setActionLoading(keyId);
    try {
      await api.deleteApiKey(keyId);
      setKeys(keys.filter(k => k.id !== keyId));
      toast.success('API key deleted');
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete key');
    } finally {
      setActionLoading(null);
    }
  };

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    toast.success('API key copied to clipboard');
  };

  const toggleScope = (scope: string) => {
    if (selectedScopes.includes(scope)) {
      setSelectedScopes(selectedScopes.filter(s => s !== scope));
    } else {
      setSelectedScopes([...selectedScopes, scope]);
    }
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setNewKeyName('');
    setSelectedScopes([]);
    setExpiresIn('never');
    setNewlyCreatedKey(null);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  const formatLastUsed = (dateStr: string | null) => {
    if (!dateStr) return 'Never used';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return <div className="api-keys-loading">Loading API keys...</div>;
  }

  if (maxKeys === 0) {
    return (
      <div className="api-keys-upgrade">
        <h3>API Keys</h3>
        <p>API keys are available for Pro and Premium subscribers.</p>
        <a href="/dashboard/subscription" className="btn btn-primary">
          Upgrade Now
        </a>
      </div>
    );
  }

  return (
    <div className="api-keys-manager">
      <div className="api-keys-header">
        <div>
          <h3>API Keys</h3>
          <p className="keys-count">{keys.length} of {maxKeys} keys used</p>
        </div>
        <button 
          className="btn btn-primary"
          onClick={() => setShowCreateModal(true)}
          disabled={keys.length >= maxKeys}
        >
          Create API Key
        </button>
      </div>

      {/* Keys List */}
      {keys.length === 0 ? (
        <div className="no-keys">
          <p>No API keys yet. Create one to get started with the automation API.</p>
        </div>
      ) : (
        <div className="keys-list">
          {keys.map(key => (
            <div key={key.id} className={`key-card ${!key.is_active ? 'revoked' : ''}`}>
              <div className="key-main">
                <div className="key-info">
                  <div className="key-name-row">
                    <span className="key-name">{key.name}</span>
                    {!key.is_active && <span className="key-badge revoked">Revoked</span>}
                    {key.expires_at && new Date(key.expires_at) < new Date() && (
                      <span className="key-badge expired">Expired</span>
                    )}
                  </div>
                  <div className="key-prefix">
                    <code>{key.key_prefix}...</code>
                  </div>
                </div>
                <div className="key-meta">
                  <span title="Last used">🕐 {formatLastUsed(key.last_used_at)}</span>
                  <span title="Usage count">📊 {key.usage_count} requests</span>
                  <span title="Created">📅 {formatDate(key.created_at)}</span>
                  {key.expires_at && (
                    <span title="Expires">⏰ Expires {formatDate(key.expires_at)}</span>
                  )}
                </div>
              </div>
              
              <div className="key-scopes">
                {key.scopes.map(scope => (
                  <span key={scope} className="scope-badge">{scope}</span>
                ))}
              </div>
              
              <div className="key-actions">
                {key.is_active ? (
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => handleRevokeKey(key.id)}
                    disabled={actionLoading === key.id}
                  >
                    {actionLoading === key.id ? '...' : 'Revoke'}
                  </button>
                ) : (
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDeleteKey(key.id)}
                    disabled={actionLoading === key.id}
                  >
                    {actionLoading === key.id ? '...' : 'Delete'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Key Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={closeCreateModal}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>Create API Key</h3>
            
            {newlyCreatedKey ? (
              <div className="key-created-view">
                <div className="success-icon">✓</div>
                <p className="warning-text">
                  <strong>Save this key now!</strong> It won't be shown again.
                </p>
                <div className="new-key-display">
                  <code>{newlyCreatedKey}</code>
                  <button 
                    className="btn btn-secondary btn-sm"
                    onClick={() => copyKey(newlyCreatedKey)}
                  >
                    Copy
                  </button>
                </div>
                <button className="btn btn-primary" onClick={closeCreateModal}>
                  Done
                </button>
              </div>
            ) : (
              <>
                <div className="form-group">
                  <label>Key Name</label>
                  <input
                    type="text"
                    value={newKeyName}
                    onChange={e => setNewKeyName(e.target.value)}
                    placeholder="e.g., GitHub Actions, My Script"
                    maxLength={100}
                  />
                  <small>A friendly name to identify this key</small>
                </div>

                <div className="form-group">
                  <label>Permissions</label>
                  <div className="scopes-grid">
                    {availableScopes.map(scope => (
                      <label key={scope.scope} className="scope-option">
                        <input
                          type="checkbox"
                          checked={selectedScopes.includes(scope.scope)}
                          onChange={() => toggleScope(scope.scope)}
                        />
                        <div className="scope-info">
                          <span className="scope-name">{scope.name}</span>
                          <span className="scope-desc">{scope.description}</span>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="form-group">
                  <label>Expiration</label>
                  <select
                    value={expiresIn}
                    onChange={e => setExpiresIn(e.target.value)}
                  >
                    <option value="never">Never expires</option>
                    <option value="7d">7 days</option>
                    <option value="30d">30 days</option>
                    <option value="90d">90 days</option>
                    <option value="1y">1 year</option>
                  </select>
                </div>

                <div className="modal-actions">
                  <button className="btn btn-secondary" onClick={closeCreateModal}>
                    Cancel
                  </button>
                  <button 
                    className="btn btn-primary" 
                    onClick={handleCreateKey}
                    disabled={creating}
                  >
                    {creating ? 'Creating...' : 'Create Key'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Documentation */}
      <div className="api-keys-docs">
        <h4>Using API Keys</h4>
        <p>Include your API key in the <code>X-API-Key</code> header:</p>
        <pre>
{`curl -X GET "https://addons.plexdev.xyz/api/v1/automation/addons" \\
  -H "X-API-Key: pa_your_key_here"`}
        </pre>
        <p>
          <strong>Pro tier:</strong> Read-only access (addons, versions, analytics)<br/>
          <strong>Premium tier:</strong> Full access including publishing versions and managing webhooks
        </p>
      </div>
    </div>
  );
}

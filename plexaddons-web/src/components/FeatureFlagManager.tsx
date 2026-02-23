import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type { FeatureFlag, FeatureFlagCreate } from '../types';
import './FeatureFlagManager.css';

interface Props {
  addonId: number;
}

export default function FeatureFlagManager({ addonId }: Props) {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [key, setKey] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [percentage, setPercentage] = useState(100);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadFlags();
  }, [addonId]);

  const loadFlags = async () => {
    try {
      setLoading(true);
      const data = await api.listFlags(addonId);
      setFlags(data.flags);
    } catch (err) {
      toast.error('Failed to load feature flags');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!key.trim() || !name.trim()) {
      toast.error('Key and name are required');
      return;
    }
    try {
      setCreating(true);
      const data: FeatureFlagCreate = {
        key: key.trim(),
        name: name.trim(),
        description: description.trim() || undefined,
        enabled: false,
        percentage,
      };
      await api.createFlag(addonId, data);
      toast.success('Feature flag created');
      setShowCreate(false);
      setKey('');
      setName('');
      setDescription('');
      setPercentage(100);
      await loadFlags();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create flag');
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (flag: FeatureFlag) => {
    try {
      await api.updateFlag(addonId, flag.id, { enabled: !flag.enabled });
      toast.success(`Flag ${flag.enabled ? 'disabled' : 'enabled'}`);
      await loadFlags();
    } catch (err) {
      toast.error('Failed to update flag');
    }
  };

  const handleDelete = async (flagId: number) => {
    if (!confirm('Delete this feature flag?')) return;
    try {
      await api.deleteFlag(addonId, flagId);
      toast.success('Flag deleted');
      await loadFlags();
    } catch (err) {
      toast.error('Failed to delete flag');
    }
  };

  const handlePercentageChange = async (flag: FeatureFlag, newPercent: number) => {
    try {
      await api.updateFlag(addonId, flag.id, { percentage: newPercent });
      toast.success('Percentage updated');
      await loadFlags();
    } catch (err) {
      toast.error('Failed to update percentage');
    }
  };

  if (loading) return <div className="flag-manager"><p>Loading feature flags...</p></div>;

  return (
    <div className="flag-manager">
      <div className="flag-header">
        <h3>Feature Flags</h3>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ New Flag'}
        </button>
      </div>

      {showCreate && (
        <div className="flag-create-form">
          <div className="form-group">
            <label>Key (unique identifier)</label>
            <input
              type="text"
              placeholder="e.g. new-dashboard"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              pattern="^[a-zA-Z0-9_.\-]+$"
            />
          </div>
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              placeholder="e.g. New Dashboard UI"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Description (optional)</label>
            <textarea
              placeholder="What does this flag control?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>
          <div className="form-group">
            <label>Rollout Percentage: {percentage}%</label>
            <input
              type="range"
              min={0}
              max={100}
              value={percentage}
              onChange={(e) => setPercentage(Number(e.target.value))}
            />
          </div>
          <button className="btn btn-primary btn-sm" onClick={handleCreate} disabled={creating}>
            {creating ? 'Creating...' : 'Create Flag'}
          </button>
        </div>
      )}

      {flags.length === 0 ? (
        <p className="no-flags">No feature flags. Create one to toggle features without redeploying.</p>
      ) : (
        <div className="flags-list">
          {flags.map((flag) => (
            <div key={flag.id} className="flag-card">
              <div className="flag-card-header">
                <div className="flag-info">
                  <span className="flag-key">{flag.key}</span>
                  <span className="flag-name">{flag.name}</span>
                </div>
                <div className="flag-toggle-container">
                  <button
                    className={`flag-toggle ${flag.enabled ? 'flag-toggle-on' : 'flag-toggle-off'}`}
                    onClick={() => handleToggle(flag)}
                    title={flag.enabled ? 'Disable' : 'Enable'}
                  >
                    {flag.enabled ? 'ON' : 'OFF'}
                  </button>
                </div>
              </div>
              {flag.description && <p className="flag-description">{flag.description}</p>}
              <div className="flag-meta">
                <span>Rollout: {flag.percentage}%</span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={flag.percentage}
                  onChange={(e) => handlePercentageChange(flag, Number(e.target.value))}
                  className="flag-percentage-slider"
                />
                <span className="flag-date">
                  Created {new Date(flag.created_at).toLocaleDateString()}
                </span>
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(flag.id)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

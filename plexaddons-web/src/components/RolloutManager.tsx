import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type { StagedRollout, StagedRolloutCreate, Version } from '../types';
import './RolloutManager.css';

const STAGE_LABELS: Record<string, string> = {
  canary: 'Canary (1%)',
  early: 'Early (5%)',
  partial: 'Partial (25%)',
  majority: 'Majority (50%)',
  full: 'Full (100%)',
  paused: 'Paused',
};

const STATUS_COLORS: Record<string, string> = {
  draft: '#6b7280',
  active: '#10b981',
  paused: '#f59e0b',
  completed: '#3b82f6',
  cancelled: '#ef4444',
};

interface Props {
  addonId: number;
  versions: Version[];
}

export default function RolloutManager({ addonId, versions }: Props) {
  const [rollouts, setRollouts] = useState<StagedRollout[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<number>(0);
  const [autoPromote, setAutoPromote] = useState(false);
  const [autoPromoteHours, setAutoPromoteHours] = useState(24);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadRollouts();
  }, [addonId]);

  const loadRollouts = async () => {
    try {
      setLoading(true);
      const data = await api.listRollouts(addonId);
      setRollouts(data.rollouts);
    } catch (err) {
      toast.error('Failed to load rollouts');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!selectedVersion) {
      toast.error('Select a version');
      return;
    }
    try {
      setCreating(true);
      const data: StagedRolloutCreate = {
        version_id: selectedVersion,
        auto_promote: autoPromote,
        auto_promote_after_hours: autoPromoteHours,
      };
      await api.createRollout(addonId, data);
      toast.success('Rollout created');
      setShowCreate(false);
      setSelectedVersion(0);
      setAutoPromote(false);
      setAutoPromoteHours(24);
      await loadRollouts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create rollout');
    } finally {
      setCreating(false);
    }
  };

  const handleActivate = async (rolloutId: number) => {
    try {
      await api.activateRollout(addonId, rolloutId);
      toast.success('Rollout activated');
      await loadRollouts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to activate');
    }
  };

  const handlePromote = async (rolloutId: number) => {
    try {
      await api.promoteRollout(addonId, rolloutId);
      toast.success('Rollout promoted');
      await loadRollouts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to promote');
    }
  };

  const handlePause = async (rolloutId: number) => {
    try {
      await api.pauseRollout(addonId, rolloutId);
      toast.success('Rollout paused');
      await loadRollouts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to pause');
    }
  };

  const handleCancel = async (rolloutId: number) => {
    if (!confirm('Cancel this rollout? This cannot be undone.')) return;
    try {
      await api.cancelRollout(addonId, rolloutId);
      toast.success('Rollout cancelled');
      await loadRollouts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to cancel');
    }
  };

  if (loading) return <div className="rollout-manager"><p>Loading rollouts...</p></div>;

  return (
    <div className="rollout-manager">
      <div className="rollout-header">
        <h3>Staged Rollouts</h3>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ New Rollout'}
        </button>
      </div>

      {showCreate && (
        <div className="rollout-create-form">
          <div className="form-group">
            <label>Version</label>
            <select value={selectedVersion} onChange={(e) => setSelectedVersion(Number(e.target.value))}>
              <option value={0}>Select a version...</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>v{v.version}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>
              <input type="checkbox" checked={autoPromote} onChange={(e) => setAutoPromote(e.target.checked)} />
              {' '}Auto-promote (advance stage if no errors)
            </label>
          </div>
          {autoPromote && (
            <div className="form-group">
              <label>Hours before auto-promote</label>
              <input
                type="number"
                min={1}
                max={720}
                value={autoPromoteHours}
                onChange={(e) => setAutoPromoteHours(Number(e.target.value))}
              />
            </div>
          )}
          <button className="btn btn-primary btn-sm" onClick={handleCreate} disabled={creating}>
            {creating ? 'Creating...' : 'Create Rollout'}
          </button>
        </div>
      )}

      {rollouts.length === 0 ? (
        <p className="no-rollouts">No rollouts yet. Create one to gradually roll out a version.</p>
      ) : (
        <div className="rollouts-list">
          {rollouts.map((r) => (
            <div key={r.id} className="rollout-card">
              <div className="rollout-card-header">
                <span className="rollout-version">Version #{r.version_id}</span>
                <span className="rollout-status" style={{ backgroundColor: STATUS_COLORS[r.status] }}>
                  {r.status}
                </span>
              </div>

              <div className="rollout-progress">
                <div className="rollout-progress-bar">
                  <div className="rollout-progress-fill" style={{ width: `${r.percentage}%` }} />
                </div>
                <span className="rollout-percentage">{r.percentage}%</span>
              </div>

              <div className="rollout-details">
                <span>Stage: {STAGE_LABELS[r.stage] || r.stage}</span>
                <span>Checks: {r.total_checks} | Errors: {r.error_reports}</span>
                {r.auto_promote && <span>Auto-promote: {r.auto_promote_after_hours}h</span>}
              </div>

              {r.events.length > 0 && (
                <div className="rollout-events">
                  <strong>History:</strong>
                  {r.events.map((ev) => (
                    <div key={ev.id} className="rollout-event">
                      {ev.from_stage ? `${ev.from_stage} → ${ev.to_stage}` : `Started at ${ev.to_stage}`}
                      {' '}({ev.from_percentage ?? 0}% → {ev.to_percentage}%)
                      <span className="rollout-event-time">
                        {new Date(ev.created_at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="rollout-actions">
                {r.status === 'draft' && (
                  <button className="btn btn-sm btn-primary" onClick={() => handleActivate(r.id)}>
                    Activate
                  </button>
                )}
                {r.status === 'active' && r.stage !== 'full' && (
                  <button className="btn btn-sm btn-primary" onClick={() => handlePromote(r.id)}>
                    Promote
                  </button>
                )}
                {r.status === 'active' && (
                  <button className="btn btn-sm btn-secondary" onClick={() => handlePause(r.id)}>
                    Pause
                  </button>
                )}
                {(r.status === 'draft' || r.status === 'active' || r.status === 'paused') && (
                  <button className="btn btn-sm btn-danger" onClick={() => handleCancel(r.id)}>
                    Cancel
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

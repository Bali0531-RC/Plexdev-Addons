import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Collaborator, CollaboratorRole } from '../types';
import './Collaborators.css';

interface CollaboratorsManagerProps {
  addonId: number;
  isOwner: boolean;
}

export default function CollaboratorsManager({ addonId, isOwner }: CollaboratorsManagerProps) {
  const { user } = useAuth();
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteUserId, setInviteUserId] = useState('');
  const [inviteRole, setInviteRole] = useState<CollaboratorRole>('editor');
  const [inviting, setInviting] = useState(false);

  const isPro = user?.subscription_tier === 'pro' || user?.subscription_tier === 'premium';

  useEffect(() => {
    loadCollaborators();
  }, [addonId]);

  const loadCollaborators = async () => {
    try {
      setLoading(true);
      const data = await api.listCollaborators(addonId);
      setCollaborators(data);
    } catch {
      // May not have access
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async () => {
    const userId = parseInt(inviteUserId);
    if (!userId || isNaN(userId)) {
      toast.error('Please enter a valid user ID');
      return;
    }
    try {
      setInviting(true);
      await api.inviteCollaborator(addonId, userId, inviteRole);
      toast.success('Invitation sent');
      setInviteUserId('');
      loadCollaborators();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to invite');
    } finally {
      setInviting(false);
    }
  };

  const handleUpdateRole = async (collaboratorId: number, role: CollaboratorRole) => {
    try {
      await api.updateCollaborator(addonId, collaboratorId, role);
      toast.success('Role updated');
      loadCollaborators();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update role');
    }
  };

  const handleRemove = async (collaboratorId: number) => {
    if (!confirm('Remove this collaborator?')) return;
    try {
      await api.removeCollaborator(addonId, collaboratorId);
      toast.success('Collaborator removed');
      loadCollaborators();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to remove');
    }
  };

  if (!isPro) {
    return (
      <div className="collaborators-section">
        <h3>Collaborators</h3>
        <p className="pro-hint">Upgrade to Pro to invite collaborators to manage your addons.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="collaborators-section">
        <h3>Collaborators</h3>
        <p className="loading-text">Loading...</p>
      </div>
    );
  }

  return (
    <div className="collaborators-section">
      <h3>Collaborators</h3>

      {/* Invite form (owner only) */}
      {isOwner && (
        <div className="invite-form">
          <input
            type="number"
            placeholder="User ID"
            value={inviteUserId}
            onChange={(e) => setInviteUserId(e.target.value)}
            className="invite-input"
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as CollaboratorRole)}
            className="invite-select"
          >
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
            <option value="viewer">Viewer</option>
          </select>
          <button
            onClick={handleInvite}
            disabled={inviting || !inviteUserId}
            className="btn btn-sm btn-primary"
          >
            {inviting ? 'Inviting...' : 'Invite'}
          </button>
        </div>
      )}

      {/* Collaborators list */}
      {collaborators.length > 0 ? (
        <div className="collaborators-list">
          {collaborators.map((collab) => (
            <div key={collab.id} className="collaborator-item">
              <div className="collab-info">
                {collab.avatar && (
                  <img src={collab.avatar} alt="" className="collab-avatar" />
                )}
                <div className="collab-details">
                  <span className="collab-name">
                    {collab.display_name || collab.username || `User #${collab.user_id}`}
                  </span>
                  <span className={`collab-status ${collab.accepted ? 'accepted' : 'pending'}`}>
                    {collab.accepted ? collab.role : 'Pending invitation'}
                  </span>
                </div>
              </div>
              {isOwner && (
                <div className="collab-actions">
                  <select
                    value={collab.role}
                    onChange={(e) => handleUpdateRole(collab.id, e.target.value as CollaboratorRole)}
                    className="role-select"
                  >
                    <option value="editor">Editor</option>
                    <option value="admin">Admin</option>
                    <option value="viewer">Viewer</option>
                  </select>
                  <button
                    onClick={() => handleRemove(collab.id)}
                    className="btn btn-sm btn-danger"
                    title="Remove collaborator"
                  >
                    Remove
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="no-collaborators">No collaborators yet. Invite users to help manage this addon.</p>
      )}
    </div>
  );
}

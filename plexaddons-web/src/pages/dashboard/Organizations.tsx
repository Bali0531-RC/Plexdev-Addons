import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import type { Organization, OrganizationDetail, OrganizationRole } from '../../types';
import './Organizations.css';

export default function Organizations() {
  const { user } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<OrganizationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);

  // Form state
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgDescription, setNewOrgDescription] = useState('');
  const [inviteUsername, setInviteUsername] = useState('');
  const [inviteRole, setInviteRole] = useState<OrganizationRole>('member');
  const [saving, setSaving] = useState(false);

  const effectiveTier = user?.effective_tier || user?.subscription_tier || 'free';
  const canCreateOrgs = effectiveTier === 'premium';

  useEffect(() => {
    loadOrganizations();
  }, []);

  const loadOrganizations = async () => {
    try {
      setLoading(true);
      const response = await api.listMyOrganizations();
      setOrganizations(response.organizations);
    } catch (err) {
      console.error('Failed to load organizations:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadOrgDetails = async (orgSlug: string) => {
    try {
      const org = await api.getOrganization(orgSlug);
      setSelectedOrg(org);
    } catch (err) {
      console.error('Failed to load organization:', err);
      toast.error('Failed to load organization details');
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName.trim()) return;

    setSaving(true);
    try {
      const org = await api.createOrganization({
        name: newOrgName,
        description: newOrgDescription || undefined,
      });
      setOrganizations(prev => [...prev, org]);
      setShowCreateModal(false);
      setNewOrgName('');
      setNewOrgDescription('');
      toast.success('Organization created!');
    } catch (err: any) {
      toast.error(err.message || 'Failed to create organization');
    } finally {
      setSaving(false);
    }
  };

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteUsername.trim() || !selectedOrg) return;

    setSaving(true);
    try {
      await api.inviteOrganizationMember(selectedOrg.slug, inviteUsername, inviteRole);
      await loadOrgDetails(selectedOrg.slug);
      setShowInviteModal(false);
      setInviteUsername('');
      setInviteRole('member');
      toast.success('Member invited!');
    } catch (err: any) {
      toast.error(err.message || 'Failed to invite member');
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveMember = async (userId: number) => {
    if (!selectedOrg || !confirm('Remove this member from the organization?')) return;

    try {
      await api.removeOrganizationMember(selectedOrg.slug, userId);
      await loadOrgDetails(selectedOrg.slug);
      toast.success('Member removed');
    } catch (err: any) {
      toast.error(err.message || 'Failed to remove member');
    }
  };

  const handleUpdateMemberRole = async (userId: number, newRole: OrganizationRole) => {
    if (!selectedOrg) return;

    try {
      await api.updateOrganizationMemberRole(selectedOrg.slug, userId, newRole);
      await loadOrgDetails(selectedOrg.slug);
      toast.success('Role updated');
    } catch (err: any) {
      toast.error(err.message || 'Failed to update role');
    }
  };

  const handleDeleteOrg = async () => {
    if (!selectedOrg || !confirm('Delete this organization? This cannot be undone.')) return;

    try {
      await api.deleteOrganization(selectedOrg.slug);
      setOrganizations(prev => prev.filter(o => o.id !== selectedOrg.id));
      setSelectedOrg(null);
      toast.success('Organization deleted');
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete organization');
    }
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  if (!canCreateOrgs && organizations.length === 0) {
    return (
      <div className="organizations-page">
        <h1>Team Organizations</h1>
        <div className="premium-gate">
          <div className="gate-icon">👥</div>
          <h2>Premium Feature</h2>
          <p>
            Team organizations allow you to collaborate with others on addons.
            Members share your storage quota and can manage addons together.
          </p>
          <Link to="/pricing" className="btn btn-primary">
            Upgrade to Premium
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="organizations-page">
      <div className="page-header">
        <h1>Team Organizations</h1>
        {canCreateOrgs && (
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            + Create Organization
          </button>
        )}
      </div>

      <div className="orgs-layout">
        <div className="orgs-list">
          {organizations.length === 0 ? (
            <div className="no-orgs">
              <p>No organizations yet</p>
              <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                Create your first organization
              </button>
            </div>
          ) : (
            organizations.map(org => (
              <div
                key={org.id}
                className={`org-card ${selectedOrg?.slug === org.slug ? 'selected' : ''}`}
                onClick={() => loadOrgDetails(org.slug)}
              >
                <div className="org-avatar">
                  {org.avatar_url ? (
                    <img src={org.avatar_url} alt={org.name} />
                  ) : (
                    <span>{org.name.charAt(0).toUpperCase()}</span>
                  )}
                </div>
                <div className="org-info">
                  <h3>{org.name}</h3>
                  <span className="org-stats">
                    {org.member_count} members · {org.addon_count} addons
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {selectedOrg && (
          <div className="org-details">
            <div className="org-details-header">
              <div className="org-details-avatar">
                {selectedOrg.avatar_url ? (
                  <img src={selectedOrg.avatar_url} alt={selectedOrg.name} />
                ) : (
                  <span>{selectedOrg.name.charAt(0).toUpperCase()}</span>
                )}
              </div>
              <div className="org-details-info">
                <h2>{selectedOrg.name}</h2>
                {selectedOrg.description && <p>{selectedOrg.description}</p>}
                <span className="org-owner">Owner: {selectedOrg.owner_username}</span>
              </div>
            </div>

            <div className="org-members">
              <div className="members-header">
                <h3>Members ({selectedOrg.members.length})</h3>
                {selectedOrg.owner_id === user?.id && (
                  <button className="btn btn-sm btn-primary" onClick={() => setShowInviteModal(true)}>
                    + Invite
                  </button>
                )}
              </div>

              <div className="members-list">
                {selectedOrg.members.map(member => (
                  <div key={member.id} className="member-row">
                    <div className="member-avatar">
                      {member.discord_avatar ? (
                        <img
                          src={`https://cdn.discordapp.com/avatars/${member.user_id}/${member.discord_avatar}.png`}
                          alt={member.discord_username || ''}
                        />
                      ) : (
                        <span>{(member.discord_username || '?').charAt(0).toUpperCase()}</span>
                      )}
                    </div>
                    <div className="member-info">
                      <span className="member-name">{member.discord_username || 'Unknown'}</span>
                      <span className={`member-role role-${member.role}`}>
                        {member.role}
                      </span>
                    </div>
                    {selectedOrg.owner_id === user?.id && member.role !== 'owner' && (
                      <div className="member-actions">
                        <select
                          value={member.role}
                          onChange={(e) => handleUpdateMemberRole(member.user_id, e.target.value as OrganizationRole)}
                        >
                          <option value="member">Member</option>
                          <option value="admin">Admin</option>
                        </select>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleRemoveMember(member.user_id)}
                        >
                          Remove
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {selectedOrg.owner_id === user?.id && (
              <div className="org-danger-zone">
                <h3>Danger Zone</h3>
                <button className="btn btn-danger" onClick={handleDeleteOrg}>
                  Delete Organization
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => !saving && setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Create Organization</h3>
            <form onSubmit={handleCreateOrg}>
              <div className="form-group">
                <label htmlFor="orgName">Name *</label>
                <input
                  type="text"
                  id="orgName"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  required
                  placeholder="My Team"
                />
              </div>
              <div className="form-group">
                <label htmlFor="orgDesc">Description</label>
                <textarea
                  id="orgDesc"
                  value={newOrgDescription}
                  onChange={(e) => setNewOrgDescription(e.target.value)}
                  placeholder="What does this organization do?"
                  rows={3}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)} disabled={saving}>
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

      {/* Invite Member Modal */}
      {showInviteModal && (
        <div className="modal-overlay" onClick={() => !saving && setShowInviteModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Invite Member</h3>
            <form onSubmit={handleInviteMember}>
              <div className="form-group">
                <label htmlFor="inviteUsername">Discord Username *</label>
                <input
                  type="text"
                  id="inviteUsername"
                  value={inviteUsername}
                  onChange={(e) => setInviteUsername(e.target.value)}
                  required
                  placeholder="username"
                />
                <small>The user must have an account on PlexAddons</small>
              </div>
              <div className="form-group">
                <label htmlFor="inviteRole">Role</label>
                <select
                  id="inviteRole"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as OrganizationRole)}
                >
                  <option value="member">Member - Can view and create addons</option>
                  <option value="admin">Admin - Can manage members and addons</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowInviteModal(false)} disabled={saving}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Inviting...' : 'Invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

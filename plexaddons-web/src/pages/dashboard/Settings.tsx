import { useState, FormEvent } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { toast } from 'sonner';
import './Settings.css';

export default function Settings() {
  const { user, setUser, logout } = useAuth();
  const [email, setEmail] = useState(user?.email || '');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Delete account state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deleting, setDeleting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setSaving(true);

    try {
      const updatedUser = await api.updateMe({ email: email || undefined });
      setUser(updatedUser);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Failed to update settings');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE') return;
    
    setDeleting(true);
    try {
      await api.deleteMyAccount();
      toast.success('Account deleted successfully. Goodbye!');
      // Wait a moment for the user to see the message
      setTimeout(() => {
        logout();
      }, 1500);
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete account');
      setDeleting(false);
    }
  };

  return (
    <div className="settings-page">
      <h1>Settings</h1>

      <div className="settings-card">
        <h2>Account Information</h2>
        <div className="account-info">
          <div className="info-item">
            <label>Discord Username</label>
            <span>{user?.discord_username}</span>
          </div>
          <div className="info-item">
            <label>Discord ID</label>
            <span className="mono">{user?.discord_id}</span>
          </div>
          <div className="info-item">
            <label>Account Created</label>
            <span>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</span>
          </div>
          <div className="info-item">
            <label>Subscription Tier</label>
            <span className="tier-badge">{user?.subscription_tier?.toUpperCase()}</span>
          </div>
        </div>
      </div>

      <div className="settings-card">
        <h2>Email Settings</h2>
        
        {success && (
          <div className="success-message">
            Settings saved successfully!
          </div>
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
            />
            <small>Used for important account notifications</small>
          </div>

          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>

      <div className="settings-card danger-zone">
        <h2>Danger Zone</h2>
        <p>These actions are irreversible. Please be careful.</p>
        
        {!showDeleteConfirm ? (
          <button 
            className="btn btn-danger" 
            onClick={() => setShowDeleteConfirm(true)}
          >
            Delete Account
          </button>
        ) : (
          <div className="delete-confirm-container">
            <p className="delete-warning">
              ⚠️ This will permanently delete your account, all your addons, versions, 
              tickets, and cancel any active subscriptions. This action cannot be undone.
            </p>
            <div className="delete-confirm-input">
              <label>Type <strong>DELETE</strong> to confirm:</label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="DELETE"
                disabled={deleting}
              />
            </div>
            <div className="delete-actions">
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteConfirmText('');
                }}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="btn btn-danger"
                onClick={handleDeleteAccount}
                disabled={deleteConfirmText !== 'DELETE' || deleting}
              >
                {deleting ? 'Deleting...' : 'Delete My Account'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

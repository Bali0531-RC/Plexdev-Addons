import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type { SigningKey, VulnerabilityScan, SBOMEntry, Version } from '../types';
import './SecurityManager.css';

interface Props {
  addonId: number;
  versions: Version[];
}

export default function SecurityManager({ addonId, versions }: Props) {
  const [activeTab, setActiveTab] = useState<'signing' | 'scanning' | 'sbom'>('signing');

  return (
    <div className="security-manager">
      <h3>Security Suite</h3>
      <div className="security-tabs">
        <button
          className={`security-tab ${activeTab === 'signing' ? 'active' : ''}`}
          onClick={() => setActiveTab('signing')}
        >
          Code Signing
        </button>
        <button
          className={`security-tab ${activeTab === 'scanning' ? 'active' : ''}`}
          onClick={() => setActiveTab('scanning')}
        >
          Vulnerability Scans
        </button>
        <button
          className={`security-tab ${activeTab === 'sbom' ? 'active' : ''}`}
          onClick={() => setActiveTab('sbom')}
        >
          SBOM
        </button>
      </div>

      {activeTab === 'signing' && <SigningPanel addonId={addonId} />}
      {activeTab === 'scanning' && <ScanningPanel versions={versions} />}
      {activeTab === 'sbom' && <SBOMPanel versions={versions} />}
    </div>
  );
}

// ============== Code Signing Panel ==============

function SigningPanel({ addonId }: { addonId: number }) {
  const [keys, setKeys] = useState<SigningKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [publicKey, setPublicKey] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => { loadKeys(); }, [addonId]);

  const loadKeys = async () => {
    try {
      setLoading(true);
      const data = await api.listSigningKeys(addonId);
      setKeys(data.keys);
    } catch { toast.error('Failed to load signing keys'); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    if (!name.trim() || !publicKey.trim()) {
      toast.error('Name and public key are required');
      return;
    }
    try {
      setCreating(true);
      await api.createSigningKey(addonId, { name: name.trim(), public_key: publicKey.trim() });
      toast.success('Signing key created');
      setShowCreate(false);
      setName('');
      setPublicKey('');
      await loadKeys();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create key');
    } finally { setCreating(false); }
  };

  const handleRevoke = async (keyId: number) => {
    if (!confirm('Revoke this signing key? Existing signatures will remain but key cannot be used again.')) return;
    try {
      await api.revokeSigningKey(addonId, keyId);
      toast.success('Key revoked');
      await loadKeys();
    } catch { toast.error('Failed to revoke key'); }
  };

  if (loading) return <p>Loading signing keys...</p>;

  return (
    <div className="security-panel">
      <div className="panel-header">
        <span>{keys.length} signing key(s)</span>
        <button className="btn btn-sm btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ Add Key'}
        </button>
      </div>

      {showCreate && (
        <div className="create-form">
          <div className="form-group">
            <label>Key Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Production Key" />
          </div>
          <div className="form-group">
            <label>Public Key (Ed25519)</label>
            <textarea rows={4} value={publicKey} onChange={(e) => setPublicKey(e.target.value)} placeholder="Paste your public key..." />
          </div>
          <button className="btn btn-sm btn-primary" onClick={handleCreate} disabled={creating}>
            {creating ? 'Creating...' : 'Create Key'}
          </button>
        </div>
      )}

      {keys.length === 0 ? (
        <p className="empty-state">No signing keys. Add one to sign your addon versions.</p>
      ) : (
        <div className="items-list">
          {keys.map((key) => (
            <div key={key.id} className="security-item">
              <div className="item-header">
                <span className="item-name">{key.name}</span>
                <span className={`status-badge ${key.is_active ? 'active' : 'revoked'}`}>
                  {key.is_active ? 'Active' : 'Revoked'}
                </span>
              </div>
              <div className="item-meta">
                <span>Algorithm: {key.algorithm}</span>
                <span>Fingerprint: {key.key_fingerprint.substring(0, 16)}...</span>
                <span>{new Date(key.created_at).toLocaleDateString()}</span>
              </div>
              {key.is_active && (
                <button className="btn btn-sm btn-danger" onClick={() => handleRevoke(key.id)}>Revoke</button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============== Vulnerability Scanning Panel ==============

function ScanningPanel({ versions }: { versions: Version[] }) {
  const [selectedVersion, setSelectedVersion] = useState<number>(0);
  const [scans, setScans] = useState<VulnerabilityScan[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);

  const loadScans = async (versionId: number) => {
    try {
      setLoading(true);
      const data = await api.listScans(versionId);
      setScans(data.scans);
    } catch { toast.error('Failed to load scans'); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (selectedVersion) loadScans(selectedVersion);
    else setScans([]);
  }, [selectedVersion]);

  const handleScan = async () => {
    if (!selectedVersion) { toast.error('Select a version'); return; }
    try {
      setScanning(true);
      await api.initiateScan(selectedVersion);
      toast.success('Scan initiated');
      await loadScans(selectedVersion);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to start scan');
    } finally { setScanning(false); }
  };

  const severityColor = (count: number, level: string) => {
    if (count === 0) return '';
    const colors: Record<string, string> = { critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#3b82f6' };
    return colors[level] || '';
  };

  return (
    <div className="security-panel">
      <div className="panel-header">
        <select value={selectedVersion} onChange={(e) => setSelectedVersion(Number(e.target.value))}>
          <option value={0}>Select version...</option>
          {versions.map((v) => <option key={v.id} value={v.id}>v{v.version}</option>)}
        </select>
        <button className="btn btn-sm btn-primary" onClick={handleScan} disabled={scanning || !selectedVersion}>
          {scanning ? 'Scanning...' : 'Scan Now'}
        </button>
      </div>

      {loading ? <p>Loading scans...</p> : scans.length === 0 ? (
        <p className="empty-state">No scans yet. Select a version and click "Scan Now".</p>
      ) : (
        <div className="items-list">
          {scans.map((scan) => (
            <div key={scan.id} className="security-item">
              <div className="item-header">
                <span className={`status-badge ${scan.status}`}>{scan.status}</span>
                <span>{scan.total_vulnerabilities} vulnerabilities</span>
              </div>
              {scan.status === 'completed' && (
                <div className="vuln-counts">
                  {scan.critical_count > 0 && <span style={{ color: severityColor(scan.critical_count, 'critical') }}>Critical: {scan.critical_count}</span>}
                  {scan.high_count > 0 && <span style={{ color: severityColor(scan.high_count, 'high') }}>High: {scan.high_count}</span>}
                  {scan.medium_count > 0 && <span style={{ color: severityColor(scan.medium_count, 'medium') }}>Medium: {scan.medium_count}</span>}
                  {scan.low_count > 0 && <span style={{ color: severityColor(scan.low_count, 'low') }}>Low: {scan.low_count}</span>}
                  {scan.total_vulnerabilities === 0 && <span className="no-vulns">No vulnerabilities found</span>}
                </div>
              )}
              {scan.error_message && <p className="scan-error">{scan.error_message}</p>}
              <span className="item-date">{new Date(scan.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============== SBOM Panel ==============

function SBOMPanel({ versions }: { versions: Version[] }) {
  const [selectedVersion, setSelectedVersion] = useState<number>(0);
  const [sboms, setSboms] = useState<SBOMEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [format, setFormat] = useState('npm');
  const [content, setContent] = useState('');
  const [uploading, setUploading] = useState(false);

  const loadSBOMs = async (versionId: number) => {
    try {
      setLoading(true);
      const data = await api.listSBOMs(versionId);
      setSboms(data.sboms);
    } catch { toast.error('Failed to load SBOMs'); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (selectedVersion) loadSBOMs(selectedVersion);
    else setSboms([]);
  }, [selectedVersion]);

  const handleUpload = async () => {
    if (!selectedVersion || !content.trim()) {
      toast.error('Select a version and provide lockfile content');
      return;
    }
    try {
      setUploading(true);
      await api.uploadSBOM(selectedVersion, { format, raw_content: content });
      toast.success('SBOM uploaded and parsed');
      setShowUpload(false);
      setContent('');
      await loadSBOMs(selectedVersion);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to upload SBOM');
    } finally { setUploading(false); }
  };

  return (
    <div className="security-panel">
      <div className="panel-header">
        <select value={selectedVersion} onChange={(e) => setSelectedVersion(Number(e.target.value))}>
          <option value={0}>Select version...</option>
          {versions.map((v) => <option key={v.id} value={v.id}>v{v.version}</option>)}
        </select>
        {selectedVersion > 0 && (
          <button className="btn btn-sm btn-primary" onClick={() => setShowUpload(!showUpload)}>
            {showUpload ? 'Cancel' : '+ Upload SBOM'}
          </button>
        )}
      </div>

      {showUpload && (
        <div className="create-form">
          <div className="form-group">
            <label>Format</label>
            <select value={format} onChange={(e) => setFormat(e.target.value)}>
              <option value="npm">npm (package-lock.json)</option>
              <option value="pip">pip (requirements.txt)</option>
              <option value="maven">Maven</option>
              <option value="gradle">Gradle</option>
              <option value="cargo">Cargo</option>
              <option value="go">Go</option>
            </select>
          </div>
          <div className="form-group">
            <label>Lockfile Content</label>
            <textarea rows={6} value={content} onChange={(e) => setContent(e.target.value)} placeholder="Paste your lockfile content..." />
          </div>
          <button className="btn btn-sm btn-primary" onClick={handleUpload} disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload & Parse'}
          </button>
        </div>
      )}

      {loading ? <p>Loading SBOMs...</p> : sboms.length === 0 ? (
        <p className="empty-state">No SBOMs uploaded. Upload a lockfile to track dependencies.</p>
      ) : (
        <div className="items-list">
          {sboms.map((sbom) => (
            <div key={sbom.id} className="security-item">
              <div className="item-header">
                <span className="item-name">{sbom.format} SBOM</span>
                <span>{sbom.total_dependencies} deps ({sbom.direct_dependencies} direct)</span>
              </div>
              {sbom.dependencies && sbom.dependencies.length > 0 && (
                <div className="deps-preview">
                  {sbom.dependencies.slice(0, 5).map((dep, i) => (
                    <span key={i} className="dep-badge">
                      {dep.name}@{dep.version}
                    </span>
                  ))}
                  {sbom.dependencies.length > 5 && (
                    <span className="dep-more">+{sbom.dependencies.length - 5} more</span>
                  )}
                </div>
              )}
              <span className="item-date">{new Date(sbom.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

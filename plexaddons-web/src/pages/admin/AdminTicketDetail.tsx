import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../../services/api';
import type { TicketDetail as TicketDetailType, TicketMessage, TicketStatus, CannedResponse } from '../../types';
import Spinner from '../../components/Spinner';
import './AdminTickets.css';

const STATUS_COLORS: Record<TicketStatus, string> = {
  open: '#28a745',
  in_progress: '#17a2b8',
  resolved: '#6c757d',
  closed: '#dc3545',
};

const STATUS_LABELS: Record<TicketStatus, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  closed: 'Closed',
};

const PRIORITY_COLORS: Record<string, string> = {
  low: '#6c757d',
  normal: '#17a2b8',
  high: '#e9a426',
  urgent: '#dc3545',
};

export default function AdminTicketDetail() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [ticket, setTicket] = useState<TicketDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);

  const [showStatusMenu, setShowStatusMenu] = useState(false);
  const [showPriorityMenu, setShowPriorityMenu] = useState(false);
  const [showCannedResponses, setShowCannedResponses] = useState(false);
  const [cannedResponses, setCannedResponses] = useState<CannedResponse[]>([]);

  useEffect(() => {
    if (ticketId) {
      loadTicket();
      loadCannedResponses();
    }
  }, [ticketId]);

  useEffect(() => {
    scrollToBottom();
  }, [ticket?.messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadTicket = async () => {
    try {
      setLoading(true);
      const data = await api.adminGetTicket(Number(ticketId));
      setTicket(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load ticket');
    } finally {
      setLoading(false);
    }
  };

  const loadCannedResponses = async () => {
    try {
      const data = await api.listCannedResponses();
      setCannedResponses(data.responses || []);
    } catch (err) {
      console.error('Failed to load canned responses:', err);
    }
  };

  const handleSendReply = async () => {
    if (!reply.trim() || !ticket) return;

    try {
      setSending(true);
      await api.adminAddTicketMessage(ticket.id, reply);
      setReply('');
      await loadTicket();
    } catch (err: any) {
      alert(err.message || 'Failed to send reply');
    } finally {
      setSending(false);
    }
  };

  const handleStatusChange = async (status: TicketStatus) => {
    if (!ticket) return;
    try {
      await api.updateTicketStatus(ticket.id, status);
      await loadTicket();
      setShowStatusMenu(false);
    } catch (err: any) {
      alert(err.message || 'Failed to update status');
    }
  };

  const handlePriorityChange = async (priority: string) => {
    if (!ticket) return;
    try {
      await api.updateTicketPriority(ticket.id, priority as any);
      await loadTicket();
      setShowPriorityMenu(false);
    } catch (err: any) {
      alert(err.message || 'Failed to update priority');
    }
  };

  const handleAssignToMe = async () => {
    if (!ticket) return;
    try {
      await api.assignTicketToMe(ticket.id);
      await loadTicket();
    } catch (err: any) {
      alert(err.message || 'Failed to assign ticket');
    }
  };

  const handleUseCannedResponse = (response: CannedResponse) => {
    setReply(response.content);
    setShowCannedResponses(false);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleDownloadAttachment = async (attachmentId: number, filename: string) => {
    try {
      const blob = await api.downloadAttachment(Number(ticketId), attachmentId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || 'Failed to download attachment');
    }
  };

  if (loading) {
    return (
      <div className="admin-ticket-detail">
        <div className="loading-state">
          <Spinner size={40} />
        </div>
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="admin-ticket-detail">
        <div className="error-state">
          <h2>Error</h2>
          <p>{error || 'Ticket not found'}</p>
          <Link to="/admin/tickets" className="btn btn-primary">
            Back to Tickets
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-ticket-detail">
      <Link to="/admin/tickets" className="back-link">
        ← Back to Tickets
      </Link>

      {/* Header Section */}
      <div className="admin-ticket-header">
        <div className="admin-ticket-title">
          <div>
            <span className="ticket-id">#{ticket.id}</span>
            <h1>{ticket.subject}</h1>
          </div>
          <div className="admin-ticket-badges">
            {/* Status Dropdown */}
            <div className="dropdown">
              <button
                className="status-badge"
                style={{ backgroundColor: STATUS_COLORS[ticket.status], cursor: 'pointer' }}
                onClick={() => setShowStatusMenu(!showStatusMenu)}
              >
                {STATUS_LABELS[ticket.status]} ▼
              </button>
              {showStatusMenu && (
                <div className="dropdown-menu">
                  {Object.entries(STATUS_LABELS).map(([value, label]) => (
                    <button
                      key={value}
                      className={`dropdown-item ${ticket.status === value ? 'active' : ''}`}
                      onClick={() => handleStatusChange(value as TicketStatus)}
                    >
                      <span
                        className="status-dot"
                        style={{ backgroundColor: STATUS_COLORS[value as TicketStatus] }}
                      />
                      {label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Priority Dropdown */}
            <div className="dropdown">
              <button
                className="priority-badge"
                style={{ color: PRIORITY_COLORS[ticket.priority], cursor: 'pointer' }}
                onClick={() => setShowPriorityMenu(!showPriorityMenu)}
              >
                {ticket.priority.toUpperCase()} ▼
              </button>
              {showPriorityMenu && (
                <div className="dropdown-menu">
                  {['low', 'normal', 'high', 'urgent'].map((priority) => (
                    <button
                      key={priority}
                      className={`dropdown-item ${ticket.priority === priority ? 'active' : ''}`}
                      onClick={() => handlePriorityChange(priority)}
                    >
                      <span
                        className="priority-dot"
                        style={{ backgroundColor: PRIORITY_COLORS[priority] }}
                      />
                      {priority.toUpperCase()}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="admin-ticket-meta">
          <div className="meta-item">
            <span className="meta-label">User</span>
            <span className="meta-value">
              {ticket.user?.discord_username || 'Unknown'}
              {ticket.user?.subscription_tier && ticket.user.subscription_tier !== 'free' && (
                <span className="user-tier-badge">{ticket.user.subscription_tier}</span>
              )}
            </span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Category</span>
            <span className="meta-value category-badge">
              {ticket.category.replace('_', ' ')}
            </span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Created</span>
            <span className="meta-value">{formatDate(ticket.created_at)}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Updated</span>
            <span className="meta-value">{formatDate(ticket.updated_at)}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Assigned To</span>
            <span className="meta-value">
              {ticket.assigned_to ? (
                ticket.assigned_to.discord_username
              ) : (
                <button className="btn btn-sm btn-secondary" onClick={handleAssignToMe}>
                  Assign to Me
                </button>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* Messages Section */}
      <div className="admin-messages-section">
        <h2>Conversation ({ticket.messages.length} messages)</h2>

        <div className="messages-list">
          {ticket.messages.map((message) => (
            <div
              key={message.id}
              className={`message-card ${message.is_staff_reply ? 'staff-reply' : ''} ${message.is_system_message ? 'system-message' : ''}`}
            >
              <div className="message-header">
                <div className="message-author">
                  <span className="message-author-name">
                    {message.author?.discord_username || (message.is_system_message ? 'System' : 'Unknown')}
                  </span>
                  {message.is_staff_reply && !message.is_system_message && (
                    <span className="message-author-badge">Staff</span>
                  )}
                </div>
                <span className="message-time">{formatDate(message.created_at)}</span>
              </div>
              <div className="message-content">{message.content}</div>

              {message.attachments && message.attachments.length > 0 && (
                <div className="message-attachments">
                  <h4>Attachments:</h4>
                  <div className="attachment-list">
                    {message.attachments.map((attachment) => (
                      <div
                        key={attachment.id}
                        className="attachment-item"
                        onClick={() => handleDownloadAttachment(attachment.id, attachment.original_filename)}
                      >
                        📎 {attachment.original_filename}
                        <span className="attachment-size">{formatBytes(attachment.file_size)}</span>
                        {attachment.is_compressed && <span className="compressed-badge">Compressed</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Reply Form */}
      {ticket.status !== 'closed' && (
        <div className="admin-reply-form">
          <h3>Reply to Ticket</h3>

          <div className="canned-responses-section">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setShowCannedResponses(!showCannedResponses)}
            >
              📝 Canned Responses
            </button>
            {showCannedResponses && cannedResponses.length > 0 && (
              <div className="canned-responses-list">
                {cannedResponses.map((response) => (
                  <button
                    key={response.id}
                    className="canned-response-item"
                    onClick={() => handleUseCannedResponse(response)}
                  >
                    <strong>{response.title}</strong>
                    <span>{response.content.substring(0, 100)}...</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <textarea
            className="reply-textarea"
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            placeholder="Type your reply..."
            disabled={sending}
          />

          <div className="reply-actions">
            <div className="quick-actions">
              <button
                className="btn btn-secondary"
                onClick={() => {
                  handleSendReply();
                  handleStatusChange('resolved');
                }}
                disabled={!reply.trim() || sending}
              >
                Reply & Resolve
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  handleSendReply();
                  handleStatusChange('closed');
                }}
                disabled={!reply.trim() || sending}
              >
                Reply & Close
              </button>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleSendReply}
              disabled={!reply.trim() || sending}
            >
              {sending ? 'Sending...' : 'Send Reply'}
            </button>
          </div>
        </div>
      )}

      {ticket.status === 'closed' && (
        <div className="closed-ticket-notice">
          <p>This ticket is closed. Reopen it to continue the conversation.</p>
          <button
            className="btn btn-primary"
            onClick={() => handleStatusChange('open')}
          >
            Reopen Ticket
          </button>
        </div>
      )}
    </div>
  );
}

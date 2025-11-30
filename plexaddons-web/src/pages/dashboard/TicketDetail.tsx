import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { toast } from 'sonner';
import { api } from '../../services/api';
import type { TicketDetail, TicketAttachment } from '../../types';
import './Support.css';

const statusLabels: Record<string, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  closed: 'Closed',
};

const statusColors: Record<string, string> = {
  open: '#28a745',
  in_progress: '#ffc107',
  resolved: '#17a2b8',
  closed: '#6c757d',
};

const categoryLabels: Record<string, string> = {
  general: 'General',
  billing: 'Billing',
  technical: 'Technical',
  feature_request: 'Feature Request',
  bug_report: 'Bug Report',
};

const priorityLabels: Record<string, string> = {
  low: 'Low',
  normal: 'Normal',
  high: 'High',
  urgent: 'Urgent',
};

const priorityColors: Record<string, string> = {
  low: '#28a745',
  normal: '#ffc107',
  high: '#fd7e14',
  urgent: '#dc3545',
};

export default function TicketDetailPage() {
  const { ticketId } = useParams();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [replyContent, setReplyContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (ticketId) {
      loadTicket();
    }
  }, [ticketId]);

  useEffect(() => {
    scrollToBottom();
  }, [ticket?.messages]);

  const loadTicket = async () => {
    try {
      setLoading(true);
      const data = await api.getTicket(Number(ticketId));
      setTicket(data);
    } catch (err) {
      console.error('Failed to load ticket:', err);
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${bytes} B`;
  };

  const handleSubmitReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyContent.trim() || !ticket) return;

    try {
      setSubmitting(true);
      const message = await api.addTicketMessage(ticket.id, replyContent);
      
      // Upload any selected files
      for (const file of selectedFiles) {
        try {
          await api.uploadTicketAttachment(ticket.id, message.id, file);
        } catch (err) {
          console.error('Failed to upload attachment:', err);
        }
      }

      setReplyContent('');
      setSelectedFiles([]);
      await loadTicket();
    } catch (err) {
      console.error('Failed to submit reply:', err);
      toast.error('Failed to submit reply. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []) as File[];
    const validFiles = files.filter((f) => f.size <= 10 * 1024 * 1024); // 10MB max
    
    if (validFiles.length !== files.length) {
      toast.error('Some files were too large (max 10MB) and were not added.');
    }
    
    setSelectedFiles((prev: File[]) => [...prev, ...validFiles]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev: File[]) => prev.filter((_: File, i: number) => i !== index));
  };

  const handleDownloadAttachment = async (attachment: TicketAttachment) => {
    try {
      const blob = await api.downloadAttachment(ticket!.id, attachment.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = attachment.original_filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download attachment:', err);
      toast.error('Failed to download attachment.');
    }
  };

  const handleCloseTicket = async () => {
    if (!ticket) return;
    
    toast.promise(
      api.closeTicket(ticket.id).then(() => loadTicket()),
      {
        loading: 'Closing ticket...',
        success: 'Ticket closed',
        error: (err: any) => err.message || 'Failed to close ticket',
      }
    );
  };

  const handleReopenTicket = async () => {
    if (!ticket) return;
    
    toast.promise(
      api.reopenTicket(ticket.id).then(() => loadTicket()),
      {
        loading: 'Reopening ticket...',
        success: 'Ticket reopened',
        error: (err: any) => err.message || 'Failed to reopen ticket',
      }
    );
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="ticket-detail">
        <div className="empty-state">
          <h2>Ticket not found</h2>
          <Link to="/dashboard/support" className="btn btn-primary">
            Back to Tickets
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="ticket-detail">
      <Link to="/dashboard/support" className="back-link">
        ← Back to Tickets
      </Link>

      <div className="ticket-detail-header">
        <div className="ticket-detail-title">
          <h1>
            <span className="ticket-id">#{ticket.id}</span>
            {ticket.subject}
          </h1>
          <span 
            className="ticket-status"
            style={{ backgroundColor: statusColors[ticket.status] }}
          >
            {statusLabels[ticket.status]}
          </span>
        </div>

        <div className="ticket-info-grid">
          <div className="ticket-info-item">
            <span className="ticket-info-label">Category</span>
            <span className="ticket-info-value">{categoryLabels[ticket.category]}</span>
          </div>
          <div className="ticket-info-item">
            <span className="ticket-info-label">Priority</span>
            <span className="ticket-info-value" style={{ color: priorityColors[ticket.priority] }}>
              {priorityLabels[ticket.priority]}
            </span>
          </div>
          <div className="ticket-info-item">
            <span className="ticket-info-label">Created</span>
            <span className="ticket-info-value">{formatDate(ticket.created_at)}</span>
          </div>
          {ticket.assigned_admin_username && (
            <div className="ticket-info-item">
              <span className="ticket-info-label">Assigned To</span>
              <span className="ticket-info-value">{ticket.assigned_admin_username}</span>
            </div>
          )}
        </div>

        <div className="ticket-actions">
          {ticket.status !== 'closed' ? (
            <button onClick={handleCloseTicket} className="btn btn-secondary">
              Close Ticket
            </button>
          ) : (
            <button onClick={handleReopenTicket} className="btn btn-secondary">
              Reopen Ticket
            </button>
          )}
        </div>
      </div>

      <div className="messages-section">
        <h2>Conversation</h2>
        <div className="messages-list">
          {ticket.messages.map(message => (
            <div 
              key={message.id}
              className={`message-card ${message.is_staff_reply ? 'staff-reply' : ''} ${message.is_system_message ? 'system-message' : ''}`}
            >
              <div className="message-header">
                <div className="message-author">
                  <span className="message-author-name">
                    {message.author_username || 'System'}
                  </span>
                  {message.is_staff_reply && !message.is_system_message && (
                    <span className="message-author-badge">Staff</span>
                  )}
                </div>
                <span className="message-time">{formatDate(message.created_at)}</span>
              </div>
              <div className="message-content">{message.content}</div>
              
              {message.attachments.length > 0 && (
                <div className="message-attachments">
                  <h4>Attachments</h4>
                  <div className="attachment-list">
                    {message.attachments.map(att => (
                      <div 
                        key={att.id}
                        className="attachment-item"
                        onClick={() => handleDownloadAttachment(att)}
                      >
                        📎 {att.original_filename}
                        <span className="attachment-size">
                          ({formatFileSize(att.file_size)})
                        </span>
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

      {ticket.status !== 'closed' && (
        <form className="reply-form" onSubmit={handleSubmitReply}>
          <h3>Reply</h3>
          <textarea
            className="reply-textarea"
            placeholder="Type your reply..."
            value={replyContent}
            onChange={(e) => setReplyContent(e.target.value)}
            disabled={submitting}
          />
          
          {selectedFiles.length > 0 && (
            <div className="selected-files">
              {selectedFiles.map((file, index) => (
                <div key={index} className="selected-file">
                  {file.name} ({formatFileSize(file.size)})
                  <button type="button" onClick={() => removeFile(index)}>×</button>
                </div>
              ))}
            </div>
          )}

          <div className="reply-actions">
            <label className="file-upload-btn">
              📎 Attach Files
              <input
                type="file"
                multiple
                ref={fileInputRef}
                onChange={handleFileSelect}
              />
            </label>
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={submitting || !replyContent.trim()}
            >
              {submitting ? 'Sending...' : 'Send Reply'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

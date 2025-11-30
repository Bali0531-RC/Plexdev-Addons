import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import type { Ticket, TicketStatus } from '../../types';
import './Support.css';

const statusLabels: Record<TicketStatus, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  closed: 'Closed',
};

const statusColors: Record<TicketStatus, string> = {
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

export default function Support() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<TicketStatus | ''>('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 10;

  useEffect(() => {
    loadTickets();
  }, [filter, page]);

  const loadTickets = async () => {
    try {
      setLoading(true);
      const data = await api.listMyTickets(page, perPage, filter || undefined);
      setTickets(data.tickets);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to load tickets:', err);
    } finally {
      setLoading(false);
    }
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

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="support-page">
      <div className="support-header">
        <div>
          <h1>Support Tickets</h1>
          <p>Get help from our support team</p>
        </div>
        <Link to="/dashboard/support/new" className="btn btn-primary">
          + New Ticket
        </Link>
      </div>

      <div className="support-filters">
        <select 
          value={filter} 
          onChange={(e) => { setFilter(e.target.value as TicketStatus | ''); setPage(1); }}
          className="filter-select"
        >
          <option value="">All Tickets</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner" />
        </div>
      ) : tickets.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🎫</div>
          <h2>No tickets yet</h2>
          <p>Need help? Create a support ticket and we'll get back to you.</p>
          <Link to="/dashboard/support/new" className="btn btn-primary">
            Create Your First Ticket
          </Link>
        </div>
      ) : (
        <>
          <div className="tickets-list">
            {tickets.map(ticket => (
              <Link 
                key={ticket.id} 
                to={`/dashboard/support/${ticket.id}`}
                className="ticket-card"
              >
                <div className="ticket-header">
                  <span className="ticket-id">#{ticket.id}</span>
                  <span 
                    className="ticket-status"
                    style={{ backgroundColor: statusColors[ticket.status] }}
                  >
                    {statusLabels[ticket.status]}
                  </span>
                </div>
                <h3 className="ticket-subject">{ticket.subject}</h3>
                <div className="ticket-meta">
                  <span className="ticket-category">{categoryLabels[ticket.category]}</span>
                  <span 
                    className="ticket-priority"
                    style={{ color: priorityColors[ticket.priority] }}
                  >
                    {priorityLabels[ticket.priority]} Priority
                  </span>
                  <span className="ticket-date">{formatDate(ticket.created_at)}</span>
                </div>
                {ticket.assigned_admin_username && (
                  <div className="ticket-assigned">
                    Assigned to: {ticket.assigned_admin_username}
                  </div>
                )}
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn btn-secondary"
              >
                Previous
              </button>
              <span className="page-info">
                Page {page} of {totalPages}
              </span>
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn btn-secondary"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../../services/api';
import type { Ticket, TicketStatus, TicketStats } from '../../types';
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

export default function AdminTickets() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [stats, setStats] = useState<TicketStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const statusFilter = searchParams.get('status') || 'all';
  const priorityFilter = searchParams.get('priority') || 'all';
  const assignedFilter = searchParams.get('assigned') || 'all';

  useEffect(() => {
    loadTickets();
    loadStats();
  }, [page, statusFilter, priorityFilter, assignedFilter]);

  const loadTickets = async () => {
    try {
      setLoading(true);
      const data = await api.listAllTickets(
        page,
        20,
        statusFilter !== 'all' ? statusFilter as TicketStatus : undefined,
        priorityFilter !== 'all' ? priorityFilter as any : undefined,
        undefined,
        assignedFilter === 'assigned' ? true : undefined,
        assignedFilter === 'unassigned' ? true : undefined
      );
      setTickets(data.tickets);
      setTotalPages(Math.ceil(data.total / data.per_page));
    } catch (err) {
      console.error('Failed to load tickets:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await api.getTicketStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setSearchParams((params) => {
      if (value === 'all') {
        params.delete(key);
      } else {
        params.set(key, value);
      }
      return params;
    });
    setPage(1);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="admin-tickets">
      <div className="admin-tickets-header">
        <h1>Support Tickets</h1>
        <p>Manage customer support requests</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card stat-open">
            <span className="stat-number">{stats.tickets_open}</span>
            <span className="stat-label">Open</span>
          </div>
          <div className="stat-card stat-progress">
            <span className="stat-number">{stats.tickets_in_progress}</span>
            <span className="stat-label">In Progress</span>
          </div>
          <div className="stat-card stat-resolved">
            <span className="stat-number">{stats.tickets_resolved}</span>
            <span className="stat-label">Resolved</span>
          </div>
          <div className="stat-card stat-total">
            <span className="stat-number">{stats.total_tickets}</span>
            <span className="stat-label">Total</span>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="admin-filters">
        <select
          value={statusFilter}
          onChange={(e) => handleFilterChange('status', e.target.value)}
          className="filter-select"
        >
          <option value="all">All Statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>

        <select
          value={priorityFilter}
          onChange={(e) => handleFilterChange('priority', e.target.value)}
          className="filter-select"
        >
          <option value="all">All Priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="normal">Normal</option>
          <option value="low">Low</option>
        </select>

        <select
          value={assignedFilter}
          onChange={(e) => handleFilterChange('assigned', e.target.value)}
          className="filter-select"
        >
          <option value="all">All Tickets</option>
          <option value="unassigned">Unassigned</option>
          <option value="assigned">Assigned</option>
        </select>
      </div>

      {/* Tickets Table */}
      {loading ? (
        <div className="loading-state">
          <Spinner size={40} />
        </div>
      ) : tickets.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <h2>No Tickets Found</h2>
          <p>No tickets match your current filters.</p>
        </div>
      ) : (
        <>
          <div className="tickets-table-container">
            <table className="tickets-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Subject</th>
                  <th>User</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Category</th>
                  <th>Assigned</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((ticket) => (
                  <tr key={ticket.id}>
                    <td>
                      <Link to={`/admin/tickets/${ticket.id}`} className="ticket-link">
                        #{ticket.id}
                      </Link>
                    </td>
                    <td>
                      <Link to={`/admin/tickets/${ticket.id}`} className="ticket-subject-link">
                        {ticket.subject}
                      </Link>
                    </td>
                    <td>
                      <div className="user-cell">
                        <span className="user-name">{ticket.user?.discord_username || 'Unknown'}</span>
                        {ticket.user?.subscription_tier && ticket.user.subscription_tier !== 'free' && (
                          <span className="user-tier">{ticket.user.subscription_tier}</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span
                        className="status-badge"
                        style={{ backgroundColor: STATUS_COLORS[ticket.status] }}
                      >
                        {STATUS_LABELS[ticket.status]}
                      </span>
                    </td>
                    <td>
                      <span
                        className="priority-badge"
                        style={{ color: PRIORITY_COLORS[ticket.priority] }}
                      >
                        {ticket.priority.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span className="category-badge">
                        {ticket.category.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      {ticket.assigned_to ? (
                        <span className="assigned-name">
                          {ticket.assigned_to.discord_username}
                        </span>
                      ) : (
                        <span className="unassigned">—</span>
                      )}
                    </td>
                    <td className="date-cell">{formatDate(ticket.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-secondary"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </button>
              <span className="page-info">
                Page {page} of {totalPages}
              </span>
              <button
                className="btn btn-secondary"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
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

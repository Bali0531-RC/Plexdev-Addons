import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../../services/api';
import type { TicketCategory } from '../../types';
import './Support.css';

const categories: { value: TicketCategory; label: string; description: string }[] = [
  { value: 'general', label: 'General', description: 'General questions and inquiries' },
  { value: 'billing', label: 'Billing', description: 'Payment and subscription issues' },
  { value: 'technical', label: 'Technical', description: 'Technical problems and bugs' },
  { value: 'feature_request', label: 'Feature Request', description: 'Suggest new features' },
  { value: 'bug_report', label: 'Bug Report', description: 'Report a bug or issue' },
];

export default function NewTicket() {
  const navigate = useNavigate();
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [category, setCategory] = useState<TicketCategory>('general');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (subject.length < 5) {
      setError('Subject must be at least 5 characters.');
      return;
    }

    if (content.length < 10) {
      setError('Description must be at least 10 characters.');
      return;
    }

    try {
      setSubmitting(true);
      const ticket = await api.createTicket({
        subject,
        content,
        category,
      });
      navigate(`/dashboard/support/${ticket.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create ticket. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="new-ticket-form">
      <Link to="/dashboard/support" className="back-link">
        ← Back to Tickets
      </Link>

      <h1>Create Support Ticket</h1>
      <p style={{ color: '#888', marginBottom: '2rem' }}>
        Need help? Fill out the form below and our support team will get back to you as soon as possible.
      </p>

      {error && (
        <div className="error-message" style={{ marginBottom: '1rem', padding: '1rem', background: '#2a1a1a', borderRadius: '8px', color: '#dc3545' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="category">Category</label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value as TicketCategory)}
            disabled={submitting}
          >
            {categories.map(cat => (
              <option key={cat.value} value={cat.value}>
                {cat.label} - {cat.description}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="subject">Subject</label>
          <input
            type="text"
            id="subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Brief summary of your issue"
            maxLength={255}
            disabled={submitting}
          />
          <p className="form-hint">{subject.length}/255 characters (minimum 5)</p>
        </div>

        <div className="form-group">
          <label htmlFor="content">Description</label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Please describe your issue in detail. Include any relevant information that might help us assist you better."
            disabled={submitting}
          />
          <p className="form-hint">
            Be as detailed as possible. You can add attachments after creating the ticket.
          </p>
        </div>

        <div className="form-actions">
          <Link to="/dashboard/support" className="btn btn-secondary">
            Cancel
          </Link>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting || subject.length < 5 || content.length < 10}
          >
            {submitting ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
      </form>
    </div>
  );
}

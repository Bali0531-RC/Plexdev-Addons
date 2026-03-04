import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Review, ReviewListResponse } from '../types';
import { toast } from 'sonner';
import './ReviewsSection.css';

interface ReviewsSectionProps {
  slug: string;
  addonOwnerId: number;
}

function StarDisplay({ rating }: { rating: number }) {
  return (
    <span className="review-rating">
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i}>{i <= rating ? '★' : '☆'}</span>
      ))}
    </span>
  );
}

export default function ReviewsSection({ slug, addonOwnerId }: ReviewsSectionProps) {
  const { user, isAuthenticated } = useAuth();
  const [data, setData] = useState<ReviewListResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [formRating, setFormRating] = useState(5);
  const [formTitle, setFormTitle] = useState('');
  const [formContent, setFormContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadReviews = useCallback(async () => {
    try {
      const result = await api.getReviews(slug);
      setData(result);
    } catch {
      // Non-critical
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  const myReview = data?.reviews.find((r) => r.user_id === user?.id);
  const isOwner = user?.id === addonOwnerId;

  const openEditForm = (review: Review) => {
    setEditMode(true);
    setFormRating(review.rating);
    setFormTitle(review.title || '');
    setFormContent(review.content || '');
    setShowForm(true);
  };

  const openNewForm = () => {
    setEditMode(false);
    setFormRating(5);
    setFormTitle('');
    setFormContent('');
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      if (editMode) {
        await api.updateReview(slug, {
          rating: formRating,
          title: formTitle || undefined,
          content: formContent || undefined,
        });
        toast.success('Review updated');
      } else {
        await api.createReview(slug, {
          rating: formRating,
          title: formTitle || undefined,
          content: formContent || undefined,
        });
        toast.success('Review submitted');
      }
      setShowForm(false);
      loadReviews();
    } catch (err: any) {
      toast.error(err.message || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Delete your review?')) return;
    try {
      await api.deleteReview(slug);
      toast.success('Review deleted');
      setShowForm(false);
      loadReviews();
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete review');
    }
  };

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });

  if (loading) return null;

  return (
    <section className="reviews-section">
      <h2>Reviews {data && data.total > 0 && `(${data.total})`}</h2>

      {/* Summary */}
      {data && data.total > 0 && data.average_rating !== null && (
        <div className="reviews-summary">
          <div className="reviews-avg">
            <div className="reviews-avg-number">{data.average_rating}</div>
            <div className="reviews-avg-label">out of 5</div>
          </div>
          <div>
            <StarDisplay rating={Math.round(data.average_rating)} />
          </div>
          {data.rating_distribution && (
            <div className="rating-bars">
              {[5, 4, 3, 2, 1].map((star) => {
                const count = data.rating_distribution?.[String(star)] || 0;
                const pct = data.total > 0 ? (count / data.total) * 100 : 0;
                return (
                  <div key={star} className="rating-bar-row">
                    <span>{star}</span>
                    <div className="rating-bar-track">
                      <div className="rating-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                    <span>{count}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Write / Edit button */}
      {isAuthenticated && !isOwner && !showForm && (
        <div style={{ marginBottom: '1rem' }}>
          {myReview ? (
            <button className="btn btn-secondary btn-sm" onClick={() => openEditForm(myReview)}>
              Edit Your Review
            </button>
          ) : (
            <button className="btn btn-primary btn-sm" onClick={openNewForm}>
              Write a Review
            </button>
          )}
        </div>
      )}

      {/* Review Form */}
      {showForm && (
        <div className="review-form">
          <h3>{editMode ? 'Edit Review' : 'Write a Review'}</h3>
          <div className="rating-input">
            {[1, 2, 3, 4, 5].map((i) => (
              <button
                key={i}
                className={i <= formRating ? 'active' : ''}
                onClick={() => setFormRating(i)}
                type="button"
              >
                {i <= formRating ? '★' : '☆'}
              </button>
            ))}
          </div>
          <input
            type="text"
            placeholder="Title (optional)"
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            maxLength={200}
          />
          <textarea
            placeholder="Share your experience (optional)"
            value={formContent}
            onChange={(e) => setFormContent(e.target.value)}
            maxLength={2000}
          />
          <div className="review-form-actions">
            <button
              className="btn btn-primary btn-sm"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : editMode ? 'Update' : 'Submit'}
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </button>
            {editMode && (
              <button
                className="btn btn-sm"
                style={{ color: '#ef4444' }}
                onClick={handleDelete}
              >
                Delete
              </button>
            )}
          </div>
        </div>
      )}

      {/* Review List */}
      {data && data.reviews.length > 0 ? (
        data.reviews.map((review) => (
          <div key={review.id} className="review-item">
            <div className="review-item-header">
              <div className="review-author">
                {review.author_avatar && (
                  <img
                    className="review-author-avatar"
                    src={`https://cdn.discordapp.com/avatars/${review.author_discord_id}/${review.author_avatar}.png?size=56`}
                    alt=""
                  />
                )}
                <span className="review-author-name">
                  {review.author_username || 'Unknown User'}
                </span>
                <StarDisplay rating={review.rating} />
              </div>
              <span className="review-date">{formatDate(review.created_at)}</span>
            </div>
            {review.title && <div className="review-title">{review.title}</div>}
            {review.content && <div className="review-content">{review.content}</div>}
            {user && review.user_id === user.id && !showForm && (
              <div className="review-actions">
                <button onClick={() => openEditForm(review)}>Edit</button>
                <button className="danger" onClick={handleDelete}>
                  Delete
                </button>
              </div>
            )}
          </div>
        ))
      ) : (
        <p className="no-reviews">No reviews yet. Be the first to review this addon!</p>
      )}
    </section>
  );
}

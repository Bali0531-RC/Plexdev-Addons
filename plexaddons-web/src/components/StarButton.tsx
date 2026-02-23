import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './StarButton.css';

interface StarButtonProps {
  slug: string;
  className?: string;
}

export default function StarButton({ slug, className = '' }: StarButtonProps) {
  const { isAuthenticated } = useAuth();
  const [starred, setStarred] = useState(false);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadStatus();
  }, [slug]);

  const loadStatus = async () => {
    try {
      const status = await api.getStarStatus(slug);
      setStarred(status.starred);
      setCount(status.star_count);
    } catch {
      // Star status not critical
    }
  };

  const toggle = async () => {
    if (!isAuthenticated || loading) return;
    setLoading(true);
    try {
      const result = starred
        ? await api.unstarAddon(slug)
        : await api.starAddon(slug);
      setStarred(result.starred);
      setCount(result.star_count);
    } catch {
      // Ignore errors
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      className={`star-button ${starred ? 'starred' : ''} ${className}`}
      onClick={toggle}
      disabled={!isAuthenticated || loading}
      title={isAuthenticated ? (starred ? 'Unstar' : 'Star') : 'Sign in to star'}
    >
      <span className="star-icon">{starred ? '★' : '☆'}</span>
      <span className="star-count">{count}</span>
    </button>
  );
}

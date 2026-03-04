import { useState, useEffect, useCallback } from 'react';
import './ScreenshotGallery.css';

interface ScreenshotGalleryProps {
  screenshots: string[];
  bannerUrl?: string | null;
}

export default function ScreenshotGallery({ screenshots, bannerUrl }: ScreenshotGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const allImages = screenshots;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (lightboxIndex === null) return;
      if (e.key === 'Escape') setLightboxIndex(null);
      if (e.key === 'ArrowLeft') setLightboxIndex(i => (i !== null && i > 0 ? i - 1 : i));
      if (e.key === 'ArrowRight')
        setLightboxIndex(i => (i !== null && i < allImages.length - 1 ? i + 1 : i));
    },
    [lightboxIndex, allImages.length]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Lock body scroll when lightbox is open
  useEffect(() => {
    if (lightboxIndex !== null) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [lightboxIndex]);

  if (!bannerUrl && allImages.length === 0) return null;

  return (
    <>
      {bannerUrl && (
        <div className="addon-banner">
          <img src={bannerUrl} alt="Addon banner" loading="lazy" />
        </div>
      )}

      {allImages.length > 0 && (
        <div className="screenshot-gallery">
          <h3>Screenshots</h3>
          <div className="screenshot-grid">
            {allImages.map((url, i) => (
              <div key={i} className="screenshot-thumb" onClick={() => setLightboxIndex(i)}>
                <img src={url} alt={`Screenshot ${i + 1}`} loading="lazy" />
              </div>
            ))}
          </div>
        </div>
      )}

      {lightboxIndex !== null && (
        <div className="lightbox-overlay" onClick={() => setLightboxIndex(null)}>
          <div className="lightbox-content" onClick={e => e.stopPropagation()}>
            <button className="lightbox-close" onClick={() => setLightboxIndex(null)}>
              ✕
            </button>
            {lightboxIndex > 0 && (
              <button
                className="lightbox-nav lightbox-prev"
                onClick={() => setLightboxIndex(i => (i !== null ? i - 1 : i))}
              >
                ‹
              </button>
            )}
            <img src={allImages[lightboxIndex]} alt={`Screenshot ${lightboxIndex + 1}`} />
            {lightboxIndex < allImages.length - 1 && (
              <button
                className="lightbox-nav lightbox-next"
                onClick={() => setLightboxIndex(i => (i !== null ? i + 1 : i))}
              >
                ›
              </button>
            )}
            <div className="lightbox-counter">
              {lightboxIndex + 1} / {allImages.length}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

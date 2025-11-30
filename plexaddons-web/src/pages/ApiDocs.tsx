import { useEffect } from 'react';
import './ApiDocs.css';

export default function ApiDocs() {
  useEffect(() => {
    // Load ReDoc script
    const script = document.createElement('script');
    script.src = 'https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js';
    script.async = true;
    script.onload = () => {
      // @ts-expect-error ReDoc is loaded from CDN
      if (window.Redoc) {
        // @ts-expect-error ReDoc is loaded from CDN
        window.Redoc.init(
          `${import.meta.env.VITE_API_URL || 'https://addons.plexdev.live/api'}/openapi.json`,
          {
            theme: {
              colors: {
                primary: {
                  main: '#6366f1',
                },
                text: {
                  primary: '#f4f4f5',
                  secondary: '#a1a1aa',
                },
                http: {
                  get: '#22c55e',
                  post: '#3b82f6',
                  put: '#f59e0b',
                  delete: '#ef4444',
                  patch: '#8b5cf6',
                },
              },
              typography: {
                fontSize: '15px',
                fontFamily: 'Inter, system-ui, sans-serif',
                headings: {
                  fontFamily: 'Inter, system-ui, sans-serif',
                },
                code: {
                  fontFamily: 'JetBrains Mono, monospace',
                },
              },
              sidebar: {
                backgroundColor: '#09090b',
                textColor: '#a1a1aa',
                activeTextColor: '#f4f4f5',
              },
              rightPanel: {
                backgroundColor: '#18181b',
              },
            },
            hideDownloadButton: false,
            hideHostname: false,
            expandResponses: '200,201',
            pathInMiddlePanel: true,
            scrollYOffset: 60,
          },
          document.getElementById('redoc-container')
        );
      }
    };
    document.body.appendChild(script);

    return () => {
      // Cleanup script on unmount
      const existingScript = document.querySelector('script[src*="redoc"]');
      if (existingScript) {
        existingScript.remove();
      }
    };
  }, []);

  return (
    <div className="api-docs-page">
      <div className="api-docs-header">
        <h1>API Documentation</h1>
        <p>Interactive API reference powered by OpenAPI/Swagger</p>
        <div className="api-docs-links">
          <a 
            href={`${import.meta.env.VITE_API_URL || 'https://addons.plexdev.live/api'}/openapi.json`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
          >
            📄 OpenAPI Spec
          </a>
          <a href="/docs" className="btn btn-secondary">
            📖 Developer Guide
          </a>
        </div>
      </div>
      <div id="redoc-container" className="redoc-container">
        <div className="redoc-loading">
          <div className="spinner"></div>
          <p>Loading API documentation...</p>
        </div>
      </div>
    </div>
  );
}

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MarkdownRenderer from './MarkdownRenderer';

describe('MarkdownRenderer', () => {
  it('renders plain text', () => {
    render(<MarkdownRenderer content="Hello world" />);
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('renders headings', () => {
    render(<MarkdownRenderer content="# My Title" />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('My Title');
  });

  it('renders bold text', () => {
    render(<MarkdownRenderer content="**bold**" />);
    expect(screen.getByText('bold').tagName).toBe('STRONG');
  });

  it('renders links', () => {
    render(<MarkdownRenderer content="[click](https://example.com)" />);
    const link = screen.getByRole('link', { name: 'click' });
    expect(link).toHaveAttribute('href', 'https://example.com');
  });

  it('applies custom className', () => {
    const { container } = render(<MarkdownRenderer content="test" className="extra" />);
    expect(container.firstChild).toHaveClass('markdown-content');
    expect(container.firstChild).toHaveClass('extra');
  });

  it('renders GFM tables', () => {
    const md = `| A | B |\n|---|---|\n| 1 | 2 |`;
    const { container } = render(<MarkdownRenderer content={md} />);
    expect(container.querySelector('table')).toBeInTheDocument();
  });

  it('sanitizes script tags', () => {
    const { container } = render(
      <MarkdownRenderer content="safe text <script>alert('xss')</script>" />
    );
    expect(container.querySelector('script')).toBeNull();
    expect(container.textContent).toContain('safe text');
  });
});

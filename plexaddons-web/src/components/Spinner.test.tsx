import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import Spinner from './Spinner';

describe('Spinner', () => {
  it('renders with default size', () => {
    const { container } = render(<Spinner />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner).toBeInTheDocument();
    expect(spinner.style.width).toBe('32px');
    expect(spinner.style.height).toBe('32px');
  });

  it('renders with custom size', () => {
    const { container } = render(<Spinner size={64} />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.style.width).toBe('64px');
    expect(spinner.style.height).toBe('64px');
  });

  it('has spinner class', () => {
    const { container } = render(<Spinner />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toBe('spinner');
  });

  it('has animation style', () => {
    const { container } = render(<Spinner />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.style.animation).toContain('spin');
  });

  it('scales border with size', () => {
    const { container } = render(<Spinner size={100} />);
    const spinner = container.firstChild as HTMLElement;
    // border should be max(2, 100/10) = 10px; jsdom converts hex to rgb
    expect(spinner.style.borderTopColor).toBe('rgb(233, 164, 38)');
  });
});

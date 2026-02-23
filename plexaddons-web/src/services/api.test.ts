import { describe, it, expect, vi } from 'vitest';
import { isAllowedRedirectUrl, safeRedirect } from '../services/api';

describe('isAllowedRedirectUrl', () => {
  it('allows Stripe checkout', () => {
    expect(isAllowedRedirectUrl('https://checkout.stripe.com/c/pay_123')).toBe(true);
  });

  it('allows Stripe billing', () => {
    expect(isAllowedRedirectUrl('https://billing.stripe.com/session/123')).toBe(true);
  });

  it('allows Discord', () => {
    expect(isAllowedRedirectUrl('https://discord.com/oauth2/authorize')).toBe(true);
  });

  it('allows PayPal', () => {
    expect(isAllowedRedirectUrl('https://www.paypal.com/checkoutnow')).toBe(true);
  });

  it('allows PayPal without www', () => {
    expect(isAllowedRedirectUrl('https://paypal.com/checkoutnow')).toBe(true);
  });

  it('rejects HTTP URLs', () => {
    expect(isAllowedRedirectUrl('http://checkout.stripe.com/c/pay_123')).toBe(false);
  });

  it('rejects unknown domains', () => {
    expect(isAllowedRedirectUrl('https://evil.com/phish')).toBe(false);
  });

  it('rejects JavaScript URLs', () => {
    expect(isAllowedRedirectUrl('javascript:alert(1)')).toBe(false);
  });

  it('rejects empty string', () => {
    expect(isAllowedRedirectUrl('')).toBe(false);
  });

  it('rejects malformed URLs', () => {
    expect(isAllowedRedirectUrl('not-a-url')).toBe(false);
  });

  it('rejects data URLs', () => {
    expect(isAllowedRedirectUrl('data:text/html,<h1>hi</h1>')).toBe(false);
  });

  it('rejects subdomain spoofing', () => {
    expect(isAllowedRedirectUrl('https://checkout.stripe.com.evil.com/pay')).toBe(false);
  });
});

describe('safeRedirect', () => {
  it('throws on disallowed URL', () => {
    expect(() => safeRedirect('https://evil.com')).toThrow('Redirect blocked: untrusted URL');
  });

  it('redirects on allowed URL', () => {
    const originalLocation = window.location.href;
    // jsdom doesn't actually navigate, but we can verify no throw
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { href: originalLocation },
    });
    expect(() => safeRedirect('https://checkout.stripe.com/c/pay_123')).not.toThrow();
  });
});

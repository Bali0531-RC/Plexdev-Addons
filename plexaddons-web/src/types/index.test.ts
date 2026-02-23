import { describe, it, expect } from 'vitest';
import { ADDON_TAGS } from './index';
import type { AddonTag } from './index';

describe('ADDON_TAGS', () => {
  it('has 11 tags', () => {
    expect(ADDON_TAGS).toHaveLength(11);
  });

  it('each tag has value, label, description', () => {
    for (const tag of ADDON_TAGS) {
      expect(tag).toHaveProperty('value');
      expect(tag).toHaveProperty('label');
      expect(tag).toHaveProperty('description');
      expect(typeof tag.value).toBe('string');
      expect(typeof tag.label).toBe('string');
      expect(typeof tag.description).toBe('string');
    }
  });

  it('includes utility tag', () => {
    const utility = ADDON_TAGS.find(t => t.value === 'utility');
    expect(utility).toBeDefined();
    expect(utility?.label).toBe('Utility');
  });

  it('has unique values', () => {
    const values = ADDON_TAGS.map(t => t.value);
    expect(new Set(values).size).toBe(values.length);
  });

  it('has unique labels', () => {
    const labels = ADDON_TAGS.map(t => t.label);
    expect(new Set(labels).size).toBe(labels.length);
  });

  it('contains expected tags', () => {
    const expected: AddonTag[] = [
      'utility', 'media', 'automation', 'moderation', 'fun',
      'economy', 'music', 'leveling', 'logging', 'integration', 'other',
    ];
    const values = ADDON_TAGS.map(t => t.value);
    for (const tag of expected) {
      expect(values).toContain(tag);
    }
  });
});

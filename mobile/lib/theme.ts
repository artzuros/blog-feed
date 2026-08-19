// Shared color tokens for the mobile app. One light palette, iOS-first.
export const colors = {
  bg: '#FBFCFE',
  surface: '#FFFFFF',
  border: '#E2E8F0',
  text: '#0F172A',
  textSub: '#64748B',
  textMuted: '#94A3B8',
  primary: '#2563EB',
  press: '#F1F5F9',
  dangerBg: '#FEF2F2',
  dangerText: '#B91C1C',
  // Score badge backgrounds/foregrounds, per quality tier (see ArticleCard).
  scoreTiers: [
    { bg: '#E8EEF4', fg: '#3A4A5A' }, // ≥ 0.5
    { bg: '#FFF3E0', fg: '#9A6B1F' }, // ≥ 0.65
    { bg: '#E6F6EC', fg: '#1E7A44' }, // ≥ 0.8
    { bg: '#E3F0FF', fg: '#1B6AC9' }, // no score
  ],
};

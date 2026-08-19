import { useColorScheme } from 'react-native';

// Fonts — from the blog-feed-hub web theme (Instrument Serif + Work Sans).
// Instrument Serif is a single-weight (400) display face — headings use it at
// weight 400. Body text uses Work Sans with explicit weights.
export const fonts = {
  serif: 'InstrumentSerif_400Regular',
  sans: 'WorkSans_400Regular',
  sansMedium: 'WorkSans_500Medium',
  sansSemibold: 'WorkSans_600SemiBold',
  sansBold: 'WorkSans_700Bold',
} as const;

// Color palettes — mapped from blog-feed-hub/src/styles.css. The hub defines
// colors in OKLCH; these are exact sRGB conversions. Hub token → this token:
//   --paper → bg, --card → surface, --foreground → text, --primary → primary,
//   --secondary-foreground → textSub, --muted-foreground → textMuted, ...
const light = {
  bg: '#f8f3eb', // --paper — warm cream page background
  surface: '#fdfaf4', // --card — raised cards
  border: '#d3cdc6', // --border
  text: '#15110d', // --foreground — warm near-black body text
  textSub: '#1a1512', // --secondary-foreground — secondary text
  textMuted: '#635c57', // --muted-foreground — captions / meta
  primary: '#15110d', // --primary — ink; buttons are dark charcoal, not blue
  onPrimary: '#f9f4ec', // --primary-foreground — cream text on primary
  press: '#e9e4dc', // --muted — chip / pressed backgrounds
  dangerBg: '#fce1de', // derived light tint of --destructive
  dangerText: '#c20011', // --destructive — rust red
  // Score badge backgrounds/foregrounds, per quality tier (see ArticleCard).
  scoreTiers: [
    { bg: '#ebe3da', fg: '#1a1512' }, // low score — --secondary (tan)
    { bg: '#f3ba25', fg: '#15110d' }, // ≥ 0.65 — --highlight (gold)
    { bg: '#c5372f', fg: '#fdf8f0' }, // ≥ 0.8 — --accent (rust)
    { bg: '#e9e4dc', fg: '#635c57' }, // no score — --muted
  ],
} as const;

const dark = {
  bg: '#100c0a', // --paper
  surface: '#1d1a17', // --card
  border: '#36322f', // --border
  text: '#efeae2', // --foreground — warm paper text
  textSub: '#efeae2', // --secondary-foreground
  textMuted: '#9d9790', // --muted-foreground
  primary: '#efeae2', // --primary — cream; buttons are paper, not black
  onPrimary: '#100c0a', // --primary-foreground — ink text on primary
  press: '#272320', // --muted
  dangerBg: '#4f1a18', // derived dark tint of --destructive
  dangerText: '#f94144', // --destructive
  scoreTiers: [
    { bg: '#2c2825', fg: '#efeae2' }, // low score — --secondary
    { bg: '#e6ad00', fg: '#100c0a' }, // ≥ 0.65 — --highlight (gold)
    { bg: '#f96c4a', fg: '#100c0a' }, // ≥ 0.8 — --accent (coral)
    { bg: '#272320', fg: '#9d9790' }, // no score — --muted
  ],
} as const;

export type Palette = {
  bg: string;
  surface: string;
  border: string;
  text: string;
  textSub: string;
  textMuted: string;
  primary: string;
  onPrimary: string;
  press: string;
  dangerBg: string;
  dangerText: string;
  scoreTiers: readonly { bg: string; fg: string }[];
};

export const palettes = { light, dark } as const;

/** Current palette, following the device's system appearance. */
export function useTheme(): Palette {
  const scheme = useColorScheme();
  return palettes[scheme === 'dark' ? 'dark' : 'light'];
}

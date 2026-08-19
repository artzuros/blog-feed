import { useMemo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { fonts, Palette, useTheme } from '../lib/theme';

/** 0 = low, 1 = mid, 2 = high, 3 = no score. */
export function scoreTier(score: number | null): number {
  if (score == null) return 3;
  if (score >= 0.8) return 2;
  if (score >= 0.65) return 1;
  return 0;
}

export function ArticleCard({
  title,
  blog,
  score,
  reason,
  meta,
  onPress,
}: {
  title: string;
  blog: string;
  score: number | null;
  reason?: string | null;
  meta?: string;
  onPress: () => void;
}) {
  const c = useTheme();
  const styles = useMemo(() => createStyles(c), [c]);
  const tier = c.scoreTiers[scoreTier(score)];
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
    >
      <View style={styles.cardHeader}>
        <Text style={styles.cardBlog} numberOfLines={1}>
          {blog}
        </Text>
        <View style={[styles.scoreBadge, { backgroundColor: tier.bg }]}>
          <Text style={[styles.scoreText, { color: tier.fg }]}>
            {(score ?? 0).toFixed(2)}
          </Text>
        </View>
      </View>
      <Text style={styles.cardTitle} numberOfLines={3}>
        {title}
      </Text>
      {reason ? (
        <Text style={styles.cardReason} numberOfLines={2}>
          {reason}
        </Text>
      ) : null}
      {meta ? <Text style={styles.cardMeta}>{meta}</Text> : null}
    </Pressable>
  );
}

const createStyles = (c: Palette) =>
  StyleSheet.create({
    card: {
      backgroundColor: c.surface,
      borderRadius: 14,
      borderWidth: 1,
      borderColor: c.border,
      padding: 16,
      marginBottom: 12,
    },
    cardPressed: {
      backgroundColor: c.press,
    },
    cardHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: 6,
    },
    cardBlog: {
      flex: 1,
      fontSize: 12,
      fontWeight: '700',
      fontFamily: fonts.sansBold,
      color: c.primary,
      textTransform: 'uppercase',
      letterSpacing: 0.5,
      marginRight: 8,
    },
    scoreBadge: {
      borderRadius: 8,
      paddingHorizontal: 8,
      paddingVertical: 3,
    },
    scoreText: {
      fontSize: 12,
      fontWeight: '800',
      fontFamily: fonts.sansBold,
      fontVariant: ['tabular-nums'],
    },
    cardTitle: {
      fontSize: 16,
      fontWeight: '400',
      fontFamily: fonts.serif,
      lineHeight: 22,
      color: c.text,
    },
    cardReason: {
      marginTop: 6,
      fontSize: 13,
      lineHeight: 18,
      fontFamily: fonts.sans,
      color: c.textSub,
    },
    cardMeta: {
      marginTop: 8,
      fontSize: 12,
      fontFamily: fonts.sans,
      color: c.textMuted,
    },
  });

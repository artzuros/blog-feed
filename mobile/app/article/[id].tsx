import { useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { scoreTier } from '../../components/ArticleCard';
import { ArticleDetail, getArticle } from '../../lib/api';
import { fonts, Palette, useTheme } from '../../lib/theme';

export default function ArticleScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const c = useTheme();
  const styles = useMemo(() => createStyles(c), [c]);
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setArticle(await getArticle(id));
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Request failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const openInBrowser = useCallback((url: string) => {
    Linking.openURL(url).catch(() => {});
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={c.primary} size="large" />
      </View>
    );
  }

  if (error || !article) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>
          {error ?? 'Article not found.'}
        </Text>
        <Pressable style={styles.retryButton} onPress={load}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </Pressable>
      </View>
    );
  }

  const tier = c.scoreTiers[scoreTier(article.combined_score)];
  const keywords = (article.keywords ?? '')
    .split(',')
    .map((k) => k.trim())
    .filter(Boolean);

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
    >
      <Text style={styles.blog}>{article.blog_name}</Text>
      <Text style={styles.title}>{article.title}</Text>

      <View style={styles.badgeRow}>
        <View style={[styles.badge, { backgroundColor: tier.bg }]}>
          <Text style={[styles.badgeText, { color: tier.fg }]}>
            Score {(article.combined_score ?? 0).toFixed(2)}
          </Text>
        </View>
      </View>

      {keywords.length > 0 && (
        <View style={styles.keywordRow}>
          {keywords.map((k) => (
            <View key={k} style={styles.keywordChip}>
              <Text style={styles.keywordText}>{k}</Text>
            </View>
          ))}
        </View>
      )}

      <Pressable
        onPress={() => openInBrowser(article.url)}
        style={({ pressed }) => [
          styles.openButton,
          pressed && styles.openButtonPressed,
        ]}
      >
        <Text style={styles.openButtonText}>Open in browser</Text>
      </Pressable>
    </ScrollView>
  );
}

const createStyles = (c: Palette) =>
  StyleSheet.create({
    screen: {
      flex: 1,
      backgroundColor: c.bg,
    },
    center: {
      flex: 1,
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: c.bg,
      padding: 24,
      gap: 16,
    },
    content: {
      padding: 20,
      paddingBottom: 48,
    },
    blog: {
      fontSize: 13,
      fontWeight: '700',
      fontFamily: fonts.sansBold,
      color: c.primary,
      textTransform: 'uppercase',
      letterSpacing: 0.5,
    },
    title: {
      marginTop: 8,
      fontSize: 24,
      fontWeight: '400',
      fontFamily: fonts.serif,
      lineHeight: 31,
      color: c.text,
    },
    badgeRow: {
      flexDirection: 'row',
      gap: 8,
      marginTop: 14,
    },
    badge: {
      borderRadius: 8,
      paddingHorizontal: 10,
      paddingVertical: 5,
    },
    badgeText: {
      fontSize: 12,
      fontWeight: '800',
      fontFamily: fonts.sansBold,
      fontVariant: ['tabular-nums'],
    },
    keywordRow: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      gap: 8,
      marginTop: 14,
    },
    keywordChip: {
      paddingHorizontal: 10,
      paddingVertical: 4,
      borderRadius: 999,
      backgroundColor: c.press,
    },
    keywordText: {
      fontSize: 12,
      fontWeight: '600',
      fontFamily: fonts.sansSemibold,
      color: c.textSub,
    },
    openButton: {
      marginTop: 24,
      height: 48,
      borderRadius: 12,
      backgroundColor: c.primary,
      alignItems: 'center',
      justifyContent: 'center',
    },
    openButtonPressed: {
      opacity: 0.85,
    },
    openButtonText: {
      color: c.onPrimary,
      fontSize: 15,
      fontWeight: '700',
      fontFamily: fonts.sansSemibold,
    },
    errorText: {
      color: c.dangerText,
      fontSize: 14,
      textAlign: 'center',
      fontFamily: fonts.sans,
    },
    retryButton: {
      paddingHorizontal: 20,
      paddingVertical: 10,
      borderRadius: 10,
      backgroundColor: c.primary,
    },
    retryButtonText: {
      color: c.onPrimary,
      fontWeight: '700',
      fontFamily: fonts.sansSemibold,
    },
  });

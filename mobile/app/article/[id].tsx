import { useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ArticleDetail, getArticle } from '../../lib/api';
import { fmtDate } from '../../lib/format';
import { colors } from '../../lib/theme';
import { scoreTier } from '../../components/ArticleCard';

export default function ArticleScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
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
        <ActivityIndicator color={colors.primary} size="large" />
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

  const tier = colors.scoreTiers[scoreTier(article.combined_score)];
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
        {article.llm_score != null && (
          <View style={[styles.badge, styles.llmBadge]}>
            <Text style={styles.llmBadgeText}>LLM reviewed</Text>
          </View>
        )}
      </View>

      {article.reason ? (
        <View style={styles.reasonBox}>
          <Text style={styles.reasonLabel}>Why this is worth reading</Text>
          <Text style={styles.reasonText}>{article.reason}</Text>
        </View>
      ) : null}

      {keywords.length > 0 && (
        <View style={styles.keywordRow}>
          {keywords.map((k) => (
            <View key={k} style={styles.keywordChip}>
              <Text style={styles.keywordText}>{k}</Text>
            </View>
          ))}
        </View>
      )}

      <Text style={styles.meta}>
        {article.source} · fetched {fmtDate(article.fetched_at)}
        {article.content_type ? ` · ${article.content_type}` : ''}
      </Text>

      {article.text_content ? (
        <View style={styles.fullTextSection}>
          <Text style={styles.fullTextLabel}>Full text</Text>
          <Text style={styles.fullText}>{article.text_content}</Text>
        </View>
      ) : null}

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

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg,
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
    color: colors.primary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  title: {
    marginTop: 8,
    fontSize: 24,
    fontWeight: '700',
    lineHeight: 31,
    color: colors.text,
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
    fontVariant: ['tabular-nums'],
  },
  llmBadge: {
    backgroundColor: colors.press,
  },
  llmBadgeText: {
    fontSize: 12,
    fontWeight: '800',
    color: colors.textSub,
  },
  reasonBox: {
    marginTop: 18,
    padding: 14,
    borderRadius: 12,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  reasonLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 6,
  },
  reasonText: {
    fontSize: 14,
    lineHeight: 20,
    color: colors.textSub,
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
    backgroundColor: colors.press,
  },
  keywordText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.textSub,
  },
  meta: {
    marginTop: 16,
    fontSize: 12,
    color: colors.textMuted,
  },
  fullTextSection: {
    marginTop: 22,
  },
  fullTextLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 8,
  },
  fullText: {
    fontSize: 14,
    lineHeight: 21,
    color: colors.text,
  },
  openButton: {
    marginTop: 24,
    height: 48,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  openButtonPressed: {
    opacity: 0.85,
  },
  openButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
  errorText: {
    color: colors.dangerText,
    fontSize: 14,
    textAlign: 'center',
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: colors.primary,
  },
  retryButtonText: {
    color: '#fff',
    fontWeight: '700',
  },
});

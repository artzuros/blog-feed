import { StatusBar } from 'expo-status-bar';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Keyboard,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

// Live API base — swap to a local URL (http://<server-ip>:8765/api) when
// running the backend locally during development.
const API_BASE = 'https://blog-feed-aws.pranav-bansal.com/api';

type Article = {
  url: string;
  title: string;
  blog_name: string;
  score: number | null;
  llm_score: number | null;
  combined_score: number | null;
  reason: string | null;
  keywords: string | null;
  source: string;
  fetched_at: string;
  snippet?: string | null;
};

type SearchResponse = {
  query: string;
  count: number;
  limit: number;
  offset: number;
  min_score: number;
  search_type: string;
  corrected_query?: string;
  fallback?: boolean;
  articles: Article[];
};

const SCORE_BADGE_COLORS: Record<number, { bg: string; fg: string }> = {
  0: { bg: '#E8EEF4', fg: '#3A4A5A' }, // ≥ 0.5
  1: { bg: '#FFF3E0', fg: '#9A6B1F' }, // ≥ 0.65
  2: { bg: '#E6F6EC', fg: '#1E7A44' }, // ≥ 0.8
  3: { bg: '#E3F0FF', fg: '#1B6AC9' }, // fallback
};

function scoreBadge(score: number | null) {
  if (score == null) return SCORE_BADGE_COLORS[3];
  if (score >= 0.8) return SCORE_BADGE_COLORS[2];
  if (score >= 0.65) return SCORE_BADGE_COLORS[1];
  return SCORE_BADGE_COLORS[0];
}

export default function App() {
  const [query, setQuery] = useState('');
  const [articles, setArticles] = useState<Article[]>([]);
  const [resultInfo, setResultInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setLoading(true);
    setError(null);
    Keyboard.dismiss();
    try {
      const res = await fetch(
        `${API_BASE}/search?q=${encodeURIComponent(q)}&limit=30`,
      );
      if (!res.ok) throw new Error(`API responded with HTTP ${res.status}`);
      const data = (await res.json()) as SearchResponse;
      setArticles(data.articles ?? []);
      const label =
        data.search_type === 'semantic'
          ? 'semantic match'
          : data.search_type === 'fuzzy'
            ? `fuzzy → “${data.corrected_query}”`
            : data.search_type;
      setResultInfo(
        `${data.count} result${data.count === 1 ? '' : 's'} · ${label}`,
      );
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Request failed';
      setError(message);
      setArticles([]);
      setResultInfo(null);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const openArticle = useCallback((url: string) => {
    Linking.openURL(url).catch(() => {});
  }, []);

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        <StatusBar style="dark" />

        <View style={styles.header}>
          <Text style={styles.title}>Blog Feed</Text>
          <Text style={styles.subtitle}>
            High-signal engineering reading — searched, scored, surfaced
          </Text>
        </View>

        <View style={styles.searchRow}>
          <TextInput
            style={styles.searchInput}
            placeholder="Search engineering blogs…"
            placeholderTextColor="#94A3B8"
            value={query}
            onChangeText={setQuery}
            onSubmitEditing={search}
            returnKeyType="search"
            autoCorrect={false}
            autoCapitalize="none"
            clearButtonMode="while-editing"
          />
          <Pressable
            style={({ pressed }) => [
              styles.searchButton,
              pressed && styles.searchButtonPressed,
            ]}
            onPress={search}
            disabled={loading || query.trim().length < 2}
          >
            {loading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={styles.searchButtonText}>Search</Text>
            )}
          </Pressable>
        </View>

        {error && (
          <View style={styles.messageBox}>
            <Text style={styles.errorText}>
              {error} — check the API base in App.tsx.
            </Text>
          </View>
        )}

        {resultInfo && !error && (
          <Text style={styles.resultInfo}>{resultInfo}</Text>
        )}

        <FlatList
          data={articles}
          keyExtractor={(item) => item.url}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            !loading && !error ? (
              <Text style={styles.emptyText}>
                {query.trim().length >= 2
                  ? 'No results — try another query.'
                  : 'Type at least 2 characters to search the index.'}
              </Text>
            ) : null
          }
          renderItem={({ item }) => (
            <ArticleCard article={item} onPress={() => openArticle(item.url)} />
          )}
        />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

function ArticleCard({
  article,
  onPress,
}: {
  article: Article;
  onPress: () => void;
}) {
  const badge = scoreBadge(article.combined_score);
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
    >
      <View style={styles.cardHeader}>
        <Text style={styles.cardBlog} numberOfLines={1}>
          {article.blog_name}
        </Text>
        <View style={[styles.scoreBadge, { backgroundColor: badge.bg }]}>
          <Text style={[styles.scoreText, { color: badge.fg }]}>
            {(article.combined_score ?? 0).toFixed(2)}
          </Text>
        </View>
      </View>
      <Text style={styles.cardTitle} numberOfLines={3}>
        {article.title}
      </Text>
      {article.reason ? (
        <Text style={styles.cardReason} numberOfLines={2}>
          {article.reason}
        </Text>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#FBFCFE',
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 16,
  },
  title: {
    fontSize: 34,
    fontWeight: '800',
    color: '#0F172A',
    letterSpacing: -0.5,
  },
  subtitle: {
    marginTop: 4,
    fontSize: 13,
    color: '#64748B',
  },
  searchRow: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
  searchInput: {
    flex: 1,
    height: 46,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 14,
    fontSize: 16,
    color: '#0F172A',
  },
  searchButton: {
    height: 46,
    paddingHorizontal: 18,
    borderRadius: 12,
    backgroundColor: '#2563EB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  searchButtonPressed: {
    opacity: 0.8,
  },
  searchButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
  resultInfo: {
    paddingHorizontal: 20,
    paddingBottom: 8,
    fontSize: 12,
    color: '#64748B',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  messageBox: {
    marginHorizontal: 20,
    marginBottom: 10,
    padding: 12,
    borderRadius: 10,
    backgroundColor: '#FEF2F2',
  },
  errorText: {
    color: '#B91C1C',
    fontSize: 13,
  },
  listContent: {
    paddingHorizontal: 20,
    paddingBottom: 32,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 16,
    marginBottom: 12,
  },
  cardPressed: {
    backgroundColor: '#F1F5F9',
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
    color: '#2563EB',
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
    fontVariant: ['tabular-nums'],
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 22,
    color: '#0F172A',
  },
  cardReason: {
    marginTop: 6,
    fontSize: 13,
    lineHeight: 18,
    color: '#64748B',
  },
  emptyText: {
    textAlign: 'center',
    color: '#94A3B8',
    fontSize: 14,
    paddingVertical: 40,
  },
});

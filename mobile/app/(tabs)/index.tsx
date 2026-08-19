import { useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Keyboard,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ArticleCard } from '../../components/ArticleCard';
import { searchArticles, SearchArticle } from '../../lib/api';
import { colors } from '../../lib/theme';

export default function SearchScreen() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [articles, setArticles] = useState<SearchArticle[]>([]);
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
      const data = await searchArticles(q, 30);
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

  const openArticle = useCallback(
    (item: SearchArticle) => {
      router.push({
        pathname: '/article/[id]',
        params: { id: String(item.id) },
      });
    },
    [router],
  );

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
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
          placeholderTextColor={colors.textMuted}
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
            {error} — check the API base in lib/api.ts.
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
          <ArticleCard
            title={item.title}
            blog={item.blog_name}
            score={item.combined_score}
            reason={item.reason}
            onPress={() => openArticle(item)}
          />
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 16,
  },
  title: {
    fontSize: 34,
    fontWeight: '800',
    color: colors.text,
    letterSpacing: -0.5,
  },
  subtitle: {
    marginTop: 4,
    fontSize: 13,
    color: colors.textSub,
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
    borderColor: colors.border,
    backgroundColor: colors.surface,
    paddingHorizontal: 14,
    fontSize: 16,
    color: colors.text,
  },
  searchButton: {
    height: 46,
    paddingHorizontal: 18,
    borderRadius: 12,
    backgroundColor: colors.primary,
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
    color: colors.textSub,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  messageBox: {
    marginHorizontal: 20,
    marginBottom: 10,
    padding: 12,
    borderRadius: 10,
    backgroundColor: colors.dangerBg,
  },
  errorText: {
    color: colors.dangerText,
    fontSize: 13,
  },
  listContent: {
    paddingHorizontal: 20,
    paddingBottom: 32,
  },
  emptyText: {
    textAlign: 'center',
    color: colors.textMuted,
    fontSize: 14,
    paddingVertical: 40,
  },
});

import { useRouter } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ArticleCard } from '../../components/ArticleCard';
import { FeedArticle, listArticles } from '../../lib/api';
import { fmtDate } from '../../lib/format';
import { colors } from '../../lib/theme';

const PAGE_SIZE = 25;
const SORTS = [
  { key: 'fetched_at', label: 'Newest' },
  { key: 'combined_score', label: 'Top' },
] as const;

type SortKey = (typeof SORTS)[number]['key'];

export default function BrowseScreen() {
  const router = useRouter();
  const [sort, setSort] = useState<SortKey>('fetched_at');
  const [articles, setArticles] = useState<FeedArticle[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Guard against overlapping loads (onEndReached fires in bursts).
  const busyRef = useRef(false);
  const offsetRef = useRef(0);

  const load = useCallback(
    async (mode: 'replace' | 'append') => {
      if (busyRef.current) return;
      busyRef.current = true;
      if (mode === 'replace') {
        setLoading(true);
        setRefreshing(false);
      } else {
        setLoadingMore(true);
      }
      setError(null);
      try {
        const offset = mode === 'append' ? offsetRef.current : 0;
        const data = await listArticles(offset, PAGE_SIZE, sort);
        setArticles((prev) =>
          mode === 'append' ? [...prev, ...data.articles] : data.articles,
        );
        setTotal(data.total);
        offsetRef.current = offset + data.articles.length;
      } catch (e) {
        const message = e instanceof Error ? e.message : 'Request failed';
        setError(message);
      } finally {
        busyRef.current = false;
        setLoading(false);
        setLoadingMore(false);
        setRefreshing(false);
      }
    },
    [sort],
  );

  // Initial load + reload whenever the sort changes.
  useEffect(() => {
    load('replace');
  }, [load]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    load('replace');
  }, [load]);

  const loadMore = useCallback(() => {
    if (total == null || articles.length >= total) return;
    load('append');
  }, [load, total, articles.length]);

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Browse</Text>
        <Text style={styles.subtitle}>
          {total != null ? `${total} articles in the index` : 'Every scored article'}
        </Text>
        <View style={styles.segRow}>
          {SORTS.map((s) => (
            <Pressable
              key={s.key}
              onPress={() => setSort(s.key)}
              style={[styles.seg, sort === s.key && styles.segActive]}
            >
              <Text
                style={[
                  styles.segText,
                  sort === s.key && styles.segTextActive,
                ]}
              >
                {s.label}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {error && (
        <View style={styles.messageBox}>
          <Text style={styles.errorText}>
            {error} — check the API base in lib/api.ts.
          </Text>
        </View>
      )}

      <FlatList
        data={articles}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        onEndReached={loadMore}
        onEndReachedThreshold={0.5}
        ListEmptyComponent={
          !loading && !error ? (
            <Text style={styles.emptyText}>The feed is empty.</Text>
          ) : null
        }
        ListFooterComponent={
          loadingMore ? (
            <ActivityIndicator
              style={styles.footerSpinner}
              color={colors.primary}
            />
          ) : null
        }
        renderItem={({ item }) => (
          <ArticleCard
            title={item.title}
            blog={item.domain}
            score={item.combined_score}
            reason={item.reason}
            meta={`${fmtDate(item.published_at)} · ${item.source}`}
            onPress={() =>
              router.push({
                pathname: '/article/[id]',
                params: { id: String(item.id) },
              })
            }
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
    paddingBottom: 12,
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
  segRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
  },
  seg: {
    paddingHorizontal: 16,
    paddingVertical: 7,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  segActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  segText: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textSub,
  },
  segTextActive: {
    color: '#fff',
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
  footerSpinner: {
    paddingVertical: 16,
  },
});

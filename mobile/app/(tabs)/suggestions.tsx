import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Linking,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { listSuggestions, Suggestion } from '../../lib/api';
import { fmtDate } from '../../lib/format';
import { fonts, Palette, useTheme } from '../../lib/theme';

const SORTS = [
  { key: 'reddit_score', label: 'Top' },
  { key: 'discovered_at', label: 'New' },
] as const;

type SortKey = (typeof SORTS)[number]['key'];

export default function SuggestionsScreen() {
  const c = useTheme();
  const styles = useMemo(() => createStyles(c), [c]);
  const [sortBy, setSortBy] = useState<SortKey>('reddit_score');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listSuggestions(50, sortBy);
      setSuggestions(data ?? []);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Request failed';
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [sortBy]);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    load();
  }, [load]);

  const openUrl = useCallback((url: string) => {
    Linking.openURL(url).catch(() => {});
  }, []);

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Suggestions</Text>
        <Text style={styles.subtitle}>
          Articles you and the community found worth reading
        </Text>
        <View style={styles.segRow}>
          {SORTS.map((s) => (
            <Pressable
              key={s.key}
              onPress={() => setSortBy(s.key)}
              style={[styles.seg, sortBy === s.key && styles.segActive]}
            >
              <Text
                style={[
                  styles.segText,
                  sortBy === s.key && styles.segTextActive,
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
        data={suggestions}
        keyExtractor={(item) => item.url}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          !loading && !error ? (
            <Text style={styles.emptyText}>No suggestions yet.</Text>
          ) : null
        }
        renderItem={({ item }) => (
          <Pressable
            onPress={() => openUrl(item.url)}
            style={({ pressed }) => [
              styles.card,
              pressed && styles.cardPressed,
            ]}
          >
            <View style={styles.cardHeader}>
              <Text style={styles.cardSub} numberOfLines={1}>
                r/{item.subreddit}
              </Text>
              <Text style={styles.scoreText}>
                ▲ {item.reddit_score.toLocaleString()}
              </Text>
            </View>
            <Text style={styles.cardTitle} numberOfLines={3}>
              {item.title}
            </Text>
            <Text style={styles.cardMeta}>
              {fmtDate(item.discovered_at)}
              {item.net_votes ? ` · ${item.net_votes} vote(s)` : ''}
            </Text>
          </Pressable>
        )}
      />
    </SafeAreaView>
  );
}

const createStyles = (c: Palette) =>
  StyleSheet.create({
    safeArea: {
      flex: 1,
      backgroundColor: c.bg,
    },
    header: {
      paddingHorizontal: 20,
      paddingTop: 24,
      paddingBottom: 12,
    },
    title: {
      fontSize: 34,
      fontWeight: '400',
      fontFamily: fonts.serif,
      color: c.text,
      letterSpacing: -0.5,
    },
    subtitle: {
      marginTop: 4,
      fontSize: 13,
      fontFamily: fonts.sans,
      color: c.textSub,
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
      borderColor: c.border,
      backgroundColor: c.surface,
    },
    segActive: {
      backgroundColor: c.primary,
      borderColor: c.primary,
    },
    segText: {
      fontSize: 13,
      fontWeight: '600',
      fontFamily: fonts.sansSemibold,
      color: c.textSub,
    },
    segTextActive: {
      color: c.onPrimary,
    },
    messageBox: {
      marginHorizontal: 20,
      marginBottom: 10,
      padding: 12,
      borderRadius: 10,
      backgroundColor: c.dangerBg,
    },
    errorText: {
      color: c.dangerText,
      fontSize: 13,
      fontFamily: fonts.sans,
    },
    listContent: {
      paddingHorizontal: 20,
      paddingBottom: 32,
    },
    emptyText: {
      textAlign: 'center',
      color: c.textMuted,
      fontSize: 14,
      fontFamily: fonts.sans,
      paddingVertical: 40,
    },
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
    cardSub: {
      flex: 1,
      fontSize: 12,
      fontWeight: '700',
      fontFamily: fonts.sansBold,
      color: c.primary,
      textTransform: 'uppercase',
      letterSpacing: 0.5,
      marginRight: 8,
    },
    scoreText: {
      fontSize: 12,
      fontWeight: '800',
      fontFamily: fonts.sansBold,
      color: c.textSub,
      fontVariant: ['tabular-nums'],
    },
    cardTitle: {
      fontSize: 16,
      fontWeight: '400',
      fontFamily: fonts.serif,
      lineHeight: 22,
      color: c.text,
    },
    cardMeta: {
      marginTop: 8,
      fontSize: 12,
      fontFamily: fonts.sans,
      color: c.textMuted,
    },
  });

// API client for the Blog Feed backend (FastAPI at /api).
// Live API base — swap to a local URL (http://<server-ip>:8765/api) when
// running the backend locally during development.
export const API_BASE = 'https://blog-feed-aws.pranav-bansal.com/api';

// Article in search results (GET /api/search) — numeric id, same shape as the browse feed.
export type SearchArticle = {
  id: number;
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
  fts_rank?: number | null;
  semantic_relevance?: number | null;
};

export type SearchResponse = {
  query: string;
  count: number;
  limit: number;
  offset: number;
  min_score: number;
  search_type: string;
  corrected_query?: string;
  fallback?: boolean;
  articles: SearchArticle[];
};

// Article in the browse feed (GET /api/articles) — has numeric id.
export type FeedArticle = {
  id: number;
  url: string;
  title: string;
  domain: string;
  score: number | null;
  llm_score: number | null;
  combined_score: number | null;
  reason: string | null;
  keywords: string | null;
  source: string;
  published_at: string;
  llm_review_status: string;
};

export type ArticleListResponse = {
  total: number;
  limit: number;
  offset: number;
  articles: FeedArticle[];
};

// Full article row (GET /api/articles/{id}) — the whole DB row.
export type ArticleDetail = {
  id: number;
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
  text_content?: string | null;
  content_type?: string | null;
  reddit_suggestion_id?: string | null;
  added_by?: string | null;
  embedding_updated?: number | null;
};

// Reddit suggestion (GET /api/suggestions) — returns a bare array.
export type Suggestion = {
  url: string;
  domain: string;
  title: string;
  subreddit: string;
  reddit_score: number;
  reddit_comments?: number;
  heuristic_score?: number | null;
  heuristic_reason?: string | null;
  discovered_at: string;
  reviewed: string; // 'pending' | 'accepted' | 'rejected'
  llm_error?: string | null;
  reviewed_at?: string | null;
  upvotes?: number;
  downvotes?: number;
  net_votes?: number;
  total_votes?: number;
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API responded with HTTP ${res.status}`);
  return (await res.json()) as T;
}

export function searchArticles(q: string, limit = 30): Promise<SearchResponse> {
  return getJson(`/search?q=${encodeURIComponent(q)}&limit=${limit}`);
}

export function listArticles(
  offset: number,
  limit = 25,
  sort: 'fetched_at' | 'combined_score' = 'fetched_at',
): Promise<ArticleListResponse> {
  return getJson(`/articles?offset=${offset}&limit=${limit}&sort=${sort}`);
}

/** Fetch one article by numeric id or base64-encoded URL. */
export function getArticle(identifier: string): Promise<ArticleDetail> {
  return getJson(`/articles/${encodeURIComponent(identifier)}`);
}

export function listSuggestions(
  limit = 50,
  sortBy: 'discovered_at' | 'net_votes' | 'reddit_score' = 'discovered_at',
): Promise<Suggestion[]> {
  return getJson(`/suggestions?limit=${limit}&sort_by=${sortBy}`);
}

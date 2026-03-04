/**
 * API client for the AI Signals backend.
 *
 * All functions are async and throw on non-2xx responses.
 * Used in Next.js Server Components (no browser fetch needed).
 */
import type {
  ArticleDetail,
  ArticleListItem,
  DailyBrief,
  PaginatedResponse,
  SearchResult,
  Tag,
  Company,
  TrendSnapshot,
} from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const BASE = `${API_URL}/api/v1`

// Revalidation interval in seconds for ISR
export const REVALIDATE_SHORT  = 300   //  5 min — trending, latest
export const REVALIDATE_MEDIUM = 3600  //  1 hr  — topic/company pages
export const REVALIDATE_LONG   = 86400 // 24 hr  — static reference pages

async function fetchAPI<T>(
  path: string,
  options: RequestInit & { next?: { revalidate?: number; tags?: string[] } } = {},
): Promise<T> {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    const body = await res.text()
    throw new APIError(res.status, path, body)
  }

  return res.json() as Promise<T>
}

export class APIError extends Error {
  constructor(
    public status: number,
    public path: string,
    public body: string,
  ) {
    super(`API ${status} at ${path}`)
  }
}

// ── News ──────────────────────────────────────────────────────────────────────

export async function getTopArticles(limit = 10): Promise<ArticleListItem[]> {
  return fetchAPI(`/news/top?limit=${limit}`, {
    next: { revalidate: REVALIDATE_SHORT, tags: ['articles'] },
  })
}

export async function getArticles(params: {
  page?: number
  page_size?: number
  tag?: string
  company?: string
  min_score?: number
  reps_only?: boolean
}): Promise<PaginatedResponse<ArticleListItem>> {
  const q = new URLSearchParams()
  if (params.page)      q.set('page',      String(params.page))
  if (params.page_size) q.set('page_size', String(params.page_size))
  if (params.tag)       q.set('tag',       params.tag)
  if (params.company)   q.set('company',   params.company)
  if (params.min_score) q.set('min_score', String(params.min_score))
  if (params.reps_only !== undefined) q.set('reps_only', String(params.reps_only))

  return fetchAPI(`/news?${q}`, {
    next: { revalidate: REVALIDATE_SHORT, tags: ['articles'] },
  })
}

export async function getArticle(slug: string): Promise<ArticleDetail> {
  return fetchAPI(`/news/${slug}`, {
    next: { revalidate: REVALIDATE_MEDIUM, tags: [`article-${slug}`] },
  })
}

// ── Briefs ────────────────────────────────────────────────────────────────────

export async function getLatestBrief(): Promise<DailyBrief> {
  return fetchAPI('/briefs/latest', {
    next: { revalidate: REVALIDATE_SHORT, tags: ['briefs'] },
  })
}

export async function getBrief(date: string): Promise<DailyBrief> {
  return fetchAPI(`/briefs/${date}`, {
    next: { revalidate: REVALIDATE_MEDIUM, tags: [`brief-${date}`] },
  })
}

export async function listBriefs(page = 1, pageSize = 20) {
  return fetchAPI<PaginatedResponse<DailyBrief>>(
    `/briefs?page=${page}&page_size=${pageSize}`,
    { next: { revalidate: REVALIDATE_MEDIUM, tags: ['briefs'] } },
  )
}

// ── Trends ────────────────────────────────────────────────────────────────────

export async function getTrendingTags(limit = 20): Promise<Tag[]> {
  return fetchAPI(`/trends/tags?limit=${limit}`, {
    next: { revalidate: REVALIDATE_SHORT, tags: ['trends'] },
  })
}

export async function getTrendingCompanies(limit = 10): Promise<Company[]> {
  return fetchAPI(`/trends/companies?limit=${limit}`, {
    next: { revalidate: REVALIDATE_SHORT, tags: ['trends'] },
  })
}

export async function getTrendHistory(
  entityType: string,
  slug: string,
  days = 30,
): Promise<TrendSnapshot[]> {
  return fetchAPI(`/trends/history/${entityType}/${slug}?days=${days}`, {
    next: { revalidate: REVALIDATE_MEDIUM },
  })
}

// ── Topics ────────────────────────────────────────────────────────────────────

export async function getAllTopics(): Promise<Tag[]> {
  return fetchAPI('/topics', {
    next: { revalidate: REVALIDATE_MEDIUM, tags: ['topics'] },
  })
}

export async function getTopic(slug: string): Promise<Tag> {
  return fetchAPI(`/topics/${slug}`, {
    next: { revalidate: REVALIDATE_MEDIUM, tags: [`topic-${slug}`] },
  })
}

export async function getTopicArticles(
  slug: string,
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<ArticleListItem>> {
  return fetchAPI(`/topics/${slug}/news?page=${page}&page_size=${pageSize}`, {
    next: { revalidate: REVALIDATE_SHORT, tags: [`topic-${slug}`] },
  })
}

// ── Companies ─────────────────────────────────────────────────────────────────

export async function getAllCompanies(): Promise<Company[]> {
  return fetchAPI('/companies', {
    next: { revalidate: REVALIDATE_MEDIUM, tags: ['companies'] },
  })
}

export async function getCompany(slug: string): Promise<Company> {
  return fetchAPI(`/companies/${slug}`, {
    next: { revalidate: REVALIDATE_MEDIUM, tags: [`company-${slug}`] },
  })
}

export async function getCompanyArticles(
  slug: string,
  page = 1,
): Promise<PaginatedResponse<ArticleListItem>> {
  return fetchAPI(`/companies/${slug}/news?page=${page}`, {
    next: { revalidate: REVALIDATE_SHORT },
  })
}

// ── Search ────────────────────────────────────────────────────────────────────

export async function searchArticles(
  query: string,
  params: { tag?: string; page?: number } = {},
): Promise<SearchResult> {
  const q = new URLSearchParams({ q: query })
  if (params.tag)  q.set('tag', params.tag)
  if (params.page) q.set('page', String(params.page))

  // Search is never cached — always fresh
  return fetchAPI(`/search?${q}`, { cache: 'no-store' })
}

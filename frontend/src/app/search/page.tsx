import type { Metadata } from 'next'
import Link from 'next/link'
import { searchArticles } from '@/lib/api'
import { ArticleCard } from '@/components/news/ArticleCard'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState } from '@/components/ui/EmptyState'

export const metadata: Metadata = {
  title: 'Search AI News',
}

interface Props {
  searchParams: { q?: string; page?: string; tag?: string }
}

export default async function SearchPage({ searchParams }: Props) {
  const query = searchParams.q?.trim() ?? ''
  const page = Number(searchParams.page ?? 1)
  const tag = searchParams.tag

  let result = null
  if (query) {
    try {
      result = await searchArticles(query, { tag, page })
    } catch {
      result = null
    }
  }

  const pageSize = 20
  const totalPages = result ? Math.ceil(result.total / pageSize) : 0
  const hasNext = page < totalPages
  const hasPrev = page > 1

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-text-primary">Search</h1>
      </header>

      {/* Search form */}
      <form method="GET" action="/search" className="flex gap-2">
        <input
          type="search"
          name="q"
          defaultValue={query}
          placeholder="Search AI news…"
          autoFocus
          className="flex-1 px-3 py-2 rounded-md border border-surface-border text-sm bg-surface-card text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-brand-400 focus:border-brand-400"
        />
        <button type="submit" className="btn-primary">
          Search
        </button>
      </form>

      {/* Results */}
      {query && result && (
        <div>
          <p className="text-xs font-mono text-text-muted mb-4">
            {result.total} results for <span className="text-brand-300">"{result.query}"</span>
            {result.took_ms > 0 && (
              <span className="ml-1 text-text-muted">({result.took_ms}ms)</span>
            )}
          </p>

          {result.articles.length === 0 ? (
            <EmptyState
              title="No results found"
              description="Try different keywords or browse by topic."
            />
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {result.articles.map((article) => (
                  <ArticleCard key={article.id} article={article} />
                ))}
              </div>

              {(hasNext || hasPrev) && (
                <Pagination
                  page={page}
                  hasNext={hasNext}
                  hasPrev={hasPrev}
                  baseUrl="/search"
                  extraParams={query ? { q: query } : {}}
                />
              )}
            </>
          )}
        </div>
      )}

      {!query && (
        <div className="text-center py-12">
          <p className="text-xs font-mono text-text-muted">Enter a query to search AI news articles.</p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {['LLM', 'GPT-4', 'Claude', 'open source', 'robotics', 'multimodal'].map((term) => (
              <a
                key={term}
                href={`/search?q=${encodeURIComponent(term)}`}
                className="badge badge-gray hover:border-brand-400/40 hover:text-brand-300 transition-colors no-underline"
              >
                {term}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

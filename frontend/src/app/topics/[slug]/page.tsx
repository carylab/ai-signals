import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getTopic, getTopicArticles, REVALIDATE_SHORT } from '@/lib/api'
import { formatScore, scoreBadgeColor } from '@/lib/utils'
import { ArticleCard } from '@/components/news/ArticleCard'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState } from '@/components/ui/EmptyState'

export const revalidate = REVALIDATE_SHORT

interface Props {
  params: { slug: string }
  searchParams: { page?: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  try {
    const topic = await getTopic(params.slug)
    return {
      title: `${topic.name} — AI News`,
      description: topic.description ?? `Latest AI news about ${topic.name}.`,
    }
  } catch {
    return { title: 'Topic' }
  }
}

export default async function TopicPage({ params, searchParams }: Props) {
  let topic
  try {
    topic = await getTopic(params.slug)
  } catch {
    notFound()
  }

  const page = Number(searchParams.page ?? 1)
  const articlesPage = await getTopicArticles(params.slug, page, 20)
  const scoreClass = scoreBadgeColor(topic.trend_score)

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-gray-400">
        <Link href="/" className="hover:text-brand-600">Home</Link>
        <span>/</span>
        <Link href="/topics" className="hover:text-brand-600">Topics</Link>
        <span>/</span>
        <span className="text-gray-600">{topic.name}</span>
      </nav>

      {/* Header */}
      <header className="card">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="badge badge-blue capitalize">{topic.category}</span>
              <span className={`badge ${scoreClass}`}>
                Trend {formatScore(topic.trend_score)}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{topic.name}</h1>
            {topic.description && (
              <p className="text-sm text-gray-500 mt-2">{topic.description}</p>
            )}
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-2xl font-bold text-gray-900">{topic.news_count_7d}</p>
            <p className="text-xs text-gray-400">articles this week</p>
          </div>
        </div>
      </header>

      {/* Articles grid */}
      {articlesPage.data.length === 0 ? (
        <EmptyState title="No articles found" />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {articlesPage.data.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>

          <Pagination
            page={page}
            hasNext={articlesPage.has_next}
            hasPrev={articlesPage.has_prev}
            baseUrl={`/topics/${params.slug}`}
          />
        </>
      )}
    </div>
  )
}

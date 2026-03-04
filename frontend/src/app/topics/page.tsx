import type { Metadata } from 'next'
import Link from 'next/link'
import { getAllTopics, REVALIDATE_MEDIUM } from '@/lib/api'
import { scoreBadgeColor } from '@/lib/utils'

export const revalidate = REVALIDATE_MEDIUM

export const metadata: Metadata = {
  title: 'AI Topics',
  description: 'Browse all AI topics and categories tracked by AI Signals.',
}

const CATEGORY_ORDER = ['technology', 'research', 'industry', 'applications', 'policy', 'other']

export default async function TopicsPage() {
  const topics = await getAllTopics()

  // Group by category
  const grouped = topics.reduce<Record<string, typeof topics>>((acc, topic) => {
    const cat = topic.category ?? 'other'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(topic)
    return acc
  }, {})

  const categories = CATEGORY_ORDER.filter((c) => grouped[c]?.length > 0)
  const extraCats = Object.keys(grouped).filter((c) => !CATEGORY_ORDER.includes(c))

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Topics</h1>
        <p className="text-sm text-gray-500 mt-1">
          {topics.length} topics tracked across AI news.
        </p>
      </header>

      {[...categories, ...extraCats].map((category) => (
        <section key={category}>
          <p className="section-title capitalize">{category}</p>
          <div className="flex flex-wrap gap-2">
            {(grouped[category] ?? [])
              .sort((a, b) => b.trend_score - a.trend_score)
              .map((topic) => {
                const scoreClass = scoreBadgeColor(topic.trend_score)
                return (
                  <Link
                    key={topic.slug}
                    href={`/topics/${topic.slug}`}
                    className={`badge ${scoreClass} hover:opacity-80 transition-opacity no-underline`}
                  >
                    {topic.name}
                    {topic.news_count_7d > 0 && (
                      <span className="ml-1 opacity-60">{topic.news_count_7d}</span>
                    )}
                  </Link>
                )
              })}
          </div>
        </section>
      ))}
    </div>
  )
}

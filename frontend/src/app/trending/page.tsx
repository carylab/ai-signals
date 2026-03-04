import type { Metadata } from 'next'
import Link from 'next/link'
import { getTrendingTags, getTrendingCompanies, REVALIDATE_SHORT } from '@/lib/api'
import { formatScore, scoreBadgeColor } from '@/lib/utils'
import { TrendingCompanyRow } from '@/components/trends/TrendingWidgets'

export const revalidate = REVALIDATE_SHORT

export const metadata: Metadata = {
  title: 'Trending in AI',
  description: 'Top trending AI topics, companies, and models right now.',
}

export default async function TrendingPage() {
  const [tagsResult, companiesResult] = await Promise.allSettled([
    getTrendingTags(30),
    getTrendingCompanies(20),
  ])

  const tags = tagsResult.status === 'fulfilled' ? tagsResult.value : []
  const companies = companiesResult.status === 'fulfilled' ? companiesResult.value : []

  // Group tags by category
  const grouped = tags.reduce<Record<string, typeof tags>>((acc, tag) => {
    const cat = tag.category ?? 'other'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(tag)
    return acc
  }, {})

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Trending</h1>
        <p className="text-sm text-gray-500 mt-1">
          What's moving in AI right now — based on article velocity and discussion.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tag trends by category */}
        <div className="lg:col-span-2 space-y-6">
          {Object.entries(grouped)
            .sort(([, a], [, b]) => b.length - a.length)
            .map(([category, catTags]) => (
              <section key={category}>
                <p className="section-title capitalize">{category}</p>
                <div className="flex flex-wrap gap-2">
                  {catTags
                    .sort((a, b) => b.trend_score - a.trend_score)
                    .map((tag) => {
                      const scoreClass = scoreBadgeColor(tag.trend_score)
                      return (
                        <Link
                          key={tag.slug}
                          href={`/topics/${tag.slug}`}
                          className={`badge ${scoreClass} hover:opacity-80 transition-opacity no-underline`}
                        >
                          {tag.name}
                          <span className="ml-1 opacity-60 text-[9px]">
                            {tag.news_count_7d}↑
                          </span>
                        </Link>
                      )
                    })}
                </div>
              </section>
            ))}
        </div>

        {/* Company ranking */}
        <aside>
          <p className="section-title">Companies</p>
          <div className="card p-0">
            {companies.map((company, i) => (
              <div key={company.slug} className="px-4">
                <TrendingCompanyRow company={company} rank={i + 1} />
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  )
}

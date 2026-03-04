import type { Metadata } from 'next'
import { Suspense } from 'react'
import {
  getTopArticles,
  getLatestBrief,
  getTrendingTags,
  getTrendingCompanies,
  getArticles,
  REVALIDATE_SHORT,
} from '@/lib/api'
import { ArticleCard } from '@/components/news/ArticleCard'
import { ArticleRow } from '@/components/news/ArticleRow'
import { BriefHero } from '@/components/brief/BriefCard'
import { TrendingTagsBar, TrendingCompanyRow } from '@/components/trends/TrendingWidgets'
import { SITE_NAME } from '@/lib/utils'

export const revalidate = REVALIDATE_SHORT

export const metadata: Metadata = {
  title: `${SITE_NAME} — AI Industry Intelligence`,
}

export default async function HomePage() {
  const [topArticles, latestBrief, trendingTags, trendingCompanies, latestPage] =
    await Promise.allSettled([
      getTopArticles(12),
      getLatestBrief(),
      getTrendingTags(20),
      getTrendingCompanies(8),
      getArticles({ page: 1, page_size: 20, reps_only: true }),
    ])

  const top = topArticles.status === 'fulfilled' ? topArticles.value : []
  const brief = latestBrief.status === 'fulfilled' ? latestBrief.value : null
  const tags = trendingTags.status === 'fulfilled' ? trendingTags.value : []
  const companies = trendingCompanies.status === 'fulfilled' ? trendingCompanies.value : []
  const latest = latestPage.status === 'fulfilled' ? latestPage.value.data : []

  const [heroArticle, ...restTop] = top

  return (
    <div className="space-y-8">
      {/* Daily brief banner */}
      {brief && <BriefHero brief={brief} />}

      {/* Trending tags */}
      {tags.length > 0 && (
        <section>
          <p className="section-title">
            <span>Trending Topics</span>
          </p>
          <TrendingTagsBar tags={tags} />
        </section>
      )}

      {/* Main layout: articles + sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Primary column */}
        <div className="lg:col-span-2 space-y-4">
          <p className="section-title">Top Stories</p>

          {heroArticle && (
            <ArticleCard article={heroArticle} hero />
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {restTop.slice(0, 6).map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* Latest stream */}
          <section>
            <p className="section-title">Latest</p>
            <div className="card p-0 divide-y divide-surface-border">
              {latest.slice(0, 10).map((article, i) => (
                <div key={article.id} className="px-4">
                  <ArticleRow article={article} rank={i + 1} />
                </div>
              ))}
            </div>
          </section>

          {/* Companies */}
          {companies.length > 0 && (
            <section>
              <p className="section-title">Companies in Focus</p>
              <div className="card p-0">
                {companies.map((company, i) => (
                  <div key={company.slug} className="px-4">
                    <TrendingCompanyRow company={company} rank={i + 1} />
                  </div>
                ))}
              </div>
            </section>
          )}
        </aside>
      </div>
    </div>
  )
}

import type { Metadata } from 'next'
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
          <p className="section-title">Trending Topics</p>
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

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
            <div className="rounded-lg border border-surface-border bg-surface-card overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2 border-b border-surface-border bg-surface-subtle/40">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
                <span className="text-xs font-mono text-text-muted">feed.live</span>
              </div>
              <div className="divide-y divide-surface-border/50">
                {latest.slice(0, 10).map((article, i) => (
                  <div key={article.id} className="px-4">
                    <ArticleRow article={article} rank={i + 1} />
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Companies */}
          {companies.length > 0 && (
            <section>
              <p className="section-title">Companies in Focus</p>
              <div className="rounded-lg border border-surface-border bg-surface-card overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-2 border-b border-surface-border bg-surface-subtle/40">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  <span className="text-xs font-mono text-text-muted">companies.ranked</span>
                </div>
                <div className="px-4">
                  {companies.map((company, i) => (
                    <TrendingCompanyRow key={company.slug} company={company} rank={i + 1} />
                  ))}
                </div>
              </div>
            </section>
          )}
        </aside>
      </div>
    </div>
  )
}

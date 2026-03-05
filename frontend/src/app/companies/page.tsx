import type { Metadata } from 'next'
import Link from 'next/link'
import { getAllCompanies, REVALIDATE_MEDIUM } from '@/lib/api'
import { formatScore, scoreBadgeColor } from '@/lib/utils'

export const revalidate = REVALIDATE_MEDIUM

export const metadata: Metadata = {
  title: 'AI Companies',
  description: 'AI companies tracked by AI Signals — ranked by recent news activity.',
}

export default async function CompaniesPage() {
  const companies = await getAllCompanies()
  const sorted = [...companies].sort((a, b) => b.trend_score - a.trend_score)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-text-primary">Companies</h1>
        <p className="text-xs font-mono text-text-muted mt-1">
          {companies.length} AI companies tracked — ranked by trend score.
        </p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {sorted.map((company) => {
          const scoreClass = scoreBadgeColor(company.trend_score)
          return (
            <Link
              key={company.slug}
              href={`/companies/${company.slug}`}
              className="card flex flex-col gap-2 no-underline group"
            >
              <div className="flex items-start justify-between gap-2">
                <h2 className="text-sm font-semibold text-text-primary group-hover:text-brand-300 transition-colors">
                  {company.name}
                  {company.is_verified && (
                    <span className="ml-1 text-cyan-400 text-xs">✓</span>
                  )}
                </h2>
                <span className={`badge ${scoreClass} text-xs flex-shrink-0`}>
                  {formatScore(company.trend_score)}
                </span>
              </div>

              {company.description && (
                <p className="text-xs text-text-muted line-clamp-2">{company.description}</p>
              )}

              <p className="text-xs font-mono text-text-muted mt-auto">
                {company.news_count_7d} articles / 7d
              </p>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getCompany, getCompanyArticles, REVALIDATE_SHORT } from '@/lib/api'
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
    const company = await getCompany(params.slug)
    return {
      title: `${company.name} — AI News`,
      description: company.description ?? `Latest AI news about ${company.name}.`,
    }
  } catch {
    return { title: 'Company' }
  }
}

export default async function CompanyPage({ params, searchParams }: Props) {
  let company
  try {
    company = await getCompany(params.slug)
  } catch {
    notFound()
  }

  const page = Number(searchParams.page ?? 1)
  const articlesPage = await getCompanyArticles(params.slug, page)
  const scoreClass = scoreBadgeColor(company.trend_score)

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-gray-400">
        <Link href="/" className="hover:text-brand-600">Home</Link>
        <span>/</span>
        <Link href="/companies" className="hover:text-brand-600">Companies</Link>
        <span>/</span>
        <span className="text-gray-600">{company.name}</span>
      </nav>

      {/* Header */}
      <header className="card">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className={`badge ${scoreClass}`}>
                Trend {formatScore(company.trend_score)}
              </span>
              {company.is_verified && (
                <span className="badge badge-blue">Verified</span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-gray-900">
              {company.name}
            </h1>
            {company.description && (
              <p className="text-sm text-gray-500 mt-2">{company.description}</p>
            )}
            {company.website && (
              <a
                href={company.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-brand-600 hover:text-brand-700 mt-1 inline-block no-underline"
              >
                {company.website.replace('https://', '')} ↗
              </a>
            )}
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-2xl font-bold text-gray-900">{company.news_count_7d}</p>
            <p className="text-xs text-gray-400">articles this week</p>
          </div>
        </div>
      </header>

      {/* Articles */}
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
            baseUrl={`/companies/${params.slug}`}
          />
        </>
      )}
    </div>
  )
}

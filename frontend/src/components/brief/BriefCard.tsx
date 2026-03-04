import Link from 'next/link'
import Image from 'next/image'
import type { DailyBrief } from '@/lib/types'
import { formatDate, formatRelativeTime } from '@/lib/utils'

interface BriefCardProps {
  brief: DailyBrief
}

export function BriefCard({ brief }: BriefCardProps) {
  return (
    <article className="card">
      <div className="flex items-center justify-between mb-3">
        <Link href={`/daily/${brief.date}`} className="no-underline">
          <h2 className="text-base font-semibold text-gray-900 hover:text-brand-600 transition-colors">
            {formatDate(brief.date)} Daily Brief
          </h2>
        </Link>
        <span className="text-xs text-gray-400">{brief.total_articles_published} articles</span>
      </div>

      <Link href={`/daily/${brief.date}`} className="no-underline">
        <p className="text-sm font-medium text-gray-800 mb-2 hover:text-brand-600 transition-colors">
          {brief.headline}
        </p>
      </Link>

      <p className="text-sm text-gray-600 leading-relaxed line-clamp-3 mb-3">
        {brief.summary}
      </p>

      {brief.key_themes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {brief.key_themes.slice(0, 4).map((theme, i) => (
            <span key={i} className="badge badge-gray text-[10px]">
              {theme}
            </span>
          ))}
        </div>
      )}
    </article>
  )
}

interface BriefHeroProps {
  brief: DailyBrief
}

export function BriefHero({ brief }: BriefHeroProps) {
  return (
    <section className="card bg-gradient-to-br from-brand-600 to-brand-700 text-white border-0 mb-6">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-blue-200 mb-1">
            Daily Brief · {formatDate(brief.date)}
          </p>
          <h1 className="text-xl font-bold leading-snug">{brief.headline}</h1>
        </div>
        <Link
          href={`/daily/${brief.date}`}
          className="flex-shrink-0 btn bg-white/10 text-white hover:bg-white/20 border border-white/20 no-underline text-xs"
        >
          Full Brief →
        </Link>
      </div>

      <p className="text-sm text-blue-100 leading-relaxed mb-4">{brief.summary}</p>

      {brief.key_themes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs text-blue-200 mr-1">Key themes:</span>
          {brief.key_themes.map((theme, i) => (
            <span key={i} className="badge bg-white/15 text-blue-50 text-[10px]">
              {theme}
            </span>
          ))}
        </div>
      )}
    </section>
  )
}

import Link from 'next/link'
import type { DailyBrief } from '@/lib/types'
import { formatDate } from '@/lib/utils'

interface BriefCardProps {
  brief: DailyBrief
}

export function BriefCard({ brief }: BriefCardProps) {
  return (
    <article className="card">
      <div className="flex items-center justify-between mb-3">
        <Link href={`/daily/${brief.date}`} className="no-underline">
          <h2 className="text-sm font-semibold text-text-primary hover:text-brand-300 transition-colors">
            {formatDate(brief.date)} Daily Brief
          </h2>
        </Link>
        <span className="text-xs font-mono text-text-muted">{brief.total_articles_published} articles</span>
      </div>

      <Link href={`/daily/${brief.date}`} className="no-underline">
        <p className="text-xs font-medium text-text-primary mb-2 hover:text-brand-300 transition-colors leading-snug">
          {brief.headline}
        </p>
      </Link>

      <p className="text-xs text-text-secondary leading-relaxed line-clamp-3 mb-3">
        {brief.summary}
      </p>

      {brief.key_themes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {brief.key_themes.slice(0, 4).map((theme, i) => (
            <span key={i} className="badge badge-gray text-xs">
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
    <section className="relative overflow-hidden rounded-lg border border-brand-800/60 bg-surface-card mb-6">
      {/* Glow background */}
      <div className="absolute inset-0 bg-gradient-to-br from-brand-400/5 via-transparent to-cyan-400/5 pointer-events-none" />
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-brand-400/60 via-cyan-400/40 to-transparent" />

      {/* Terminal-style header bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-surface-border/60 bg-surface-subtle/30">
        <span className="dot bg-red-500/60" />
        <span className="dot bg-amber-500/60" />
        <span className="dot bg-brand-400/60" />
        <span className="ml-2 text-xs font-mono text-text-muted">
          daily_brief.md — {formatDate(brief.date)}
        </span>
        <span className="ml-auto text-xs font-mono text-brand-400/60 animate-pulse-slow">
          ● LIVE
        </span>
      </div>

      <div className="p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex-1">
            <p className="text-xs font-mono font-semibold uppercase tracking-widest text-brand-400/70 mb-2">
              <span className="text-brand-400/40">$</span> cat daily_brief/{brief.date}.md
            </p>
            <h1 className="text-base font-bold leading-snug text-text-primary">
              {brief.headline}
            </h1>
          </div>
          <Link
            href={`/daily/${brief.date}`}
            className="flex-shrink-0 btn-primary text-xs no-underline"
          >
            Full Brief →
          </Link>
        </div>

        <p className="text-xs text-text-secondary leading-relaxed mb-4">{brief.summary}</p>

        {brief.key_themes.length > 0 && (
          <div className="flex flex-wrap gap-1.5 items-center">
            <span className="text-xs font-mono text-text-muted mr-1">
              <span className="text-brand-400/40">#</span> themes:
            </span>
            {brief.key_themes.map((theme, i) => (
              <span key={i} className="badge badge-gray text-xs">
                {theme}
              </span>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

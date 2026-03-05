import Link from 'next/link'
import Image from 'next/image'
import type { ArticleListItem } from '@/lib/types'
import { formatRelativeTime, scoreBadgeColor, formatScore, truncate } from '@/lib/utils'

interface ArticleCardProps {
  article: ArticleListItem
  hero?: boolean
}

export function ArticleCard({ article, hero = false }: ArticleCardProps) {
  const scoreClass = scoreBadgeColor(article.final_score)
  const primaryTag = article.tags[0]
  const ago = formatRelativeTime(article.published_at)

  if (hero) {
    return (
      <article className="relative overflow-hidden rounded-lg border border-surface-border bg-surface-card hover:border-brand-800 transition-all duration-300 group">
        {/* Top accent bar */}
        <div className="h-px bg-gradient-to-r from-brand-400/60 via-cyan-400/40 to-transparent" />

        <div className="flex flex-col md:flex-row gap-0">
          {article.image_url && (
            <div className="relative w-full md:w-72 h-48 md:h-auto flex-shrink-0 overflow-hidden">
              <Image
                src={article.image_url}
                alt={article.title}
                fill
                className="object-cover opacity-70 group-hover:opacity-80 transition-opacity duration-300"
                sizes="(max-width: 768px) 100vw, 288px"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-transparent to-surface-card/80 hidden md:block" />
              <div className="absolute inset-0 bg-gradient-to-t from-surface-card/80 to-transparent md:hidden" />
            </div>
          )}

          <div className="p-5 flex flex-col gap-3 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              {primaryTag && (
                <Link href={`/topics/${primaryTag.slug}`} className="badge badge-blue no-underline">
                  {primaryTag.name}
                </Link>
              )}
              <span className={`badge ${scoreClass}`}>
                SIG {formatScore(article.final_score)}
              </span>
              <span className="text-xs font-mono text-text-muted ml-auto">{ago}</span>
            </div>

            <Link href={`/news/${article.slug}`} className="no-underline group/title">
              <h2 className="text-base font-semibold text-text-primary group-hover/title:text-brand-300 transition-colors leading-snug">
                {article.title}
              </h2>
            </Link>

            {article.summary && (
              <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">
                {truncate(article.summary, 240)}
              </p>
            )}

            <div className="flex items-center gap-3 mt-auto pt-1 border-t border-surface-border/50">
              {article.author && (
                <span className="text-xs font-mono text-text-muted">{article.author}</span>
              )}
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-mono text-brand-400/60 hover:text-brand-300 ml-auto no-underline transition-colors"
              >
                SOURCE ↗
              </a>
            </div>
          </div>
        </div>
      </article>
    )
  }

  return (
    <article className="relative overflow-hidden rounded-lg border border-surface-border bg-surface-card hover:border-brand-800 hover:bg-surface-hover transition-all duration-200 group p-4 flex gap-3">
      {article.image_url && (
        <div className="relative w-16 h-12 flex-shrink-0 rounded overflow-hidden">
          <Image
            src={article.image_url}
            alt={article.title}
            fill
            className="object-cover opacity-60 group-hover:opacity-75 transition-opacity"
            sizes="64px"
          />
        </div>
      )}

      <div className="flex flex-col gap-1.5 flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          {primaryTag && (
            <Link href={`/topics/${primaryTag.slug}`} className="badge badge-blue no-underline text-xs">
              {primaryTag.name}
            </Link>
          )}
          <span className={`badge ${scoreClass} text-xs`}>
            {formatScore(article.final_score)}
          </span>
        </div>

        <Link href={`/news/${article.slug}`} className="no-underline group/title">
          <h3 className="text-sm font-medium text-text-primary group-hover/title:text-brand-300 transition-colors leading-snug line-clamp-2">
            {article.title}
          </h3>
        </Link>

        <div className="flex items-center gap-2 mt-auto">
          <span className="text-xs font-mono text-text-muted">{ago}</span>
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-mono text-text-muted hover:text-brand-300 ml-auto no-underline transition-colors"
          >
            ↗
          </a>
        </div>
      </div>
    </article>
  )
}

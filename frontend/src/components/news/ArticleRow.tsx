import Link from 'next/link'
import type { ArticleListItem } from '@/lib/types'
import { formatRelativeTime, scoreBadgeColor, formatScore } from '@/lib/utils'

interface ArticleRowProps {
  article: ArticleListItem
  rank?: number
}

export function ArticleRow({ article, rank }: ArticleRowProps) {
  const scoreClass = scoreBadgeColor(article.final_score)
  const ago = formatRelativeTime(article.published_at)

  return (
    <div className="flex items-start gap-3 py-3 border-b border-surface-border/50 last:border-0 group">
      {rank !== undefined && (
        <span className="text-sm font-mono font-bold text-brand-400/20 w-6 flex-shrink-0 text-center leading-snug mt-0.5 group-hover:text-brand-400/40 transition-colors">
          {String(rank).padStart(2, '0')}
        </span>
      )}

      <div className="flex-1 min-w-0">
        <Link href={`/news/${article.slug}`} className="no-underline group/title">
          <p className="text-sm font-medium text-text-primary group-hover/title:text-brand-300 transition-colors leading-snug line-clamp-2">
            {article.title}
          </p>
        </Link>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          {article.tags.slice(0, 2).map((tag) => (
            <Link key={tag.slug} href={`/topics/${tag.slug}`} className="badge badge-gray no-underline text-xs">
              {tag.name}
            </Link>
          ))}
          <span className="text-xs font-mono text-text-muted">{ago}</span>
        </div>
      </div>

      <div className="flex-shrink-0 text-right flex flex-col items-end gap-1">
        <span className={`badge ${scoreClass} text-xs`}>
          {formatScore(article.final_score)}
        </span>
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-mono text-text-muted hover:text-brand-300 no-underline transition-colors"
        >
          ↗
        </a>
      </div>
    </div>
  )
}

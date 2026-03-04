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
    <div className="flex items-start gap-3 py-3 border-b border-surface-border last:border-0">
      {rank !== undefined && (
        <span className="text-lg font-bold text-gray-200 w-7 flex-shrink-0 text-center leading-snug">
          {rank}
        </span>
      )}

      <div className="flex-1 min-w-0">
        <Link href={`/news/${article.slug}`} className="no-underline group">
          <p className="text-sm font-medium text-gray-900 group-hover:text-brand-600 transition-colors leading-snug line-clamp-2">
            {article.title}
          </p>
        </Link>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          {article.tags.slice(0, 2).map((tag) => (
            <Link key={tag.slug} href={`/topics/${tag.slug}`} className="badge badge-gray no-underline text-[10px]">
              {tag.name}
            </Link>
          ))}
          <span className="text-xs text-gray-400">{ago}</span>
        </div>
      </div>

      <div className="flex-shrink-0 text-right">
        <span className={`badge ${scoreClass} text-[10px]`}>
          {formatScore(article.final_score)}
        </span>
        <div className="mt-1">
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-400 hover:text-brand-600 no-underline"
          >
            ↗
          </a>
        </div>
      </div>
    </div>
  )
}

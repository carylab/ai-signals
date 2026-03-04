import Link from 'next/link'
import Image from 'next/image'
import type { ArticleListItem } from '@/lib/types'
import { formatRelativeTime, scoreBadgeColor, formatScore, truncate } from '@/lib/utils'

interface ArticleCardProps {
  article: ArticleListItem
  /** Show full-width hero layout for top article */
  hero?: boolean
}

export function ArticleCard({ article, hero = false }: ArticleCardProps) {
  const scoreClass = scoreBadgeColor(article.final_score)
  const primaryTag = article.tags[0]
  const ago = formatRelativeTime(article.published_at)

  if (hero) {
    return (
      <article className="card p-0 overflow-hidden flex flex-col md:flex-row gap-0">
        {article.image_url && (
          <div className="relative w-full md:w-72 h-48 md:h-auto flex-shrink-0">
            <Image
              src={article.image_url}
              alt={article.title}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 288px"
            />
          </div>
        )}
        <div className="p-5 flex flex-col gap-2 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            {primaryTag && (
              <Link href={`/topics/${primaryTag.slug}`} className="badge badge-blue no-underline">
                {primaryTag.name}
              </Link>
            )}
            <span className={`badge ${scoreClass} no-underline`}>
              Score {formatScore(article.final_score)}
            </span>
          </div>

          <Link href={`/news/${article.slug}`} className="no-underline group">
            <h2 className="text-lg font-semibold text-gray-900 group-hover:text-brand-600 transition-colors leading-snug">
              {article.title}
            </h2>
          </Link>

          {article.summary && (
            <p className="text-sm text-gray-600 leading-relaxed line-clamp-3">
              {truncate(article.summary, 240)}
            </p>
          )}

          <div className="flex items-center gap-3 mt-auto pt-2">
            <span className="text-xs text-gray-400">{ago}</span>
            {article.author && (
              <span className="text-xs text-gray-400">· {article.author}</span>
            )}
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-brand-600 hover:text-brand-700 ml-auto no-underline"
            >
              Source ↗
            </a>
          </div>
        </div>
      </article>
    )
  }

  return (
    <article className="card flex gap-3">
      {article.image_url && (
        <div className="relative w-20 h-16 flex-shrink-0 rounded overflow-hidden">
          <Image
            src={article.image_url}
            alt={article.title}
            fill
            className="object-cover"
            sizes="80px"
          />
        </div>
      )}

      <div className="flex flex-col gap-1 flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          {primaryTag && (
            <Link href={`/topics/${primaryTag.slug}`} className="badge badge-blue no-underline text-[10px]">
              {primaryTag.name}
            </Link>
          )}
          <span className={`badge ${scoreClass} text-[10px]`}>
            {formatScore(article.final_score)}
          </span>
        </div>

        <Link href={`/news/${article.slug}`} className="no-underline group">
          <h3 className="text-sm font-medium text-gray-900 group-hover:text-brand-600 transition-colors leading-snug line-clamp-2">
            {article.title}
          </h3>
        </Link>

        <div className="flex items-center gap-2 mt-auto">
          <span className="text-xs text-gray-400">{ago}</span>
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-400 hover:text-brand-600 ml-auto no-underline"
          >
            ↗
          </a>
        </div>
      </div>
    </article>
  )
}

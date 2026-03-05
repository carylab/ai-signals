import Link from 'next/link'
import type { Tag, Company } from '@/lib/types'
import { formatScore, scoreBadgeColor } from '@/lib/utils'

interface TrendTagChipProps {
  tag: Tag
}

export function TrendTagChip({ tag }: TrendTagChipProps) {
  const scoreClass = scoreBadgeColor(tag.trend_score)
  return (
    <Link
      href={`/topics/${tag.slug}`}
      className={`badge ${scoreClass} hover:brightness-125 transition-all no-underline`}
    >
      {tag.name}
      <span className="ml-1.5 font-mono text-xs opacity-60">{tag.news_count_7d}↑</span>
    </Link>
  )
}

interface TrendingTagsBarProps {
  tags: Tag[]
}

export function TrendingTagsBar({ tags }: TrendingTagsBarProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <TrendTagChip key={tag.slug} tag={tag} />
      ))}
    </div>
  )
}

interface TrendingCompanyRowProps {
  company: Company
  rank: number
}

export function TrendingCompanyRow({ company, rank }: TrendingCompanyRowProps) {
  const scoreClass = scoreBadgeColor(company.trend_score)
  return (
    <Link
      href={`/companies/${company.slug}`}
      className="flex items-center gap-3 py-2.5 border-b border-surface-border/50 last:border-0 no-underline group"
    >
      <span className="text-xs font-mono font-bold text-brand-400/20 w-5 text-center group-hover:text-brand-400/50 transition-colors">
        {String(rank).padStart(2, '0')}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-text-primary group-hover:text-brand-300 transition-colors truncate">
          {company.name}
        </p>
        <p className="text-xs font-mono text-text-muted">{company.news_count_7d} articles / 7d</p>
      </div>
      <span className={`badge ${scoreClass} text-xs flex-shrink-0`}>
        {formatScore(company.trend_score)}
      </span>
    </Link>
  )
}

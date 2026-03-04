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
      className={`badge ${scoreClass} hover:opacity-80 transition-opacity no-underline`}
    >
      {tag.name}
      <span className="ml-1 opacity-70">{tag.news_count_7d}↑</span>
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
    <Link href={`/companies/${company.slug}`} className="flex items-center gap-3 py-2 border-b border-surface-border last:border-0 no-underline group">
      <span className="text-sm font-bold text-gray-200 w-5 text-center">{rank}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 group-hover:text-brand-600 transition-colors truncate">
          {company.name}
        </p>
        <p className="text-xs text-gray-400">{company.news_count_7d} articles this week</p>
      </div>
      <span className={`badge ${scoreClass} text-[10px] flex-shrink-0`}>
        {formatScore(company.trend_score)}
      </span>
    </Link>
  )
}

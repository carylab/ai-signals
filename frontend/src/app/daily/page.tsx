import type { Metadata } from 'next'
import Link from 'next/link'
import { listBriefs, REVALIDATE_MEDIUM } from '@/lib/api'
import { BriefCard } from '@/components/brief/BriefCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { Pagination } from '@/components/ui/Pagination'

export const revalidate = REVALIDATE_MEDIUM

export const metadata: Metadata = {
  title: 'Daily Brief Archive',
  description: 'Browse daily AI intelligence briefings — curated summaries of the top AI news.',
}

interface Props {
  searchParams: { page?: string }
}

export default async function DailyBriefListPage({ searchParams }: Props) {
  const page = Number(searchParams.page ?? 1)
  const result = await listBriefs(page, 10)

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Daily Brief</h1>
        <p className="text-sm text-gray-500 mt-1">
          Daily AI intelligence briefings. Generated automatically from top articles.
        </p>
      </header>

      {result.data.length === 0 ? (
        <EmptyState title="No briefs yet" description="Check back tomorrow." />
      ) : (
        <>
          <div className="space-y-4">
            {result.data.map((brief) => (
              <BriefCard key={brief.date} brief={brief} />
            ))}
          </div>

          <Pagination
            page={page}
            hasNext={result.has_next}
            hasPrev={result.has_prev}
            baseUrl="/daily"
          />
        </>
      )}
    </div>
  )
}

interface PaginationProps {
  page: number
  hasNext: boolean
  hasPrev: boolean
  baseUrl: string
  extraParams?: Record<string, string>
}

export function Pagination({ page, hasNext, hasPrev, baseUrl, extraParams = {} }: PaginationProps) {
  const params = new URLSearchParams(extraParams)

  const prevParams = new URLSearchParams(params)
  prevParams.set('page', String(page - 1))

  const nextParams = new URLSearchParams(params)
  nextParams.set('page', String(page + 1))

  return (
    <div className="flex items-center justify-center gap-4 py-6">
      {hasPrev ? (
        <a
          href={`${baseUrl}?${prevParams}`}
          className="btn-primary no-underline"
        >
          ← Prev
        </a>
      ) : (
        <span className="btn opacity-40 cursor-default">← Prev</span>
      )}

      <span className="text-sm text-gray-500">Page {page}</span>

      {hasNext ? (
        <a
          href={`${baseUrl}?${nextParams}`}
          className="btn-primary no-underline"
        >
          Next →
        </a>
      ) : (
        <span className="btn opacity-40 cursor-default">Next →</span>
      )}
    </div>
  )
}

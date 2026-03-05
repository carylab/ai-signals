import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { getArticle } from '@/lib/api'
import { formatDate, formatRelativeTime, scoreBadgeColor, formatScore, SITE_NAME } from '@/lib/utils'

interface Props {
  params: { slug: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  try {
    const article = await getArticle(params.slug)
    return {
      title: article.title,
      description: article.meta_description ?? article.summary ?? undefined,
      openGraph: {
        title: article.title,
        description: article.meta_description ?? article.summary ?? undefined,
        type: 'article',
        publishedTime: article.published_at ?? undefined,
        images: article.image_url ? [article.image_url] : [],
      },
    }
  } catch {
    return { title: 'Article' }
  }
}

export default async function ArticlePage({ params }: Props) {
  let article
  try {
    article = await getArticle(params.slug)
  } catch {
    notFound()
  }

  const scoreClass = scoreBadgeColor(article.final_score)

  return (
    <article className="max-w-3xl mx-auto">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs font-mono text-text-muted mb-6">
        <Link href="/" className="hover:text-brand-300 no-underline">Home</Link>
        <span className="text-surface-border">/</span>
        {article.tags[0] && (
          <>
            <Link href={`/topics/${article.tags[0].slug}`} className="hover:text-brand-300 no-underline">
              {article.tags[0].name}
            </Link>
            <span className="text-surface-border">/</span>
          </>
        )}
        <span className="text-text-muted truncate">{article.title.slice(0, 50)}…</span>
      </nav>

      {/* Header */}
      <header className="mb-6">
        <div className="flex flex-wrap gap-1.5 mb-3">
          {article.tags.slice(0, 4).map((tag) => (
            <Link key={tag.slug} href={`/topics/${tag.slug}`} className="badge badge-blue no-underline">
              {tag.name}
            </Link>
          ))}
          <span className={`badge ${scoreClass}`}>
            Score {formatScore(article.final_score)}
          </span>
        </div>

        <h1 className="text-2xl font-bold leading-tight text-text-primary mb-3">
          {article.title}
        </h1>

        <div className="flex items-center gap-3 text-xs font-mono text-text-muted flex-wrap">
          {article.author && <span>{article.author}</span>}
          {article.published_at && (
            <>
              <span>·</span>
              <time dateTime={article.published_at} title={formatDate(article.published_at)}>
                {formatRelativeTime(article.published_at)}
              </time>
            </>
          )}
          {article.word_count && (
            <>
              <span>·</span>
              <span>{article.word_count.toLocaleString()} words</span>
            </>
          )}
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto btn-primary no-underline text-xs"
          >
            Read original ↗
          </a>
        </div>
      </header>

      {/* Hero image */}
      {article.image_url && (
        <div className="relative w-full h-64 rounded-lg overflow-hidden mb-6">
          <Image
            src={article.image_url}
            alt={article.title}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 768px"
            priority
          />
        </div>
      )}

      {/* AI summary */}
      {(article.summary || article.summary_bullets?.length > 0) && (
        <div className="rounded-lg border border-brand-800/50 bg-brand-400/5 p-4 mb-6">
          <p className="section-title">AI Summary</p>
          {article.summary && (
            <p className="text-xs text-text-secondary leading-relaxed mb-3">{article.summary}</p>
          )}
          {article.summary_bullets?.length > 0 && (
            <ul className="space-y-1.5">
              {article.summary_bullets.map((bullet, i) => (
                <li key={i} className="flex gap-2 text-xs text-text-secondary">
                  <span className="text-brand-400 flex-shrink-0">›</span>
                  {bullet}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Full content */}
      {article.clean_content && (
        <div className="prose prose-sm prose-invert max-w-none text-text-secondary leading-relaxed mb-8">
          {article.clean_content.split('\n\n').map((para, i) => (
            <p key={i} className="mb-4 text-xs">{para}</p>
          ))}
        </div>
      )}

      <div className="space-y-3 border-t border-surface-border pt-5">
        {article.companies.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-text-muted w-20">Companies</span>
            {article.companies.map((c) => (
              <Link key={c.slug} href={`/companies/${c.slug}`} className="badge badge-gray no-underline">
                {c.name}
              </Link>
            ))}
          </div>
        )}

        {article.ai_models.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-text-muted w-20">AI Models</span>
            {article.ai_models.map((m) => (
              <span key={m.slug} className="badge badge-gray">{m.name}</span>
            ))}
          </div>
        )}

        {article.tags.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-text-muted w-20">Topics</span>
            {article.tags.map((tag) => (
              <Link key={tag.slug} href={`/topics/${tag.slug}`} className="badge badge-blue no-underline">
                {tag.name}
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Structured data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'NewsArticle',
            headline: article.title,
            description: article.meta_description ?? article.summary,
            image: article.image_url ? [article.image_url] : undefined,
            datePublished: article.published_at,
            url: article.url,
            publisher: { '@type': 'Organization', name: SITE_NAME },
          }),
        }}
      />
    </article>
  )
}

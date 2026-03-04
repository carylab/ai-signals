import Link from 'next/link'
import { SITE_NAME, SITE_URL } from '@/lib/utils'

export function SiteFooter() {
  const year = new Date().getFullYear()

  return (
    <footer className="border-t border-surface-border bg-white mt-12">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
          <div>
            <p className="font-semibold text-gray-900 text-sm mb-3">{SITE_NAME}</p>
            <p className="text-xs text-gray-500 leading-relaxed">
              Daily AI news, trends, and analysis. Curated intelligence for researchers,
              engineers, and investors.
            </p>
          </div>

          <div>
            <p className="section-title">Discover</p>
            <ul className="space-y-1.5">
              {[
                { href: '/trending',  label: 'Trending' },
                { href: '/topics',    label: 'Topics' },
                { href: '/companies', label: 'Companies' },
                { href: '/daily',     label: 'Daily Brief' },
              ].map(({ href, label }) => (
                <li key={href}>
                  <Link href={href} className="text-xs text-gray-500 hover:text-brand-600 no-underline">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="section-title">Tools</p>
            <ul className="space-y-1.5">
              <li>
                <Link href="/search" className="text-xs text-gray-500 hover:text-brand-600 no-underline">
                  Search
                </Link>
              </li>
              <li>
                <a href="/api/v1/rss" className="text-xs text-gray-500 hover:text-brand-600 no-underline">
                  RSS Feed
                </a>
              </li>
              <li>
                <a href="/api/v1/docs" className="text-xs text-gray-500 hover:text-brand-600 no-underline">
                  API Docs
                </a>
              </li>
            </ul>
          </div>

          <div>
            <p className="section-title">Meta</p>
            <ul className="space-y-1.5">
              <li>
                <a
                  href={SITE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-gray-500 hover:text-brand-600 no-underline"
                >
                  {SITE_URL.replace('https://', '')}
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="pt-4 border-t border-surface-border flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <p className="text-xs text-gray-400">
            © {year} {SITE_NAME}. Powered by AI pipeline.
          </p>
          <p className="text-xs text-gray-400">
            Updated daily · <a href="/api/v1/rss" className="hover:text-brand-600 no-underline">RSS</a>
          </p>
        </div>
      </div>
    </footer>
  )
}

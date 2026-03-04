import Link from 'next/link'
import { SITE_NAME } from '@/lib/utils'

const NAV_LINKS = [
  { href: '/',          label: 'Home' },
  { href: '/trending',  label: 'Trending' },
  { href: '/topics',    label: 'Topics' },
  { href: '/companies', label: 'Companies' },
  { href: '/daily',     label: 'Daily Brief' },
  { href: '/search',    label: 'Search' },
]

export function SiteHeader() {
  return (
    <header className="border-b border-surface-border bg-white sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-1.5 text-gray-900 hover:text-gray-900 no-underline">
          <span className="font-bold text-base tracking-tight">{SITE_NAME}</span>
          <span className="badge badge-blue text-[10px]">beta</span>
        </Link>

        {/* Nav */}
        <nav className="hidden md:flex items-center gap-1 flex-1">
          {NAV_LINKS.slice(1).map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="px-2.5 py-1 rounded text-sm text-gray-600 hover:text-gray-900 hover:bg-surface-subtle transition-colors no-underline"
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* RSS link */}
        <a
          href="/api/v1/rss"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden md:flex items-center gap-1 text-xs text-gray-400 hover:text-brand-600 transition-colors no-underline"
          title="RSS Feed"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6.18 15.64a2.18 2.18 0 0 1 2.18 2.18C8.36 19.01 7.38 20 6.18 20C4.98 20 4 19.01 4 17.82a2.18 2.18 0 0 1 2.18-2.18M4 4.44A15.56 15.56 0 0 1 19.56 20h-2.83A12.73 12.73 0 0 0 4 7.27V4.44m0 5.66a9.9 9.9 0 0 1 9.9 9.9h-2.83A7.07 7.07 0 0 0 4 12.93V10.1z"/>
          </svg>
          RSS
        </a>
      </div>
    </header>
  )
}

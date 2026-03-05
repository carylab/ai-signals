'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { SITE_NAME } from '@/lib/utils'

const NAV_LINKS = [
  { href: '/trending',  label: 'Trending' },
  { href: '/topics',    label: 'Topics' },
  { href: '/companies', label: 'Companies' },
  { href: '/daily',     label: 'Daily Brief' },
  { href: '/search',    label: 'Search' },
]

export function SiteHeader() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-40 border-b border-surface-border bg-surface/95 backdrop-blur-md">
      {/* Top accent line */}
      <div className="h-px bg-gradient-to-r from-transparent via-brand-400 to-transparent opacity-60" />

      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 no-underline group flex-shrink-0"
        >
          {/* Icon mark */}
          <div className="relative w-7 h-7 flex items-center justify-center">
            <div className="absolute inset-0 bg-brand-400/10 rounded border border-brand-400/30 group-hover:border-brand-400/60 group-hover:bg-brand-400/15 transition-all duration-200" />
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="relative z-10">
              <path d="M7 1L13 4V10L7 13L1 10V4L7 1Z" stroke="#00ffb3" strokeWidth="1" strokeLinejoin="round" opacity="0.8"/>
              <path d="M7 4L10 5.5V8.5L7 10L4 8.5V5.5L7 4Z" fill="#00ffb3" opacity="0.4"/>
            </svg>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-bold text-sm tracking-tight text-text-primary group-hover:text-brand-300 transition-colors">
              {SITE_NAME}
            </span>
            <span className="badge badge-green text-xs py-0">BETA</span>
          </div>
        </Link>

        {/* Separator */}
        <div className="h-4 w-px bg-surface-border hidden md:block" />

        {/* Nav */}
        <nav className="hidden md:flex items-center gap-0.5 flex-1">
          {NAV_LINKS.map(({ href, label }) => {
            const active = pathname === href || (href !== '/' && pathname.startsWith(href))
            return (
              <Link
                key={href}
                href={href}
                className={`px-3 py-1.5 rounded text-xs font-mono transition-all duration-150 no-underline ${
                  active
                    ? 'text-brand-300 bg-brand-400/10 border border-brand-400/20'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover border border-transparent'
                }`}
              >
                {label}
              </Link>
            )
          })}
        </nav>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-3">
          {/* Live indicator */}
          <div className="hidden sm:flex items-center gap-1.5 text-xs font-mono text-text-muted">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-brand-400" />
            </span>
            LIVE
          </div>

          {/* RSS */}
          <a
            href="/api/v1/rss"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden md:flex items-center gap-1 text-xs font-mono text-text-muted hover:text-brand-400 transition-colors no-underline border border-surface-border hover:border-brand-400/40 rounded px-2 py-1"
            title="RSS Feed"
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6.18 15.64a2.18 2.18 0 0 1 2.18 2.18C8.36 19.01 7.38 20 6.18 20C4.98 20 4 19.01 4 17.82a2.18 2.18 0 0 1 2.18-2.18M4 4.44A15.56 15.56 0 0 1 19.56 20h-2.83A12.73 12.73 0 0 0 4 7.27V4.44m0 5.66a9.9 9.9 0 0 1 9.9 9.9h-2.83A7.07 7.07 0 0 0 4 12.93V10.1z"/>
            </svg>
            RSS
          </a>
        </div>
      </div>
    </header>
  )
}

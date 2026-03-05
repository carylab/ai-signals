import Link from 'next/link'
import { SITE_NAME, SITE_URL } from '@/lib/utils'

export function SiteFooter() {
  const year = new Date().getFullYear()

  return (
    <footer className="border-t border-surface-border bg-surface-subtle/50 mt-16">
      {/* Top accent */}
      <div className="h-px bg-gradient-to-r from-transparent via-brand-400/30 to-transparent" />

      <div className="max-w-6xl mx-auto px-4 py-10">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-5 h-5 flex items-center justify-center border border-brand-400/30 rounded bg-brand-400/5">
                <svg width="10" height="10" viewBox="0 0 14 14" fill="none">
                  <path d="M7 1L13 4V10L7 13L1 10V4L7 1Z" stroke="#00ffb3" strokeWidth="1" strokeLinejoin="round" opacity="0.8"/>
                  <path d="M7 4L10 5.5V8.5L7 10L4 8.5V5.5L7 4Z" fill="#00ffb3" opacity="0.4"/>
                </svg>
              </div>
              <p className="font-bold text-sm text-text-primary font-mono">{SITE_NAME}</p>
            </div>
            <p className="text-xs text-text-muted leading-relaxed">
              Daily AI news, trends, and analysis. Curated intelligence for researchers,
              engineers, and investors.
            </p>
          </div>

          <div>
            <p className="section-title">Discover</p>
            <ul className="space-y-2">
              {[
                { href: '/trending',  label: 'Trending' },
                { href: '/topics',    label: 'Topics' },
                { href: '/companies', label: 'Companies' },
                { href: '/daily',     label: 'Daily Brief' },
              ].map(({ href, label }) => (
                <li key={href}>
                  <Link href={href} className="text-xs font-mono text-text-muted hover:text-brand-300 no-underline transition-colors">
                    <span className="text-brand-400/40 mr-1">›</span>{label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="section-title">Tools</p>
            <ul className="space-y-2">
              {[
                { href: '/search',     label: 'Search', external: false },
                { href: '/api/v1/rss', label: 'RSS Feed', external: true },
                { href: '/api/v1/docs', label: 'API Docs', external: true },
              ].map(({ href, label, external }) => (
                <li key={href}>
                  {external ? (
                    <a href={href} className="text-xs font-mono text-text-muted hover:text-brand-300 no-underline transition-colors">
                      <span className="text-brand-400/40 mr-1">›</span>{label}
                    </a>
                  ) : (
                    <Link href={href} className="text-xs font-mono text-text-muted hover:text-brand-300 no-underline transition-colors">
                      <span className="text-brand-400/40 mr-1">›</span>{label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="section-title">Status</p>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-400 shadow-neon-green" />
                <span className="text-xs font-mono text-text-muted">Pipeline: Active</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                <span className="text-xs font-mono text-text-muted">Updated: Daily 06:00 UTC</span>
              </div>
              <div className="mt-3">
                <a
                  href={SITE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-mono text-text-muted hover:text-brand-300 no-underline transition-colors"
                >
                  <span className="text-brand-400/40 mr-1">›</span>{SITE_URL.replace('https://', '')}
                </a>
              </div>
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-surface-border flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <p className="text-xs font-mono text-text-muted">
            © {year} {SITE_NAME} · Powered by AI pipeline
          </p>
          <p className="text-xs font-mono text-text-muted">
            <span className="text-brand-400/50">~/</span> Updated daily ·{' '}
            <a href="/api/v1/rss" className="hover:text-brand-300 no-underline">RSS ↗</a>
          </p>
        </div>
      </div>
    </footer>
  )
}

import type { Metadata } from 'next'
import '@/styles/globals.css'
import { SiteHeader } from '@/components/layout/SiteHeader'
import { SiteFooter } from '@/components/layout/SiteFooter'
import { SITE_NAME, SITE_URL } from '@/lib/utils'

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — AI Industry Intelligence`,
    template: `%s | ${SITE_NAME}`,
  },
  description:
    'Daily AI news, trends, and analysis. Curated intelligence for researchers, engineers, and investors.',
  keywords: ['AI news', 'artificial intelligence', 'LLM', 'machine learning', 'AI trends'],
  authors: [{ name: SITE_NAME, url: SITE_URL }],
  creator: SITE_NAME,
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: SITE_URL,
    siteName: SITE_NAME,
    title: `${SITE_NAME} — AI Industry Intelligence`,
    description: 'Daily AI news, trends, and analysis.',
  },
  twitter: {
    card: 'summary_large_image',
    title: SITE_NAME,
    description: 'Daily AI news, trends, and analysis.',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
  alternates: {
    types: { 'application/rss+xml': `${SITE_URL}/api/v1/rss` },
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen flex flex-col bg-surface-muted">
        <SiteHeader />
        <main className="flex-1 w-full max-w-6xl mx-auto px-4 py-6">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  )
}

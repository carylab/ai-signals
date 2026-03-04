import { MetadataRoute } from 'next'
import { getAllTopics, getAllCompanies, listBriefs, REVALIDATE_LONG } from '@/lib/api'
import { SITE_URL } from '@/lib/utils'

export const revalidate = REVALIDATE_LONG

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date().toISOString()

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: SITE_URL, lastModified: now, changeFrequency: 'hourly', priority: 1.0 },
    { url: `${SITE_URL}/trending`, lastModified: now, changeFrequency: 'hourly', priority: 0.9 },
    { url: `${SITE_URL}/daily`, lastModified: now, changeFrequency: 'daily', priority: 0.8 },
    { url: `${SITE_URL}/topics`, lastModified: now, changeFrequency: 'daily', priority: 0.7 },
    { url: `${SITE_URL}/companies`, lastModified: now, changeFrequency: 'daily', priority: 0.7 },
    { url: `${SITE_URL}/search`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
  ]

  // Fetch dynamic routes in parallel; silently omit on error
  const [topicsRes, companiesRes, briefsRes] = await Promise.allSettled([
    getAllTopics(),
    getAllCompanies(),
    listBriefs(1, 90),
  ])

  const topicRoutes: MetadataRoute.Sitemap =
    topicsRes.status === 'fulfilled'
      ? topicsRes.value.map((t) => ({
          url: `${SITE_URL}/topics/${t.slug}`,
          lastModified: now,
          changeFrequency: 'daily' as const,
          priority: 0.6,
        }))
      : []

  const companyRoutes: MetadataRoute.Sitemap =
    companiesRes.status === 'fulfilled'
      ? companiesRes.value.map((c) => ({
          url: `${SITE_URL}/companies/${c.slug}`,
          lastModified: now,
          changeFrequency: 'daily' as const,
          priority: 0.6,
        }))
      : []

  const briefRoutes: MetadataRoute.Sitemap =
    briefsRes.status === 'fulfilled'
      ? briefsRes.value.data.map((b) => ({
          url: `${SITE_URL}/daily/${b.date}`,
          lastModified: b.date,
          changeFrequency: 'monthly' as const,
          priority: 0.5,
        }))
      : []

  return [...staticRoutes, ...topicRoutes, ...companyRoutes, ...briefRoutes]
}

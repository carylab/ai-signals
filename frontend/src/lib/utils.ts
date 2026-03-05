import { format, formatDistanceToNow, parseISO } from 'date-fns'

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  try {
    return format(parseISO(dateStr), 'MMM d, yyyy')
  } catch {
    return dateStr
  }
}

export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  try {
    return formatDistanceToNow(parseISO(dateStr), { addSuffix: true })
  } catch {
    return ''
  }
}

export function formatScore(score: number): string {
  return (score * 100).toFixed(0)
}

export function scoreColor(score: number): string {
  if (score >= 0.75) return 'text-green-600'
  if (score >= 0.50) return 'text-yellow-600'
  if (score >= 0.25) return 'text-orange-500'
  return 'text-gray-400'
}

export function scoreBadgeColor(score: number): string {
  if (score >= 0.75) return 'score-high'
  if (score >= 0.50) return 'score-medium'
  if (score >= 0.25) return 'score-low'
  return 'score-none'
}

export function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text
  return text.slice(0, maxLen - 1) + '…'
}

export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://aisignals.io'
export const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME ?? 'AI Signals'

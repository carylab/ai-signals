import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="text-center py-20">
      <p className="text-6xl font-bold text-gray-200 mb-4">404</p>
      <h1 className="text-xl font-semibold text-gray-700 mb-2">Page not found</h1>
      <p className="text-sm text-gray-500 mb-6">
        This page may have moved or doesn't exist.
      </p>
      <Link href="/" className="btn-primary no-underline">
        Go Home
      </Link>
    </div>
  )
}

interface EmptyStateProps {
  title: string
  description?: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="text-center py-16">
      <p className="text-gray-400 font-medium">{title}</p>
      {description && (
        <p className="text-gray-400 text-sm mt-1">{description}</p>
      )}
    </div>
  )
}

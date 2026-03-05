interface EmptyStateProps {
  title: string
  description?: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="text-center py-16">
      <p className="text-text-muted font-mono text-sm font-medium">{title}</p>
      {description && (
        <p className="text-text-muted font-mono text-xs mt-1">{description}</p>
      )}
    </div>
  )
}
